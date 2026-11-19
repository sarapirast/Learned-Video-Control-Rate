"""test2 previous-GOP base-QP estimate for CQL->PPO @prev (exp_next/test2/PLAN.md step 9). No encodes, nothing fitted
on test2.

scripts/base_prev.py's "+prev linear" model (fixed in advance there): features lb, fp0, (fpP for k >= 1), prev_qeq,
prev_lcal from the controller run 'final3' on GOP n-1 (same clip, level, k); target q_fit; OLS on v1 TRAIN rows with a
predecessor. For non-train rows base_prev.py predicts with exactly this all-train fit, so it is refitted here on the
same v1 rows in the same order (v1 budgets.csv, v1 fp_bits, results_v1/controller_real/final3_<enc>_*.parquet) and
applied to test2, whose GOP n-1 history comes from the test2 final3 run (tag t2final3). A clip's first GOP keeps
base_qp_est (has_prev = 0), as in base_prev.py.

  /scratch1/aayushso/envs/ee599/bin/python -I exp_next/test2/base_prev_t2.py <x264|x265> [--check]
Out: $P2_DATA/budgets_prev_<enc>.csv (columns as v1's). --check: parity rows vs v1 budgets_prev_<enc>.csv.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

ROOT = "/scratch1/aayushso/ee599"
V1 = f"{ROOT}/data/v1/320x180"
T2 = os.environ.get("P2_DATA") or f"{ROOT}/data/t2/320x180"
CTRL = f"{ROOT}/results_v1/controller_real"
KS = (0, 2, 5, 10, 29)


def prep(root, tag, enc, s_p):
    bt = pd.read_csv(f"{root}/budgets.csv").query("encoder == @enc").reset_index(drop=True)
    fp = pd.read_parquet(f"{root}/features/fp_bits.parquet").query("fp_qp == 32 and encoder == @enc")
    fpw = np.log2(np.maximum(fp.pivot_table(index=["clip_id", "gop"], columns="frame", values="fp_slice_bits"), 8))
    fptot = np.log2((2 ** fpw).sum(1))
    files = sorted(glob.glob(f"{CTRL}/{tag}_{enc}_*.parquet"))
    assert files, f"no {tag}_{enc}_*.parquet"
    ctrl = pd.concat([pd.read_parquet(p, columns=["clip_id", "gop", "level_q0", "k", "setting", "budget_bits", "bits",
                                                  "qps"]) for p in files], ignore_index=True)
    assert ctrl.setting.nunique() == 1 and ctrl.setting.iloc[0] == "1.0:9.0:1.0:2.0:3.0:4.0:0.0:1.0:1.0:0.0", \
        ctrl.setting.unique()
    assert not ctrl.duplicated(["clip_id", "gop", "level_q0", "k"]).any()
    ctrl["prev_qeq"] = [np.mean(q[1:]) + s_p * np.log2(b / B) for q, b, B in zip(ctrl.qps, ctrl.bits, ctrl.budget_bits)]
    ctrl["prev_lcal"] = np.log2(ctrl.bits.to_numpy()) - fptot.reindex(list(zip(ctrl.clip_id, ctrl.gop))).to_numpy()
    cidx = ctrl.set_index(["clip_id", "gop", "level_q0", "k"])[["prev_qeq", "prev_lcal"]]
    has_prev = bt.set_index(["clip_id", "gop", "level_q0"]).index
    bt["has_prev"] = pd.Index(list(zip(bt.clip_id, bt.gop - 1, bt.level_q0))).isin(has_prev)
    return bt, fpw, cidx


def design(bt, fpw, cidx, k):          # base_prev.py main(), per k
    idx = list(zip(bt.clip_id, bt.gop))
    X = pd.DataFrame({"lb": np.log2(bt.budget_bits / 30), "fp0": fpw.loc[idx, 0].to_numpy()})
    if k >= 1:
        X["fpP"] = np.log2((2 ** fpw.loc[idx, list(range(1, k + 1))]).mean(1)).to_numpy()
    c = cidx.reindex([(cl, g - 1, lv, k) for cl, g, lv in zip(bt.clip_id, bt.gop, bt.level_q0)])
    hp = bt.has_prev.to_numpy()
    assert c.prev_qeq[hp].notna().all(), "controller result missing for a previous GOP"
    Xp = X.assign(prev_qeq=c.prev_qeq.to_numpy(), prev_lcal=c.prev_lcal.to_numpy())[hp].reset_index(drop=True)
    return Xp, hp, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codec", choices=("x264", "x265"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    enc = a.codec
    assert os.path.realpath(T2) != os.path.realpath(V1), "P2_DATA points at v1"
    out = f"{T2}/budgets_prev_{enc}.csv"
    if a.check:
        t2, v1 = pd.read_csv(out), pd.read_csv(f"{V1}/budgets_prev_{enc}.csv")
        p = t2[t2.split == "parity"]
        key = ["encoder", "clip_id", "gop", "level_q0", "k"]
        m = p.merge(v1, on=key, suffixes=("", "_v1"))
        assert len(m) == len(p) and len(p), (len(m), len(p))
        bad = [c for c in ("q_fit", "has_prev", "base_qp_est", "base_qp_prev", "prev_qeq", "prev_lcal", "cls")
               if not (np.allclose(m[c], m[c + "_v1"], rtol=0, atol=1e-9, equal_nan=True)
                       if pd.api.types.is_numeric_dtype(m[c]) else (m[c] == m[c + "_v1"]).all())]
        print(f"budgets_prev parity {enc}: {len(p)} rows; mismatched columns: {bad or 'none'}")
        sys.exit(1 if bad else 0)

    s_p = json.load(open(f"{V1}/rd/controller_model.json"))[enc]["s_p"]
    bt1, fpw1, c1 = prep(V1, "final3", enc, s_p)
    bt2, fpw2, c2 = prep(T2, "t2final3", enc, s_p)
    assert set(bt2.split) <= {"test2", "parity"}
    out_rows = []
    for k in KS:
        Xp1, hp1, _ = design(bt1, fpw1, c1, k)
        tr = (bt1.split[hp1] == "train").to_numpy()
        lm = LinearRegression().fit(Xp1[tr], bt1.q_fit.to_numpy()[hp1][tr])
        Xp2, hp2, cc = design(bt2, fpw2, c2, k)
        o = bt2[["encoder", "clip_id", "gop", "level_q0", "split", "cls", "q_fit", "has_prev"]].copy()
        o["k"] = k
        o["base_qp_est"] = bt2[f"base_qp_est_k{k}"]
        o["base_qp_prev"] = o.base_qp_est
        if hp2.any():
            o.loc[hp2, "base_qp_prev"] = lm.predict(Xp2)
        o["prev_qeq"] = cc.prev_qeq.to_numpy()
        o["prev_lcal"] = cc.prev_lcal.to_numpy()
        out_rows.append(o)
    O = pd.concat(out_rows, ignore_index=True)
    O["has_prev"] = O.has_prev.astype(int)
    txt = O.to_csv(index=False)
    if os.path.exists(out) and open(out).read() != txt:
        sys.exit(f"{out} exists and differs; move it away first")
    open(out, "w").write(txt)
    print(f"-> {out}: {len(O)} rows, {O.clip_id.nunique()} clips")


if __name__ == "__main__":
    main()
