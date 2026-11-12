"""Gate test: does the PREVIOUS GOP of the same clip improve the causal base-QP estimate? (P2, 2026-11-09)

Budgets are clip-level (budgets.csv: every GOP of a clip gets the same budget at a level), GOPs within a clip are
consecutive, and a real encoder has finished GOP n-1 before it starts GOP n. Nothing in the env or the controller
uses that history today: each GOP starts from the train-mean rate model. Target = q_fit (hindsight constant QP that
spends exactly the budget; the estimator's target in scripts/budgets_v1.py). Rows = GOPs WITH a predecessor in the
same clip (933 of 1042); first GOPs of a clip are unchanged by construction and are left out of every comparison.

Feature sets (all on first-pass QP 32, same as budgets.csv's recorded estimator):
  base     log2(B/30), log2 fp[0]; for k >= 1 also log2 mean fp[1..k]                       (= budgets_v1.py)
  +ideal   base + the previous GOP's q_fit at the same level and log2(its CQP-32 bits / its first-pass total)
           (an idealised summary of its encode: as if the encoder knew its whole constant-QP curve)
  +ctrl    base + what the encoder REALLY has after running P2's controller (final2, same level and k) on GOP n-1:
           q_eq = mean P QP used + s_p x log2(bits spent / budget) (the constant QP that would have hit the budget, via
           the controller's rate-model slope), and log2(bits spent / its first-pass total). x264 only (x265 has no
           train controller run).
  prev     q_fit = previous GOP's q_fit (naive "same QP as last GOP"), no model
Models: linear (OLS) and gradient boosting, fitted on train only; train rows out-of-fold by source group (as in
budgets_v1.py). Reported: MAE in QP on val and test, by class (stable / cut+gradual / cut at the GOP start), and the
paired improvement over base with a 95% bootstrap CI over clips.

  /scratch1/aayushso/envs/ee599/bin/python -I scripts/prevgop_gate.py
Out: results_v1/gates/prevgop_gate.md (+ .csv)
"""
import glob
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold

ROOT = "/scratch1/aayushso/ee599"
D = f"{ROOT}/data/v1/320x180"
OUT = f"{ROOT}/results_v1/gates"
KS = (0, 2, 5)
SETTING = "0.97:3.0:0.3:2.0:3.0:4.0:0.0:1.0:0.0:0.0"
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def gbm():
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, random_state=0)


