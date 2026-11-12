"""Stage A of tracker item 31: causal base-QP estimate that also uses the PREVIOUS GOP of the same clip. No encodes.

Budgets are clip-level (budgets.csv: every GOP of a clip has the same budget per level) and a clip's GOPs are encoded
in order, so before GOP n starts the encoder knows how GOP n-1 went. Here "how it went" = the final controller run
(results_v1/controller_real/<tag>_<codec>_*.parquet, one setting) on GOP n-1 at the SAME level and k:
  prev_qeq  = mean P-frame QP + s_p x log2(bits / budget)  (the constant QP that would have hit the budget, through
              the controller's rate-model slope s_p, rd/controller_model.json)
  prev_lcal = log2(bits of GOP n-1) - log2(its first-pass total)  (how expensive the clip encodes vs its first pass)
Features (first pass at QP 32, as budgets_v1.py): lb = log2(B / 30), fp0 = log2 first-pass bits of frame 0, and for
k >= 1 fpP = log2 mean first-pass bits of frames 1..k; "+prev" adds prev_qeq and prev_lcal.
Target = q_fit (hindsight constant QP that spends exactly the budget). Model fixed in advance: linear (OLS), fitted on
train only; train rows are out-of-fold by source group (GroupKFold 5, as budgets_v1.py). gbm is reported alongside.
The first GOP of each clip has no predecessor: base_qp_prev = budgets.csv base_qp_est_k (has_prev = 0).
Caveat: GOP n-1 is the CONTROLLER's encode; a learner deployed clip-sequentially would see its own. Check reported:
spread of prev_qeq for the same GOP x level across k (different QP plans, same GOP) -- small = policy-insensitive.

Gate A (written before the run): val MAE at k0 better than budgets.csv base_qp_est_k0 by >= 1 QP, 95% clip-bootstrap
CI excluding 0 (rows with a predecessor).

  python -I scripts/base_prev.py <x264|x265> [--tag final3]
Out: data/v1/320x180/base_prev_model.json (per encoder and k: feature order, linear coefficients fitted on ALL train
     rows = the model applied to val/test; scripts/controller_real.py history mode uses it on its own GOP n-1),
     data/v1/320x180/budgets_prev_<codec>.csv (encoder, clip_id, gop, level_q0, k, split, cls, q_fit, base_qp_est,
     base_qp_prev, has_prev, prev_qeq, prev_lcal) and results_v1/gates/base_prev_<codec>.md
"""
import argparse
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
KS = (0, 2, 5, 10, 29)
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
    ap = argparse.ArgumentParser()
    ap.add_argument("codec", choices=("x264", "x265"))
    ap.add_argument("--tag", default="final3")
    a = ap.parse_args()
    enc = a.codec
    bt = pd.read_csv(f"{D}/budgets.csv").query("encoder == @enc").reset_index(drop=True)
    fp = pd.read_parquet(f"{D}/features/fp_bits.parquet").query("fp_qp == 32 and encoder == @enc")
    fpw = np.log2(np.maximum(fp.pivot_table(index=["clip_id", "gop"], columns="frame", values="fp_slice_bits"), 8))
    fptot = np.log2((2 ** fpw).sum(1))
    s_p = json.load(open(f"{D}/rd/controller_model.json"))[enc]["s_p"]

    files = sorted(glob.glob(f"{ROOT}/results_v1/controller_real/{a.tag}_{enc}_*.parquet"))
    ctrl = pd.concat([pd.read_parquet(p, columns=["clip_id", "gop", "level_q0", "k", "setting", "budget_bits", "bits",
                                                  "qps"]) for p in files], ignore_index=True)
    assert ctrl.setting.nunique() == 1, ctrl.setting.unique()
    setting = ctrl.setting.iloc[0]
    assert not ctrl.duplicated(["clip_id", "gop", "level_q0", "k"]).any()
    ctrl["prev_qeq"] = [np.mean(q[1:]) + s_p * np.log2(b / B) for q, b, B in zip(ctrl.qps, ctrl.bits, ctrl.budget_bits)]
    ctrl["prev_lcal"] = np.log2(ctrl.bits.to_numpy()) - fptot.reindex(list(zip(ctrl.clip_id, ctrl.gop))).to_numpy()
    # policy-sensitivity check: spread of prev_qeq across k for the same GOP x level
    spread = ctrl.groupby(["clip_id", "gop", "level_q0"]).prev_qeq.agg(lambda s: s.max() - s.min())
    cidx = ctrl.set_index(["clip_id", "gop", "level_q0", "k"])[["prev_qeq", "prev_lcal"]]

    has_prev = bt.set_index(["clip_id", "gop", "level_q0"]).index
    prev_key = list(zip(bt.clip_id, bt.gop - 1, bt.level_q0))
    bt["has_prev"] = pd.Index(prev_key).isin(has_prev)
    idx = list(zip(bt.clip_id, bt.gop))
    y = bt.q_fit.to_numpy()
    out, evals, coefs = [], [], {}
    for k in KS:
        X = pd.DataFrame({"lb": np.log2(bt.budget_bits / 30), "fp0": fpw.loc[idx, 0].to_numpy()})
        if k >= 1:
            X["fpP"] = np.log2((2 ** fpw.loc[idx, list(range(1, k + 1))]).mean(1)).to_numpy()
        c = cidx.reindex([(cl, g - 1, lv, k) for cl, g, lv in zip(bt.clip_id, bt.gop, bt.level_q0)])
        hp = bt.has_prev.to_numpy()
        assert c.prev_qeq[hp].notna().all(), "controller result missing for a previous GOP"
        sub = hp.copy()
        Xp = X.assign(prev_qeq=c.prev_qeq.to_numpy(), prev_lcal=c.prev_lcal.to_numpy())[sub].reset_index(drop=True)
        Xb = X[sub].reset_index(drop=True)
        ys, tr, grp = y[sub], (bt.split[sub] == "train").to_numpy(), bt.group[sub].to_numpy()
        lm = LinearRegression().fit(Xp[tr], ys[tr])
        coefs[str(k)] = {"features": list(Xp.columns), "coef": [float(v) for v in lm.coef_],
                         "intercept": float(lm.intercept_)}
        preds = {"est (budgets.csv)": bt[f"base_qp_est_k{k}"].to_numpy()[sub],
                 "base refit linear": fit_predict(Xb, ys, tr, grp, LinearRegression),
                 "+prev linear": fit_predict(Xp, ys, tr, grp, LinearRegression),
                 "base refit gbm": fit_predict(Xb, ys, tr, grp, gbm),
                 "+prev gbm": fit_predict(Xp, ys, tr, grp, gbm)}
        rows = bt[sub][["clip_id", "gop", "level_q0", "split", "cls"]].reset_index(drop=True)
        for name, p in preds.items():
            evals.append(rows.assign(k=k, model=name, err=np.abs(p - ys), bias=p - ys))
        o = bt[["encoder", "clip_id", "gop", "level_q0", "split", "cls", "q_fit", "has_prev"]].copy()
        o["k"] = k
        o["base_qp_est"] = bt[f"base_qp_est_k{k}"]
        o["base_qp_prev"] = o.base_qp_est
        o.loc[sub, "base_qp_prev"] = preds["+prev linear"]
        o["prev_qeq"] = c.prev_qeq.to_numpy()
        o["prev_lcal"] = c.prev_lcal.to_numpy()
        out.append(o)
    mf = f"{D}/base_prev_model.json"
    allm = json.load(open(mf)) if os.path.exists(mf) else {}
    allm[enc] = {"tag": a.tag, "setting": setting, "s_p": s_p, "fp_qp": 32, "k": coefs}
    json.dump(allm, open(mf, "w"), indent=1)
    O = pd.concat(out, ignore_index=True)
    O["has_prev"] = O.has_prev.astype(int)
    O.to_csv(f"{D}/budgets_prev_{enc}.csv", index=False)
    E = pd.concat(evals, ignore_index=True)

    L = [f"# Stage A (tracker 31): base-QP estimate with the previous GOP, {enc} (scripts/base_prev.py)", "",
         f"History = controller run '{a.tag}' setting {setting} on GOP n-1 (same clip, level, k). Target q_fit. "
         f"Rows = GOPs with a predecessor x 4 levels ({int(bt.has_prev.sum())} of {len(bt)}; first GOPs keep "
         "budgets.csv). MAE / bias in QP; diff = MAE(model) - MAE(est budgets.csv), 95% bootstrap CI over clips. "
         "Gate A: val k0 diff <= -1.0 QP with CI excluding 0.", "",
         f"Policy-sensitivity check: range of prev_qeq across k (same GOP x level): median {spread.median():.2f}, "
         f"p90 {spread.quantile(0.9):.2f}, max {spread.max():.2f} QP.", ""]
    gate = None
    for split in ("val", "test", "train"):
        x = E[E.split == split]
        tab = []
        for (k, model), g in x.groupby(["k", "model"], sort=False):
            r = {"k": k, "model": model, "n": len(g), "MAE": g.err.mean(), "bias": g.bias.mean(),
                 "MAE stable": g[g.cls == "stable"].err.mean(), "MAE cut/grad": g[g.cls != "stable"].err.mean()}
            if model != "est (budgets.csv)":
                b = x[(x.k == k) & (x.model == "est (budgets.csv)")]
                m, lo, hi = boot(g.err.to_numpy() - b.err.to_numpy(), g.clip_id.to_numpy())
                r["diff vs est [CI]"] = f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]"
                if split == "val" and k == 0 and model == "+prev linear":
                    gate = (m, lo, hi)
            else:
                r["diff vs est [CI]"] = ""
            tab.append(r)
        L += [f"## {split}", "", pd.DataFrame(tab).round(2).to_markdown(index=False), ""]
    ok = gate[0] <= -1.0 and gate[2] < 0
    L.insert(5, f"**Gate A ({'PASS' if ok else 'FAIL'}):** val k0 +prev linear vs est: {gate[0]:+.2f} "
                f"[{gate[1]:+.2f}, {gate[2]:+.2f}] QP.")
    L.insert(6, "")
    open(f"{ROOT}/results_v1/gates/base_prev_{enc}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
