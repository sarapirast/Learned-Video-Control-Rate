"""Final report (F + baselines + Exp 7) from stored rows. Pre-registration: exp_next/final/PREREG.md (branch A).

  python -I exp_next/final/report.py --split val      dry run (R3 rows = the stored val rows, parity 48/48 checked)
  python -I exp_next/final/report.py --split test     after the approved test pass
Every method is rescored with one function (rclib.metrics.score, dPSNR_B - 0.17 x %over) on the same curves and
budgets (rcwork_v1/<enc>_resh infos); flat GOPs are not in those infos; level-24-hole episodes excluded in the primary.
PRIMARY: R3 (180k model, fresh seeds 3-5 averaged per episode) - final4 at k5, per encoder, 95 % clip bootstrap.
Out: results_v1/final/report_<split>.md
"""
import argparse
import glob
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp5")
from rclib import metrics  # noqa: E402
from shift_report import boot, fmt  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
OUT = f"{ROOT}/results_v1/final"
R3RUN = "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s{s}"
ABR_M = {"x264": 0.90, "x265": 0.93}
KS = (0, 2, 5, 10, 29)


class Scorer:
    def __init__(self, enc):
        self.inf = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))

    def row(self, method, gid, level, k, bits, psnr, seed=-1, stored=None):
        x = self.inf[gid]
        cv, B = x["curve"], x["budget"][level]
        s = float(metrics.score(bits, psnr, cv, B))
        if stored is not None:
            assert abs(s - stored) < 1e-6, (method, gid, level, s, stored)
        return {"method": method, "gid": gid, "clip": x["gop"]["clip"], "level": level, "k": k, "seed": seed,
                "score": s, "A": float(psnr - metrics.psnr_at_bits(cv, bits)), "rho": bits / B,
                "hole": B > max(cv["bits"]),
                "cls": "cut/gradual" if x["gop"]["label"] in ("cut", "gradual") else "stable"}


def load_r3(enc, split, S):
    rows = []
    if split == "test":
        res = pickle.load(open(f"{OUT}/r3_test_{enc}.pkl", "rb"))
    else:
        res = {}
        for s in (3, 4, 5):
            d = f"{RC}/{enc}_resh/results_rl/{R3RUN.format(s=s)}"
            res[(s, "180k")] = pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"][(180993, "fixed", 5, "val")]
            res[(s, "360k")] = pickle.load(open(f"{d}/eval.pkl", "rb"))["res"][("fixed", 5, "val")]
    for (s, lab), rr in res.items():
        for r in rr:
            rows.append(S.row(f"R3 {lab}", r["gid"], r["budget"], 5, r["bits"], r["psnr"], s, r["score"]))
            if s == 3 and lab == "180k":
                ctrl = S.inf[r["gid"]]["ctrl"][(r["budget"], 5)]
                rows.append({**S.row("final4", r["gid"], r["budget"], 5, ctrl["bits"],
                                     ctrl["dpsnr"] + metrics.psnr_at_bits(S.inf[r["gid"]]["curve"], S.inf[r["gid"]]["budget"][r["budget"]])),
                             "score": ctrl["score"]})
    return rows


def load_final4_k(enc, split, S):
    d = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{ROOT}/results_v1/controller_real/final4_{enc}_{split}_*.parquet"))
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    d = d[d.gid.isin(S.inf)]
    return [S.row("final4", r.gid, int(r.level_q0), int(r.k), float(r.bits), float(r.psnr_yuv)) for r in d.itertuples()]


def load_abr(enc, split, S):
    fs = [f for f in glob.glob(f"{ROOT}/results_v1/next/exp10/rows_{enc}_{split}_*.parquet") if "_limit" not in f]
    if not fs:
        return []
    d = pd.concat(pd.read_parquet(f) for f in fs)
    d = d[np.isclose(d.margin, ABR_M[enc])]
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    d = d[d.gid.isin(S.inf)]
    return [S.row(f"ABR m{ABR_M[enc]:.2f}", r.gid, int(r.level_q0), int(r.k), float(r.bits), float(r.psnr_yuv)) for r in d.itertuples()]


def load_540k(enc, split, S):
    rows = []
    for k in KS:
        for s in (0, 1, 2):
            p = f"{RC}/{enc}_lfqp/results_rl/cql_ppo_k{k}_fixed_st540k_s{s}/eval.pkl"
            if not os.path.exists(p):
                continue
            for r in pickle.load(open(p, "rb"))["res"].get(("fixed", k, split), []):
                if r["gid"] in S.inf:
                    rows.append(S.row("CQL->PPO 540k", r["gid"], r["budget"], k, r["bits"], r["psnr"], s))
    return rows


def load_shift(enc, split, S):
    f = f"{ROOT}/results_v1/next/exp5/shift_rows_{enc}_{split}_qbin_k5_0of1.pkl"
    if enc != "x265" or not os.path.exists(f):
        return []
    return [S.row("final4 + shift", r["gid"], r["level"], 5, r["bits"], r["psnr"], -1, r["score"]) for r in pickle.load(open(f, "rb"))]


