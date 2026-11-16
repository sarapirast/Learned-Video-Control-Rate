"""Exp 5b BC-only rung report (fold). PREREG: exp_next/exp5/PREREG_BC.md.

Rows: bc_rows_<enc>_fold.pkl (bc_eval.py; seeds averaged per episode) vs final4 (stored ctrl row = static_score) and
vs the mean[t]-only arm (Exp 5a pooled:bit fold rows: same mean vector, same bit cap, offset 0), paired on
(GOP, level, k), 95% clip bootstrap, level-24-hole episodes excluded. Decomposition A / E-P / spend as Exp 5a.

  python -I exp_next/exp5/bc_report.py
Out: results_v1/next/exp5/bc_fold.md
"""
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

RC = "/scratch1/aayushso/rcwork_v1"
OUT = "/scratch1/aayushso/ee599/results_v1/next/exp5"


def rows(enc, infos):
    out = []
    for r in pickle.load(open(f"{OUT}/bc_rows_{enc}_fold.pkl", "rb")):
        g, lv, k = r["gid"], r["level"], r["k"]
        cv, B, c = infos[g]["curve"], infos[g]["budget"][lv], infos[g]["ctrl"][(lv, k)]
        assert abs(r["static_score"] - c["score"]) < 1e-9
        p4 = c["dpsnr"] + metrics.psnr_at_bits(cv, B)
        out.append({"enc": enc, "gid": g, "clip": r["clip"], "level": lv, "k": k, "seed": r["seed"],
                    "hole": B > max(cv["bits"]), "score": r["score"], "final4": c["score"], "rho": r["bits"] / B,
                    "A": float(r["psnr"] - metrics.psnr_at_bits(cv, r["bits"])), "rho_f4": c["bits"] / B,
                    "A_f4": float(p4 - metrics.psnr_at_bits(cv, c["bits"])),
                    "zero_share": float(np.mean(np.array(r["acts"]) == 0)),
                    "cls": "cut/gradual" if infos[g]["gop"]["label"] in ("cut", "gradual") else "stable"})
    mean_only = {}
    for r in pickle.load(open(f"{OUT}/shift_rows_{enc}_fold_0of1.pkl", "rb")):
        if "pooled:bit" in r["variants"]:
            mean_only[(r["gid"], r["level"], r["k"])] = r["score"]
    d = pd.DataFrame(out)
    d["mean_only"] = [mean_only[(g, lv, k)] for g, lv, k in zip(d.gid, d.level, d.k)]
    return d


def dec(x, f4=False):
    s, A, rho = (x.final4, x.A_f4, x.rho_f4) if f4 else (x.score, x.A, x.rho)
    return {"score": s.mean(), "A": A.mean(), "E-P": (s - A).mean(), "mean |err| %": 100 * (rho - 1).abs().mean(),
            "p90 |err| %": 100 * (rho - 1).abs().quantile(0.9), "signed err %": 100 * (rho - 1).mean(),
            "% over": 100 * (rho > 1).mean()}


def main():
    L = ["# Exp 5b BC-only rung, fold (exp_next/exp5/bc_report.py)", "",
         "final4 + mean[t] + BC (argmax, 13 offsets), bit cap. Seeds 0/1/2 averaged per episode (per-seed means "
         "listed). Paired, 95% clip bootstrap over the 8 fold clips ('*' excludes 0), hole excluded. mean-only = Exp 5a "
         "pooled:bit (same mean[t] and cap, offset 0). Caveat: final4's rate model saw the fold clips.", ""]
    dec_rows = []
    for enc in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
        d = rows(enc, infos)
        y = d[~d.hole]
        p = y.groupby(["gid", "clip", "level", "k", "cls"])[["score", "final4", "mean_only", "zero_share"]].mean() \
            .reset_index()
        L += [f"## {enc}", ""]
        for k, x in [("k0+k5", p)] + [(f"k{k}", q) for k, q in p.groupby("k")]:
            L.append(f"- {k}: BC - final4 {fmt(boot(x.score - x.final4, x['clip']))}; BC - mean-only "
                     f"{fmt(boot(x.score - x.mean_only, x['clip']))}; mean-only - final4 "
                     f"{fmt(boot(x.mean_only - x.final4, x['clip']))} (n {len(x)})")
        L += ["- per seed (BC - final4, k0+k5): " + "; ".join(
            f"s{s} {(q.score - q.final4).mean():+.3f}" for s, q in y.groupby("seed")),
              "- cut/gradual vs stable (BC - final4): " + "; ".join(
            f"{c} {fmt(boot(q.score - q.final4, q['clip']))} (n {len(q)})" for c, q in p.groupby("cls")),
              f"- share of frames with BC offset 0: {p.zero_share.mean():.2f}", ""]
        for k, x in y.groupby("k"):
            dec_rows += [{"enc": enc, "k": k, "method": "final4 + mean + BC", **dec(x)},
                         {"enc": enc, "k": k, "method": "final4", **dec(x, True)}]
    L += ["## Decomposition (seed-level episodes)", "", pd.DataFrame(dec_rows).round(3).to_markdown(index=False), ""]
    open(f"{OUT}/bc_fold.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