def fit_predict(X, y, tr, groups, mk):
    p = np.full(len(y), np.nan)
    for a, b in GroupKFold(5).split(X[tr], y[tr], groups[tr]):
        p[np.flatnonzero(tr)[b]] = mk().fit(X[tr].iloc[a], y[tr][a]).predict(X[tr].iloc[b])
    p[~tr] = mk().fit(X[tr], y[tr]).predict(X[~tr])
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    bt = pd.read_csv(f"{D}/budgets.csv")
    gops = pd.read_csv(f"{D}/gops.csv")[["clip_id", "gop", "cut_at_gop_start"]]
    bt = bt.merge(gops, on=["clip_id", "gop"])
    fp = pd.read_parquet(f"{D}/features/fp_bits.parquet").query("fp_qp == 32")
    fpw = np.log2(np.maximum(fp.pivot_table(index=["encoder", "clip_id", "gop"], columns="frame",
                                            values="fp_slice_bits"), 8))
    fptot = np.log2((2 ** fpw).sum(1))
    rd = pd.read_parquet(f"{D}/rd/rd_native.parquet", columns=["encoder", "clip_id", "gop", "qp", "slice_bits"])
    cq32 = np.log2(rd[rd.qp == 32].set_index(["encoder", "clip_id", "gop"]).slice_bits)
    sp = {e: v["s_p"] for e, v in json.load(open(f"{D}/rd/controller_model.json")).items()}

    ctrl = pd.concat([pd.read_parquet(p) for p in glob.glob(f"{ROOT}/results_v1/controller_real/final2_x264_*.parquet")])
    ctrl = ctrl[ctrl.setting == SETTING]
    ctrl["q_eq"] = [np.mean(q[1:]) + sp["x264"] * np.log2(b / B)
                    for q, b, B in zip(ctrl.qps, ctrl.bits, ctrl.budget_bits)]
    ctrl["lcal"] = np.log2(ctrl.bits) - fptot.loc["x264"].reindex(list(zip(ctrl.clip_id, ctrl.gop))).to_numpy()
    ctrl = ctrl.set_index(["clip_id", "gop", "level_q0", "k"])[["q_eq", "lcal"]]

    rows, res = [], []
    for enc in ("x264", "x265"):
        sub = bt[bt.encoder == enc].copy()
        prev = sub[["clip_id", "gop", "level_q0", "q_fit"]].assign(gop=lambda x: x.gop + 1)
        sub = sub.merge(prev.rename(columns={"q_fit": "prev_qfit"}), on=["clip_id", "gop", "level_q0"], how="inner")
        key_prev = list(zip([enc] * len(sub), sub.clip_id, sub.gop - 1))
        sub["prev_lcal"] = cq32.reindex(key_prev).to_numpy() - fptot.reindex(key_prev).to_numpy()
        sub = sub.reset_index(drop=True)
        idx = list(zip(sub.clip_id, sub.gop))
        f = fpw.loc[enc]
        y = sub.q_fit.to_numpy()
        tr = (sub.split == "train").to_numpy()
        for k in KS:
            X = pd.DataFrame({"lb": np.log2(sub.budget_bits / 30), "fp0": f.loc[idx, 0].to_numpy()})
            if k >= 1:
                X["fpP"] = np.log2((2 ** f.loc[idx, list(range(1, k + 1))]).mean(1)).to_numpy()
            sets = {"base": X, "+ideal": X.assign(prev_qfit=sub.prev_qfit, prev_lcal=sub.prev_lcal)}
            if enc == "x264":
                c = ctrl.reindex(list(zip(sub.clip_id, sub.gop - 1, sub.level_q0, [k] * len(sub))))
                assert c.q_eq.notna().all(), "controller result missing for a previous GOP"
                sets["+ctrl"] = X.assign(prev_qeq=c.q_eq.to_numpy(), prev_lcal=c.lcal.to_numpy())
            preds = {("prev", "none"): sub.prev_qfit.to_numpy()}
            for name, Xs in sets.items():
                preds[(name, "linear")] = fit_predict(Xs, y, tr, sub.group.to_numpy(), LinearRegression)
                preds[(name, "gbm")] = fit_predict(Xs, y, tr, sub.group.to_numpy(), gbm)
            for (name, model), p in preds.items():
                e = np.abs(p - y)
                df =sub[["clip_id", "gop", "split", "cls", "level_q0", "cut_at_gop_start"]].assign(
                    encoder=enc, k=k, features=name, model=model, err=e)
                rows.append(df)
    E = pd.concat(rows, ignore_index=True)
    E.to_csv(f"{OUT}/prevgop_gate.csv", index=False)

    L = ["# Gate: previous-GOP features for the causal base-QP estimate", "",
         "Generated by `scripts/prevgop_gate.py` (definitions in its docstring). Target = q_fit (hindsight constant QP "
         "that spends exactly the clip-level budget). Rows = GOPs with a predecessor in the same clip, x 4 budget "
         "levels. MAE in QP. diff = MAE(features) - MAE(base, same model); negative = better; 95% bootstrap CI over "
         "clips.", ""]
    for split in ("val", "test"):
        L += [f"## {split}", ""]
        x = E[E.split == split]
        out = []
        for (enc, k), g in x.groupby(["encoder", "k"]):
            for model in ("linear", "gbm", "none"):
                for name in ("base", "+ideal", "+ctrl", "prev"):
                    h = g[(g.features == name) & (g.model == model)]
                    if h.empty:
                        continue
                    r = {"encoder": enc, "k": k, "model": model, "features": name, "n": len(h),
                         "MAE all": h.err.mean(), "MAE stable": h[h.cls == "stable"].err.mean(),
                         "MAE cut/grad": h[h.cls != "stable"].err.mean(),
                         "MAE cut@start": h[h.cut_at_gop_start == 1].err.mean()}
                    bm = "linear" if model == "none" else model
                    b = g[(g.features == "base") & (g.model == bm)].set_index(["clip_id", "gop", "level_q0"]).err
                    hh = h.set_index(["clip_id", "gop", "level_q0"]).err
                    if name != "base":
                        m, lo, hi = boot(hh - b.reindex(hh.index), h.clip_id.to_numpy())
                        r["diff vs base [CI]"] = f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]"
                    else:
                        r["diff vs base [CI]"] = ""
                    out.append(r)
        L += [pd.DataFrame(out).round(2).to_markdown(index=False), ""]
    L += ["Notes: 'prev' = use the previous GOP's q_fit as the estimate (diff vs the linear base). 'cut@start' = a "
          "scene cut at frame 0 of the GOP (7 GOPs in the whole set), where the previous GOP should be uninformative."]
    open(f"{OUT}/prevgop_gate.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
