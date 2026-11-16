"""Experiment 2 report: handoff (540k learner for frames 0..29-m, final4 for the last m) vs final4 and vs the learner
alone. Pre-registration: exp_next/exp2/PREREG.md.

Inputs: results_v1/next/exp2/rows_<enc>_val_*of4.pkl (hybrid episodes); final4's stored row per (GOP, level, k)
(rcwork_v1/<enc>_resh infos 'ctrl'); the learner alone = its stored val eval (rcwork_v1/<enc>_lfqp/results_rl/
cql_ppo_k<k>_fixed_st540k_s<seed>/eval.pkl). Val only; level-24-hole episodes excluded from the gate.
Gate (m = 10): hybrid - final4, seeds averaged per episode, pooled over both encoders and k 0/5, 95% clip
bootstrap (each clip carries both encoders): point >= 0, CI lower bound > -0.05 dB, and mean |spend error| of the
hybrid <= final4's + 0.5 percentage points on the same episodes.

  python -I exp_next/exp2/report.py
Out: results_v1/next/exp2/report.md, episodes.parquet
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import metrics  # noqa: E402

RC = "/scratch1/aayushso/rcwork_v1"
OUT = "/scratch1/aayushso/ee599/results_v1/next/exp2"
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)])
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def fmt(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" + (" *" if t[1] > 0 or t[2] < 0 else "")


def main():
    rows = []
    for enc in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
        files = sorted(glob.glob(f"{OUT}/rows_{enc}_val_*of4.pkl"))
        assert len(files) == 4, (enc, files)
        h = [r for f in files for r in pickle.load(open(f, "rb"))]
        lab = {}
        for k in (0, 5):
            for s in (0, 1, 2):
                ev = pickle.load(open(f"{RC}/{enc}_lfqp/results_rl/cql_ppo_k{k}_fixed_st540k_s{s}/eval.pkl", "rb"))
                for r in ev["res"][("fixed", k, "val")]:
                    lab[(r["gid"], r["budget"], k, s)] = r
        for r in h:
            g, b, k, s = r["gid"], r["level"], r["k"], r["seed"]
            cv, B = infos[g]["curve"], infos[g]["budget"][b]
            c = infos[g]["ctrl"][(b, k)]
            le = lab[(g, b, k, s)]
            rows.append({"enc": enc, "gid": g, "clip": r["clip"], "level": b, "k": k, "seed": s, "m": r["m"],
                         "hole": B > max(cv["bits"]), "score": r["score"], "rho": r["bits"] / B,
                         "A": float(r["psnr"] - metrics.psnr_at_bits(cv, r["bits"])),
                         "final4": c["score"], "rho_f4": c["bits"] / B, "learner": le["score"],
                         "rho_l": le["bits"] / B})
    d = pd.DataFrame(rows)
    d.to_parquet(f"{OUT}/episodes.parquet")
    key = ["enc", "gid", "clip", "level", "k", "m", "hole"]
    a = d.assign(err=100 * (d.rho - 1).abs(), err_f4=100 * (d.rho_f4 - 1).abs(), err_l=100 * (d.rho_l - 1).abs())
    e = a.groupby(key)[["score", "final4", "learner", "err", "err_f4", "err_l", "A"]].mean().reset_index()
    L = ["# Exp 2: handoff -- learner first, final4 for the last m frames (exp_next/exp2/report.py)", "",
         "Val, score in dB, seeds averaged per episode, 95% clip bootstrap ('*' = CI excludes 0). Gate at m = 10, "
         "level-24-hole episodes excluded. 'learner' = the 540k learner alone (m = 0).", ""]
    g = e[(e.m == 10) & ~e.hole]
    t = boot(g.score - g.final4, g["clip"])
    err_h, err_f = g.err.mean(), g.err_f4.mean()
    ok = t[0] >= 0 and t[1] > -0.05 and err_h <= err_f + 0.5
    L += ["## GATE (m = 10, both encoders, k 0/5)", "",
          f"- hybrid - final4: {fmt(t)} (n {len(g)})",
          f"- mean |spend error|: hybrid {err_h:.2f}% vs final4 {err_f:.2f}% (limit final4 + 0.5 = {err_f + 0.5:.2f}%)",
          f"- per encoder: " + "; ".join(f"{en} {fmt(boot(x.score - x.final4, x['clip']))}"
                                          for en, x in g.groupby("enc")),
          f"- per k: " + "; ".join(f"k{k} {(x.score - x.final4).mean():+.3f}" for k, x in g.groupby("k")),
          f"- **{'PASS' if ok else 'FAIL'}** (point >= 0, CI lower bound > -0.05, spend error within +0.5 pp)", ""]
    rows = []
    for m, x in e[~e.hole].groupby("m"):
        rows.append({"m": m, "hybrid": x.score.mean(), "final4": x.final4.mean(), "learner": x.learner.mean(),
                     "hybrid - final4": fmt(boot(x.score - x.final4, x["clip"])),
                     "hybrid - learner": fmt(boot(x.score - x.learner, x["clip"])),
                     "|err| hybrid %": x.err.mean(), "|err| final4 %": x.err_f4.mean(),
                     "|err| learner %": x.err_l.mean(), "A hybrid": x.A.mean()})
    L += ["## All m (both encoders, k 0/5, hole excluded)", "", pd.DataFrame(rows).round(3).to_markdown(index=False),
          ""]
    for en in ("x264", "x265"):
        rows = []
        for (m, k), x in e[~e.hole & (e.enc == en)].groupby(["m", "k"]):
            rows.append({"m": m, "k": k, "hybrid": x.score.mean(), "final4": x.final4.mean(),
                         "learner": x.learner.mean(), "hybrid - final4": fmt(boot(x.score - x.final4, x["clip"])),
                         "|err| hybrid %": x.err.mean(), "|err| final4 %": x.err_f4.mean()})
        L += [f"## {en} by m x k", "", pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
    s = d[(d.m == 10) & ~d.hole].groupby("seed").apply(lambda x: (x.score - x.final4).mean(), include_groups=False)
    L += ["## m = 10 per seed (hybrid - final4)", "", s.round(3).to_markdown(), "",
          f"With the hole included, m = 10: {fmt(boot(e[e.m == 10].score - e[e.m == 10].final4, e[e.m == 10]['clip']))}",
          ""]
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
