"""Final-week item 5: metric sensitivity (no encodes). Re-score stored per-episode rows as
score_lambda = dPSNR_B - lambda x max(0, % over), lambda in {0, 0.085, 0.17, 0.34, 0.68} dB per 1 %, with the 100 dB
PSNR cap; R3 (k5, 180k, seeds 3-5 averaged per episode) and final4, plus R3 360k and CQL->PPO 540k (context) and
final4 + shift (x265). Hole excluded. Rule: exp_next/fw/PLAN.md.

  python -I exp_next/fw/metric_sens.py --split val
Out: results_v1/next/fw/metric_sens_<split>.md
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/final")
import report as R  # noqa: E402  (sets RC_METRIC=dpsnr; Scorer, loaders)
from shift_report import boot, fmt  # noqa: E402

LAMS = (0.0, 0.085, 0.17, 0.34, 0.68)
FINE = np.round(np.arange(0.0, 1.0001, 0.01), 3)
OUT = "/scratch1/aayushso/ee599/results_v1/next/fw"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("val", "test"), required=True)
    a = ap.parse_args()
    L = [f"# Metric sensitivity, {a.split} (EXPLORATORY; exp_next/fw/metric_sens.py)", "",
         "score_lambda = dPSNR_B - lambda x max(0, % over budget); stored rows, 100 dB PSNR cap, k5, hole excluded; "
         "R3 = 180k model, seeds 3-5 averaged per episode. R3 was trained at lambda 0.17 and is NOT retrained, so other "
         "lambdas show how the comparison depends on the price, not what a learner trained at that price would do.", ""]
    if a.split == "test":
        L += ["**POST-HOC re-analysis of the sealed test rows (Aayush OK 11-17):** the stored rows of the single 11-16 test "
              "pass, re-scored at other overshoot prices; no new encodes, models or choices. Descriptive only; the "
              "pre-registered test result is lambda 0.17.", ""]
    for enc in ("x264", "x265"):
        S = R.Scorer(enc, cap=True)
        d = pd.DataFrame(R.load_r3(enc, a.split, S) + R.load_shift(enc, a.split, S) + R.load_540k(enc, a.split, S))
        d = d[(~d.hole) & (d.k == 5)].copy()
        d["over"] = 100 * np.maximum(d.rho - 1, 0)
        d["dpsnr"] = d.score + 0.17 * d.over
        assert np.allclose(d.dpsnr - 0.17 * d.over, d.score)
        key = ["gid", "clip", "level", "cls"]
        L += [f"## {enc}", ""]
        rows = []
        for lam in LAMS:
            d["s"] = d.dpsnr - lam * d.over
            p = d.groupby(key + ["method"]).s.mean().unstack("method").reset_index()
            prim = p.dropna(subset=["R3 180k", "final4"])
            r = {"lambda": lam, "R3 - final4": fmt(boot(prim["R3 180k"] - prim.final4, prim["clip"])),
                 "R3": f"{prim['R3 180k'].mean():+.3f}", "final4": f"{prim.final4.mean():+.3f}"}
            for m in [c for c in p.columns if c not in key + ["R3 180k", "final4"]]:
                q = p.dropna(subset=["R3 180k", m])
                r[f"R3 - {m}"] = fmt(boot(q["R3 180k"] - q[m], q["clip"]))
            rows.append(r)
        L += [pd.DataFrame(rows).to_markdown(index=False), ""]
        ov = d.groupby("method").agg(n=("over", "size"), pct_over=("over", lambda x: 100 * (x > 0).mean()),
                                     mean_over_when_over=("over", lambda x: x[x > 0].mean()),
                                     dpsnr=("dpsnr", "mean")).round(3)
        L += ["Overshoot profile (per seed-episode):", "", ov.to_markdown(), ""]
        diffs = []
        for lam in FINE:
            d["s"] = d.dpsnr - lam * d.over
            p = d[d.method.isin(["R3 180k", "final4"])].groupby(key + ["method"]).s.mean().unstack("method").dropna()
            diffs.append((p["R3 180k"] - p.final4).mean())
        diffs = np.array(diffs)
        cross = [float(FINE[i]) for i in range(1, len(FINE)) if np.sign(diffs[i]) != np.sign(diffs[i - 1])]
        L += [f"- R3 - final4 (mean) on a 0.01 grid over lambda 0-1: {diffs[0]:+.3f} at 0, {diffs[17]:+.3f} at 0.17, "
              f"{diffs[-1]:+.3f} at 1.0; sign change at lambda = {cross if cross else 'none in [0, 1]'}", ""]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/metric_sens_{a.split}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
