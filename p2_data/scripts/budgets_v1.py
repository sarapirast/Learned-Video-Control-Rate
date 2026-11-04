"""P2 work-queue item 14: budget table + causal base-QP estimator on data v1 (no encodes).

Budgets (never the GOP's own spend, which leaks the GOP's cost to the policy; finding C1):
  For clip c and level q0, every GOP of c gets B = mean over c's GOPs of their constant-QP slice bits at q0, i.e. a
  whole-clip constant-QP encode at q0 split evenly per GOP (GOPs are closed IDR GOPs, so the clip encode's bits are
  the sum of the GOP encodes up to headers). A hard GOP gets less than its own need, an easy one more.
  Levels q0 in LEVELS. Bits are slice bits only (headers excluded; agreed with P1 2026-11-03).
Hindsight reference per GOP and budget (NOT causal; the estimator's target and P3's search start):
  q_fit = the QP at which this GOP's own constant-QP curve spends exactly B (log-bits interpolated over QP 18-50;
  clipped to the range, with flags).
Causal estimator: q_hat = f(budget per frame, first-pass bits visible at lookahead k), fitted on TRAIN only.
  features at k: log2(B / 30), log2 fp[0] (the I frame); for k >= 1 also log2 mean fp[1..k] (visible P frames).
  models: linear (OLS) and gradient boosting (sklearn HistGradientBoosting). Train predictions are out-of-fold
  (GroupKFold by source group), so no stored prediction is in-sample.
Encoders x264 and x265; first-pass QP 30 and 32 (both kept until the team picks one).

  python scripts/budgets_v1.py   -> data/v1/320x180/budgets.csv, docs/budget-estimator-v1.md
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold

D = "/scratch1/aayushso/ee599/data/v1/320x180"
LEVELS = (24, 30, 36, 42)
KS = (0, 2, 5, 10, 29)
QMIN, QMAX = 18, 50

rd = pd.read_parquet(f"{D}/rd/rd_native.parquet")
fp = pd.read_parquet(f"{D}/features/fp_bits.parquet")
gops = pd.read_csv(f"{D}/gops.csv")
gops["cls"] = np.where(gops.label.isin(["cut", "gradual"]), "cut/gradual", "stable")

# ---------------------------------------------------------------- budget table
curves = {k: g.sort_values("qp") for k, g in rd.groupby(["encoder", "clip_id", "gop"])}
rows = []
for (enc, clip), g in rd.groupby(["encoder", "clip_id"]):
    for q0 in LEVELS:
        B = g[g.qp == q0].slice_bits.mean()
        for gop in sorted(g.gop.unique()):
            c = curves[(enc, clip, gop)]
            qs, lb = c.qp.to_numpy(float), np.log2(np.minimum.accumulate(c.slice_bits.to_numpy(float)))
            lB = np.log2(B)
            if lB >= lb[0]:
                qf, flag = QMIN, "budget >= own spend at QP 18"
            elif lB <= lb[-1]:
                qf, flag = QMAX, "budget <= own spend at QP 50"
            else:
                qf, flag = float(np.interp(-lB, -lb, qs)), ""
            own = c[c.qp == q0].slice_bits.iloc[0]
            rows.append({"encoder": enc, "clip_id": clip, "gop": gop, "level_q0": q0, "budget_bits": B,
                         "how_set": f"clip mean of constant-QP {q0} slice bits per GOP",
                         "budget_over_own_cqp": B / own, "q_fit": qf, "q_fit_flag": flag})
bt = pd.DataFrame(rows).merge(gops[["clip_id", "gop", "split", "group", "label", "cls"]], on=["clip_id", "gop"])

# ---------------------------------------------------------------- estimator features
fpw = fp.pivot_table(index=["encoder", "fp_qp", "clip_id", "gop"], columns="frame", values="fp_slice_bits")
fpw = np.log2(np.maximum(fpw, 8))


def feats(sub, enc, fq, k):
    f = fpw.loc[(enc, fq)]
    X = pd.DataFrame({"lb": np.log2(sub.budget_bits.to_numpy() / 30)}, index=sub.index)
    idx = list(zip(sub.clip_id, sub.gop))
    X["fp0"] = f.loc[idx, 0].to_numpy()
    if k >= 1:
        X["fpP"] = np.log2((2 ** f.loc[idx, list(range(1, k + 1))]).mean(1)).to_numpy()
    return X


res, preds = [], {}
for enc in ("x264", "x265"):
    for fq in (30, 32):
        for k in KS:
            sub = bt[bt.encoder == enc]
            X = feats(sub, enc, fq, k)
            y = sub.q_fit.to_numpy()
            tr = (sub.split == "train").to_numpy()
            for name, mk in (("linear", LinearRegression),
                             ("gbm", lambda: HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                                                          max_leaf_nodes=15, random_state=0))):
                p = np.full(len(sub), np.nan)
                for a, b in GroupKFold(5).split(X[tr], y[tr], sub.group[tr]):     # out-of-fold on train
                    m = mk().fit(X[tr].iloc[a], y[tr][a])
                    p[np.flatnonzero(tr)[b]] = m.predict(X[tr].iloc[b])
                m = mk().fit(X[tr], y[tr])
                p[~tr] = m.predict(X[~tr])
                preds[(enc, fq, k, name)] = pd.Series(p, index=sub.index)
                if name == "linear":
                    coef = dict(zip(X.columns, np.round(m.coef_, 3)), intercept=round(float(m.intercept_), 2))
                e = np.abs(p - y)
                for split in ("train", "val", "test"):
                    for cls in ("all", "stable", "cut/gradual"):
                        msk = (sub.split == split).to_numpy() & ((sub.cls == cls).to_numpy() if cls != "all" else True)
                        res.append({"encoder": enc, "fp_qp": fq, "k": k, "model": name, "split": split, "class": cls,
                                    "n": int(msk.sum()), "MAE (QP)": e[msk].mean(), "p90 |err|": np.percentile(e[msk], 90),
                                    "bias": (p - y)[msk].mean(), "coef": coef if name == "linear" else ""})
# budget-only baseline (no first pass): how much the first pass adds
for enc in ("x264", "x265"):
    sub = bt[bt.encoder == enc]
    tr = (sub.split == "train").to_numpy()
    X = pd.DataFrame({"lb": np.log2(sub.budget_bits / 30)})
    m = LinearRegression().fit(X[tr], sub.q_fit[tr])
    p = m.predict(X)
    for split in ("val", "test"):
        msk = (sub.split == split).to_numpy()
        res.append({"encoder": enc, "fp_qp": "-", "k": "-", "model": "budget only", "split": split, "class": "all",
                    "n": int(msk.sum()), "MAE (QP)": np.abs(p - sub.q_fit)[msk].mean(),
                    "p90 |err|": np.percentile(np.abs(p - sub.q_fit)[msk], 90), "bias": (p - sub.q_fit)[msk].mean(),
                    "coef": ""})
R = pd.DataFrame(res)

# ---------------------------------------------------------------- write budget table with the k=0 estimate
CHOSEN = ("linear", 32)          # recorded estimator in budgets.csv (k=0, fp QP 32); all variants are in the report
for enc in ("x264", "x265"):
    for k in KS:
        bt.loc[bt.encoder == enc, f"base_qp_est_k{k}"] = preds[(enc, CHOSEN[1], k, CHOSEN[0])]
bt.to_csv(f"{D}/budgets.csv", index=False)

# ---------------------------------------------------------------- report
L = ["# Budget table and causal base-QP estimator (data v1)", "",
     "Generated by `scripts/budgets_v1.py` (see its docstring for definitions). Output table: "
     "`data/v1/320x180/budgets.csv` (one row per encoder x GOP x level; `base_qp_est_k*` = linear estimator, "
     "first pass at QP 32, out-of-fold on train).", ""]
q = bt.groupby(["encoder", "level_q0"]).agg(
    gops=("gop", "size"), median_kbit=("budget_bits", lambda s: s.median() / 1e3),
    ratio_p10=("budget_over_own_cqp", lambda s: s.quantile(.1)), ratio_median=("budget_over_own_cqp", "median"),
    ratio_p90=("budget_over_own_cqp", lambda s: s.quantile(.9)),
    q_fit_median=("q_fit", "median"), clipped=("q_fit_flag", lambda s: int((s != "").sum()))).reset_index()
L += ["## Budgets", "",
      "`ratio` = budget / the GOP's own constant-QP spend at the same level. Under the old definition it is exactly 1 "
      "for every GOP; here it varies with how hard the GOP is relative to its clip. `clipped` = GOPs whose q_fit hit "
      "QP 18 or 50.", "", q.round(3).to_markdown(index=False), ""]
sel = R[(R["class"] == "all") & (R.split.isin(["val", "test"]))]
piv = sel[sel.model != "budget only"].pivot_table(index=["encoder", "fp_qp", "model", "split"], columns="k",
                                                  values="MAE (QP)").round(2)
piv.columns = [f"k={c}" for c in piv.columns]
L += ["## Estimator error (mean absolute error in QP vs q_fit)", "",
      "q_fit is the hindsight constant QP that spends exactly the budget. k = lookahead frames whose first-pass "
      "bits the estimator sees (k = 0: the I frame only).", "", piv.reset_index().to_markdown(index=False), "",
      "Budget only (no first-pass bits):", "",
      sel[sel.model == "budget only"][["encoder", "split", "MAE (QP)", "p90 |err|", "bias"]].round(2)
      .to_markdown(index=False), ""]
vc = R[(R.split == "val") & (R.model == "linear") & (R.fp_qp == 32) & (R["class"] != "all")].pivot_table(
    index=["encoder", "class"], columns="k", values="MAE (QP)").round(2)
vc.columns = [f"k={c}" for c in vc.columns]
L += ["## Stable vs cut/gradual GOPs (val, linear, first pass QP 32)", "", vc.reset_index().to_markdown(index=False), ""]
co = R[(R.model == "linear") & (R.split == "val") & (R["class"] == "all")][["encoder", "fp_qp", "k", "coef"]]
L += ["## Linear coefficients (fitted on all train)", "", co.to_markdown(index=False), ""]
L += ["## Full table", "", R.drop(columns="coef").round(3).to_markdown(index=False), ""]
open("/scratch1/aayushso/ee599/docs/budget-estimator-v1.md", "w").write("\n".join(L) + "\n")
print("\n".join(L[:40]))