def dec(x):
    return {"n": len(x), "score": x.score.mean(), "A": x.A.mean(), "E-P": (x.score - x.A).mean(),
            "mean |err| %": 100 * (x.rho - 1).abs().mean(), "p90 |err| %": 100 * (x.rho - 1).abs().quantile(0.9),
            "signed err %": 100 * (x.rho - 1).mean(), "% over": 100 * (x.rho > 1).mean()}


def exp7_section(split):
    L = ["## Exp 7 (stream level; frozen configuration)", ""]
    for enc in ("x264", "x265"):
        f = f"{OUT}/exp7_{split}_{enc}.pkl"
        if not os.path.exists(f):
            L.append(f"- {enc}: no {split} rows (exp_next/exp7/test_eval.py --split {split} not run)")
            continue
        R = pickle.load(open(f, "rb"))
        for n in (8, 16, 32):
            pol = [R[k] for k in R if k[0] == "policy" and k[1] == n]
            if not pol:
                continue
            kinds = ("clip", "mixed") if n == 8 else ("clip",)
            for kind in kinds:
                idx = [i for i, r in enumerate(pol[0]) if r["kind"] == kind]
                p = np.mean([[rr[i]["score"] for i in idx] for rr in pol], axis=0)
                g = np.array([pol[0][i]["group"] for i in idx])
                for lab, key in (("retuned rule", ("rule_retuned", n, 2)), ("rule as reported", ("rule_reported", n, 2))):
                    q = np.array([R[key][i]["score"] for i in idx])
                    L.append(f"- {enc} N={n} {kind}: policy - {lab} {fmt(boot(p - q, g))} (n {len(idx)})"
                             + ("  <- PRIMARY" if n == 8 and kind == "clip" and lab == "retuned rule" else ""))
    L += ["", "Part 2 (x264, descriptive): see results_v1/next/exp7/part2_x264" + ("" if split == "val" else f"_{split}") + ".md", ""]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("val", "test"), required=True)
    a = ap.parse_args()
    L = [f"# Final results, {a.split} (exp_next/final/report.py)", "",
         "Pre-registration exp_next/final/PREREG.md (branch A). All methods rescored with one metric function on the same "
         "curves and budgets; hole excluded in the primary; 95 % clip bootstrap ('*' excludes 0). final4's and the 540k "
         "reference's test rows existed before this pass (final4 run 11-11; 540k eval default val,test).", ""]
    for enc in ("x264", "x265"):
        S = Scorer(enc)
        d = pd.DataFrame(load_r3(enc, a.split, S) + load_shift(enc, a.split, S) + load_abr(enc, a.split, S)
                         + load_540k(enc, a.split, S))
        y = d[(~d.hole) & (d.k == 5)]
        key = ["gid", "clip", "level", "cls"]
        p = y.groupby(key + ["method"]).score.mean().unstack("method").reset_index()
        L += [f"## {enc}", ""]
        prim = p.dropna(subset=["R3 180k", "final4"])
        L.append(f"- **PRIMARY R3 (180k) - final4, k5: {fmt(boot(prim['R3 180k'] - prim.final4, prim['clip']))}** (n {len(prim)})")
        for m in [c for c in p.columns if c not in key + ["R3 180k", "final4"]]:
            q = p.dropna(subset=["R3 180k", m])
            if len(q):
                L.append(f"- R3 (180k) - {m}: {fmt(boot(q['R3 180k'] - q[m], q['clip']))} (n {len(q)})")
        L.append("- per seed (R3 180k - final4): " + "; ".join(
            f"s{s} {(x.set_index(key).score - p.set_index(key).final4.reindex(x.set_index(key).index)).mean():+.3f}"
            for s, x in y[y.method == "R3 180k"].groupby("seed")))
        L.append("- by class (R3 180k - final4): " + "; ".join(
            f"{c} {fmt(boot(x['R3 180k'] - x.final4, x['clip']))} (n {len(x)})" for c, x in prim.groupby("cls")))
        L.append("- by level (R3 180k - final4): " + "; ".join(
            f"L{lv} {(x['R3 180k'] - x.final4).mean():+.3f}" for lv, x in prim.groupby("level")))
        L += ["", "Decomposition at k5 (hole excluded):", "",
              pd.DataFrame([{"method": m, **dec(x)} for m, x in y.groupby("method")]).round(3).to_markdown(index=False), ""]
        kc = pd.DataFrame(load_final4_k(enc, a.split, S) + load_abr(enc, a.split, S) + load_540k(enc, a.split, S))
        kc = kc[~kc.hole]
        L += ["k-curve (existing runs; R3 was tested only at k5):", "",
              kc.pivot_table(index="method", columns="k", values="score", aggfunc="mean").round(3).to_markdown(), ""]
    L += exp7_section(a.split)
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report_{a.split}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
