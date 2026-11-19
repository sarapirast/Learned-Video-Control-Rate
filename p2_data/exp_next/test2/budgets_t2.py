"""test2 budget table + causal base-QP estimate (exp_next/test2/PLAN.md step 7). No encodes, nothing fitted on test2.

Same definitions as scripts/budgets_v1.py (copied, not changed):
  budget  B = clip mean of constant-QP-q0 slice bits per GOP, q0 in 24/30/36/42 (the clip's own curves)
  q_fit   hindsight QP spending exactly B on the GOP's own curve (log-bits interpolated over QP 18-50)
  base_qp_est_k<k>  the recorded estimator of budgets_v1.py (linear OLS, first pass at QP 32), refitted here on the
          SAME v1 train rows in the same order (v1 budgets.csv + v1 fp_bits), then applied to test2 rows. For non-train
          rows budgets_v1.py uses exactly this all-train fit, so the parity clips must reproduce v1 budgets.csv.
Inputs: data/v1/320x180 (fit) and $P2_DATA (default data/t2/320x180; rd/rd_native.parquet, features/fp_bits.parquet,
gops.csv). Out: $P2_DATA/budgets.csv (same columns as v1's). Refuses to overwrite a differing file.

  /scratch1/aayushso/envs/ee599/bin/python -I exp_next/test2/budgets_t2.py [--check]
--check: parity clips vs v1 budgets.csv (every column except split must match).
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

V1 = "/scratch1/aayushso/ee599/data/v1/320x180"
T2 = os.environ.get("P2_DATA") or "/scratch1/aayushso/ee599/data/t2/320x180"
LEVELS = (24, 30, 36, 42)
KS = (0, 2, 5, 10, 29)
QMIN, QMAX = 18, 50
FQ = 32


def budget_table(rd, gops):        # verbatim logic of budgets_v1.py "budget table"
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
    return pd.DataFrame(rows).merge(gops[["clip_id", "gop", "split", "group", "label", "cls"]], on=["clip_id", "gop"])


def fpwide(root):
    fp = pd.read_parquet(f"{root}/features/fp_bits.parquet")
    w = fp.pivot_table(index=["encoder", "fp_qp", "clip_id", "gop"], columns="frame", values="fp_slice_bits")
    return np.log2(np.maximum(w, 8))


def feats(fpw, sub, enc, k):       # budgets_v1.py feats()
    f = fpw.loc[(enc, FQ)]
    X = pd.DataFrame({"lb": np.log2(sub.budget_bits.to_numpy() / 30)}, index=sub.index)
    idx = list(zip(sub.clip_id, sub.gop))
    X["fp0"] = f.loc[idx, 0].to_numpy()
    if k >= 1:
        X["fpP"] = np.log2((2 ** f.loc[idx, list(range(1, k + 1))]).mean(1)).to_numpy()
    return X


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    assert os.path.realpath(T2) != os.path.realpath(V1), "P2_DATA points at v1"
    out = f"{T2}/budgets.csv"
    if a.check:
        t2 = pd.read_csv(out)
        v1 = pd.read_csv(f"{V1}/budgets.csv")
        p = t2[t2.split == "parity"]
        key = ["encoder", "clip_id", "gop", "level_q0"]
        m = p.merge(v1, on=key, suffixes=("", "_v1"))
        assert len(m) == len(p) and len(p), (len(m), len(p))
        bad = []
        for c in v1.columns:
            if c in key or c == "split":
                continue
            x, y = m[c], m[f"{c}_v1"]
            same = (np.allclose(x, y, rtol=0, atol=1e-9) if pd.api.types.is_numeric_dtype(x)
                    else (x.fillna("") == y.fillna("")).all())
            if not same:
                bad.append(c)
        print(f"budgets parity: {len(p)} rows ({p.clip_id.nunique()} clips); mismatched columns: {bad or 'none'}")
        sys.exit(1 if bad else 0)

    v1b = pd.read_csv(f"{V1}/budgets.csv")             # v1 train rows: targets, in budgets_v1.py's row order
    fpw1 = fpwide(V1)
    gops = pd.read_csv(f"{T2}/gops.csv")
    gops["cls"] = np.where(gops.label.isin(["cut", "gradual"]), "cut/gradual", "stable")
    bt = budget_table(pd.read_parquet(f"{T2}/rd/rd_native.parquet"), gops)
    assert set(bt.split) <= {"test2", "parity"}, set(bt.split)
    fpw2 = fpwide(T2)
    for enc in ("x264", "x265"):
        sub1 = v1b[v1b.encoder == enc]
        tr = (sub1.split == "train").to_numpy()
        sub2 = bt[bt.encoder == enc]
        for k in KS:
            X1 = feats(fpw1, sub1, enc, k)
            m = LinearRegression().fit(X1[tr], sub1.q_fit.to_numpy()[tr])
            bt.loc[sub2.index, f"base_qp_est_k{k}"] = m.predict(feats(fpw2, sub2, enc, k))
    bt = bt[list(v1b.columns)]
    txt = bt.to_csv(index=False)
    if os.path.exists(out) and open(out).read() != txt:
        sys.exit(f"{out} exists and differs; move it away first")
    open(out, "w").write(txt)
    print(f"-> {out}: {len(bt)} rows, {bt.clip_id.nunique()} clips, splits {bt.split.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
