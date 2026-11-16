"""Pre-written gates for tracker item 40: CQL->PPO with 540k PPO steps (cql_ppo_st540k@prev, previous-GOP base).

(a) still improving: on VAL, 540k - 180k (same k and seed, paired), pooled over k 0/5/29, > 0 with a CI excluding 0 on
    at least one encoder.
(b) vs the baseline: on VAL, 540k - final4, pooled over k 0/2/5/10/29, > 0 with a CI excluding 0 on at least one
    encoder. Per k and test reported either way.
Also: score, budget use and % of episodes over at 60k / 180k / 540k.
Input: results_v1/lfq_compare_<codec>_final4.csv ('ctrl' = final4). CIs = 95% bootstrap over clips ('*' = excludes 0).
An encoder whose 540k runs are not all in yet is reported with the (k, seed) pairs it has.

  python -I scripts/gates_40.py [x264,x265]
Out: results_v1/w5/gates_40.md
"""
import sys

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
KS = (0, 2, 5, 10, 29)
STEPS = (("60k", "cql_ppo@prev"), ("180k", "cql_ppo_st180k@prev"), ("540k", "cql_ppo_st540k@prev"))
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    lo, hi = np.percentile(ms, 2.5), np.percentile(ms, 97.5)
    return f"{d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]" + (" *" if lo > 0 or hi < 0 else "")


def main():
    encs = sys.argv[1].split(",") if len(sys.argv) > 1 else ["x264", "x265"]
    L = ["# Gates for tracker 40: CQL->PPO at 540k PPO steps (scripts/gates_40.py)", "",
         "Score in dB (dPSNR_B - 0.17 per 1% over), previous-GOP base. 95% bootstrap over clips ('*' = CI excludes 0). "
         "Source: results_v1/lfq_compare_<codec>_final4.csv.", ""]
    for e in encs:
        d = pd.read_csv(f"{ROOT}/results_v1/lfq_compare_{e}_final4.csv",
                        usecols=["method", "k", "seed", "split", "gid", "clip", "budget", "score", "use", "over",
                                 "ctrl"])
        d = d[d.method.isin([m for _, m in STEPS])]
        new = d[d.method == "cql_ppo_st540k@prev"]
        have = sorted({(int(k), int(s)) for k, s in zip(new.k, new.seed)})
        L += [f"## {e}", "", f"540k (k, seed) present: {have}", ""]
        key = ["split", "k", "seed", "gid", "clip", "budget"]
        W = {lab: d[d.method == m].set_index(key) for lab, m in STEPS}
        # score / use / over by steps, on the (k, seed) pairs where 540k exists
        t = []
        for split in ("val", "test"):
            for lab, _ in STEPS:
                x = W[lab].reset_index()
                x = x[(x.split == split).to_numpy() & np.array([(int(k), int(s)) in have
                                                                 for k, s in zip(x.k, x.seed)], bool)]
                r = {"split": split, "steps": lab, "score": x.score.mean(), "use": x.use.mean(),
                     "% eps over": 100 * x.over.mean()}
                for k in KS:
                    r[f"k{k}"] = x[x.k == k].score.mean()
                t.append(r)
            x = W["540k"].reset_index()
            x = x[x.split == split]
            r = {"split": split, "steps": "final4", "score": x.ctrl.mean()}
            for k in KS:
                r[f"k{k}"] = x[x.k == k].ctrl.mean()
            t.append(r)
        L += ["Mean score (rows restricted to the (k, seed) pairs above):", "",
              pd.DataFrame(t).round(3).to_markdown(index=False), ""]
        # gate (a): 540k - 180k, k 0/5/29
        m = W["540k"].join(W["180k"], how="inner", lsuffix="_n", rsuffix="_o").reset_index()
        t = []
        for split in ("val", "test"):
            x = m[m.split == split]
            r = {"split": split, "n": len(x), "540k - 180k (pooled k 0/5/29)": boot(x.score_n - x.score_o, x["clip"])}
            for k in (0, 5, 29):
                z = x[x.k == k]
                r[f"k{k}"] = f"{(z.score_n - z.score_o).mean():+.3f}"
            t.append(r)
        L += ["### Gate (a): 540k - 180k, paired on GOP x level x k x seed", "", pd.DataFrame(t).to_markdown(index=False),
              ""]
        # gate (b): 540k - final4, all k (seeds averaged per GOP x level x k)
        g = new.groupby(["split", "k", "gid", "clip", "budget"], as_index=False)[["score", "ctrl"]].mean()
        t = []
        for split in ("val", "test"):
            x = g[g.split == split]
            r = {"split": split, "540k - final4 (pooled k)": boot(x.score - x.ctrl, x["clip"])}
            for k in KS:
                z = x[x.k == k]
                r[f"k{k}"] = boot(z.score - z.ctrl, z["clip"]) if len(z) else ""
            t.append(r)
        L += ["### Gate (b): 540k - final4, seeds averaged, paired on GOP x level x k", "",
              pd.DataFrame(t).to_markdown(index=False), ""]
    open(f"{ROOT}/results_v1/w5/gates_40.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
