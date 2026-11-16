"""Exp 7 Part 2 report (x264, val, DESCRIPTIVE ONLY per exp_next/exp7/PREREG.md). Four systems on the val same-clip
8-GOP streams: stream RL (bc_ppo, seeds averaged per case) or the retuned L = 2 rule, each with constant QP per GOP
(curves, = Part 1) or final4 (k5) inside each GOP at B_g (real encodes). Stream-level metric as Part 1; 95 % cluster
bootstrap over source groups (same as stream_rl.cboot); per-GOP check |bits - B_g| / B_g reported separately.

  python -I exp_next/exp7/part2_report.py [x264]
Out: results_v1/next/exp7/part2_<enc>.md
"""
import glob
import pickle
import sys

import numpy as np
import pandas as pd

ENC = sys.argv[1] if len(sys.argv) > 1 else "x264"
OUT = "/scratch1/aayushso/ee599/results_v1/next/exp7"


def cboot(d, groups, n=4000, seed=0):
    u, inv = np.unique(groups, return_inverse=True)
    s, c = np.bincount(inv, d, len(u)), np.bincount(inv, minlength=len(u))
    w = np.random.default_rng(seed).multinomial(len(u), [1 / len(u)] * len(u), n)
    m = (w @ s) / (w @ c)
    return f"{np.mean(d):+.3f} [{np.percentile(m, 2.5):+.3f}, {np.percentile(m, 97.5):+.3f}]"


def main():
    split = sys.argv[2] if len(sys.argv) > 2 else "val"
    pat = f"{OUT}/part2_{ENC}_[0-9]*of*.pkl" if split == "val" else f"{OUT}/part2_{ENC}_{split}_*of*.pkl"
    rows = [r for f in sorted(glob.glob(pat)) if "_limit" not in f for r in pickle.load(open(f, "rb"))]
    recs, gops = [], []
    for r in rows:
        kind, grp, st, q0, s = r["case"]
        for sysn in ("cqp", "f4"):
            x = r[sysn]
            recs.append({"ctrl": r["ctrl"], "seed": r["seed"], "sys": sysn, "grp": grp, "case": (st, q0, s),
                         "score": x["score"], "dpsnr": x["dpsnr"], "use": x["use"], "over_pct": x["over_pct"]})
        gops += [{"ctrl": r["ctrl"], "err": (g["bits"] - g["B_g"]) / g["B_g"]} for g in r["gops_f4"]]
    d = pd.DataFrame(recs)
    p = d.groupby(["ctrl", "sys", "case", "grp"])[["score", "dpsnr", "use", "over_pct"]].mean().reset_index()
    w = p.pivot_table(index=["case", "grp"], columns=["ctrl", "sys"], values="score").reset_index()
    g = w["grp"].to_numpy()
    col = lambda c, s: w[(c, s)].to_numpy()  # noqa: E731
    L = [f"# Exp 7 Part 2: zero-shot hierarchy, {ENC}, val (exp_next/exp7/part2.py, part2_report.py)", "",
         "**Descriptive only** (pre-registered): few same-clip streams; the retuned rule was tuned on these streams. "
         f"{len(w)} cases, {len(set(g))} source groups; bc_ppo = Pavneet's stored BC->PPO L = 2, seeds 0-2 averaged per "
         "case; final4 = 1.0:6:1.0:2:3:4:1:1:1:0:3 at k5 inside each GOP at B_g = the stream controller's own predicted "
         "spend; history from the stream's previous GOP.", "",
         "| system | score | dPSNR_B | signed spend err % | % streams > 1 % over | p90 abs err % |", "|---|---|---|---|---|---|"]
    for c in ("bc_ppo", "rule"):
        for s in ("cqp", "f4"):
            x = p[(p.ctrl == c) & (p.sys == s)]
            u = x.use.to_numpy()
            L.append(f"| {'stream RL (bc_ppo)' if c == 'bc_ppo' else 'retuned rule'} + {'constant QP' if s == 'cqp' else 'final4'} | "
                     f"{x.score.mean():+.4f} | {x.dpsnr.mean():+.4f} | {100 * (u - 1).mean():+.2f} | "
                     f"{100 * np.mean(100 * (u - 1) > 1):.1f} | {100 * np.quantile(np.abs(u - 1), 0.9):.2f} |")
    L += ["", "Paired differences (cluster bootstrap over source groups):", "",
          f"- RL + final4 - RL + constant QP: {cboot(col('bc_ppo', 'f4') - col('bc_ppo', 'cqp'), g)}",
          f"- rule + final4 - rule + constant QP: {cboot(col('rule', 'f4') - col('rule', 'cqp'), g)}",
          f"- RL + final4 - rule + final4: {cboot(col('bc_ppo', 'f4') - col('rule', 'f4'), g)}",
          f"- RL + constant QP - rule + constant QP (= Part 1): {cboot(col('bc_ppo', 'cqp') - col('rule', 'cqp'), g)}",
          f"- RL + final4 - rule + constant QP: {cboot(col('bc_ppo', 'f4') - col('rule', 'cqp'), g)}", ""]
    ge = pd.DataFrame(gops)
    L += ["Per-GOP check with final4 inside, |GOP bits - B_g| / B_g (%):", "",
          "| controller | GOPs | mean | median | p90 | max | signed mean |", "|---|---|---|---|---|---|---|"]
    for c, x in ge.groupby("ctrl"):
        a = 100 * x.err.abs()
        L.append(f"| {c} | {len(x)} | {a.mean():.2f} | {a.median():.2f} | {a.quantile(0.9):.2f} | {a.max():.2f} | "
                 f"{100 * x.err.mean():+.2f} |")
    L += ["", f"Check (mean about 2 % or less): {'met' if (100 * ge.err.abs()).mean() <= 2.0 else 'NOT met'}", ""]
    open(f"{OUT}/part2_{ENC}{'' if split == 'val' else '_' + split}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
