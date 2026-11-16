"""Learners vs every version of the P2 causal controller, on the quality-at-budget metric (dB).

Controller versions (results_v1/controller_real/<tag>_<codec>_<split>_*.parquet, one setting each), rescored exactly as
scripts/lfq_compare.py does (metrics.score under RC_METRIC=dpsnr, budgets/curves from the lfq infos):
  final  = v1 real-encode final run (11-04)
  final2 = v2, tuned for the OLD metric (% saved - 2 x %over)
  final3 = retuned on val under dPSNR_B (tracker 30e)
  final4 = final3 + previous-GOP history (tracker 31 stage B), frozen baseline (tracker 34)
Learners: results_v1/lfq_compare_<codec>_final4.csv (seeds averaged per GOP x level x k). Rows = GOP x level x k
present for every controller version and the learner. Differences paired, 95% bootstrap over clips.

  python -I scripts/ctrl_versions.py
Out: results_v1/w5/ctrl_versions.md
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

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
VERS = ("final", "final2", "final3", "final4")
LEARN = ("bc", "cql_ppo", "lagr_lam0.17", "bc@prev", "cql_ppo@prev", "lagr_lam0.17@prev", "res", "res@hist")
KS = (0, 2, 5, 10, 29)
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    lo, hi = np.percentile(ms, 2.5), np.percentile(ms, 97.5)
    return f"{d.mean():+.2f} [{lo:+.2f}, {hi:+.2f}]" + ("" if lo > 0 or hi < 0 else " ns")


def ctrl_scores(codec, infos):
    out = []
    for t in VERS:
        cp = pd.concat([pd.read_parquet(p) for p in glob.glob(f"{ROOT}/results_v1/controller_real/{t}_{codec}_*.parquet")],
                       ignore_index=True)
        assert cp.setting.nunique() == 1, t
        cp = cp[cp.split.isin(["val", "test"])] if "split" in cp else cp
        for r in cp.itertuples():
            g = f"{r.clip_id}@{30 * r.gop}"
            if g in infos:
                out.append({"ver": t, "gid": g, "budget": int(r.level_q0), "k": int(r.k),
                            "s": float(metrics.score(r.bits, r.psnr_yuv, infos[g]["curve"],
                                                     infos[g]["budget"][int(r.level_q0)])),
                            "use": r.bits / infos[g]["budget"][int(r.level_q0)]})
    c = pd.DataFrame(out)
    return (c.pivot_table(index=["gid", "budget", "k"], columns="ver", values="s"),
            c.groupby("ver").use.mean())


def main():
    L = ["# Learners vs every controller version (scripts/ctrl_versions.py)", "",
         "Score in dB (dPSNR_B - 0.17 per 1% over). final = v1 (11-04); final2 = v2 tuned for the old metric; final3 = "
         "retuned for dPSNR_B; final4 = final3 + previous-GOP history (frozen baseline). Learners seeds-averaged; rows "
         "paired on GOP x level x k; 95% bootstrap over clips ('ns' = CI includes 0). Learner labels as in "
         "lfq_compare: no suffix = causal budgets.csv base QP (res = residual on final3), @prev = previous-GOP base, "
         "@hist = residual on final4.", ""]
    for e in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{e}_lfq/results_infos/infos_learn.pkl", "rb"))
        C, use = ctrl_scores(e, infos)
        d = pd.read_csv(f"{ROOT}/results_v1/lfq_compare_{e}_final4.csv",
                        usecols=["method", "k", "split", "gid", "clip", "budget", "score", "search"])
        d = d[d.method.isin(LEARN)]
        g = d.groupby(["method", "split", "gid", "clip", "budget", "k"], as_index=False)[["score", "search"]].mean()
        W = g.pivot_table(index=["split", "gid", "clip", "budget", "k"], columns="method", values="score")
        srch = g.groupby(["split", "gid", "clip", "budget", "k"]).search.first()
        W = W.join(C, on=["gid", "budget", "k"]).assign(search=srch).reset_index().dropna(subset=list(VERS))
        L += [f"## {e}", "", "Controller budget use (val+test, all k): " +
              ", ".join(f"{v} {use[v]:.3f}" for v in VERS), ""]
        for split in ("val", "test"):
            x = W[W.split == split]
            t = []
            for m in ("search",) + VERS + tuple(m for m in LEARN if m in x):
                r = {"method": m, "pooled k": x[m].mean()}
                for k in KS:
                    r[f"k{k}"] = x[x.k == k][m].mean()
                t.append(r)
            L += [f"### {split}: mean score ({x.gid.nunique()} GOPs, {x['clip'].nunique()} clips)", "",
                  pd.DataFrame(t).round(3).to_markdown(index=False), ""]
            t = []
            for m in [m for m in LEARN if m in x]:
                y = x.dropna(subset=[m])
                r = {"learner (pooled k)": m}
                for v in VERS:
                    r[f"- {v}"] = boot(y[m] - y[v], y["clip"])
                t.append(r)
            L += [f"### {split}: learner - controller version, pooled over k", "",
                  pd.DataFrame(t).to_markdown(index=False), ""]
    os.makedirs(f"{ROOT}/results_v1/w5", exist_ok=True)
    open(f"{ROOT}/results_v1/w5/ctrl_versions.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
