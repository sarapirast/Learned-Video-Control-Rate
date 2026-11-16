"""Pre-written gates for tracker items 37/38: are the learners under-trained?

37: residual RL on final4 with 180k PPO steps (res_st180k@hist) vs 60k (res@hist).
38: CQL->PPO on the previous-GOP base with 180k PPO steps (cql_ppo_st180k@prev) vs 60k (cql_ppo@prev).
GATE (written before results): on VAL, 180k - 60k (same k and seed, paired) > 0 pooled over k 0/5/29 with a CI
excluding 0 on at least one encoder -> "under-trained". Also reported: test, per k, and both vs final4.
Pairing: GOP x level x k x seed (only (k, seed) pairs present for both); 95% bootstrap over clips.
Input: results_v1/lfq_compare_<codec>_final4.csv ('ctrl' = final4).

  python -I scripts/gates_37_38.py
Out: results_v1/w5/gates_37_38.md
"""
import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
KS = (0, 5, 29)
PAIRS = (("37 residual", "res_st180k@hist", "res@hist"), ("38 CQL->PPO", "cql_ppo_st180k@prev", "cql_ppo@prev"))
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    lo, hi = np.percentile(ms, 2.5), np.percentile(ms, 97.5)
    return f"{d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]" + (" *" if lo > 0 or hi < 0 else "")


def main():
    L = ["# Gates for tracker 37/38: 3x PPO steps (180k vs 60k) (scripts/gates_37_38.py)", "",
         "Score in dB (dPSNR_B - 0.17 per 1% over). Paired on GOP x level x k x seed; 95% bootstrap over clips "
         "('*' = CI excludes 0). k 0/5/29. Source: results_v1/lfq_compare_<codec>_final4.csv.", ""]
    for e in ("x264", "x265"):
        d = pd.read_csv(f"{ROOT}/results_v1/lfq_compare_{e}_final4.csv",
                        usecols=["method", "k", "seed", "split", "gid", "clip", "budget", "score", "use", "over",
                                 "ctrl"])
        d = d[d.k.isin(KS)]
        L += [f"## {e}", ""]
        for item, new, old in PAIRS:
            key = ["split", "k", "seed", "gid", "clip", "budget"]
            a = d[d.method == new].set_index(key)
            b = d[d.method == old].set_index(key)
            m = a.join(b, how="inner", lsuffix="_new", rsuffix="_old").reset_index()
            have = sorted({(int(k), int(s)) for k, s in zip(m.k, m.seed)})
            t = []
            for split in ("val", "test"):
                x = m[m.split == split]
                r = {"split": split, "n": len(x), "60k": x.score_old.mean(), "180k": x.score_new.mean(),
                     "180k - 60k (pooled k)": boot(x.score_new - x.score_old, x["clip"])}
                for k in KS:
                    z = x[x.k == k]
                    r[f"k{k}"] = f"{(z.score_new - z.score_old).mean():+.3f}"
                r["use 60k/180k"] = f"{x.use_old.mean():.3f} / {x.use_new.mean():.3f}"
                r["% over 60k/180k"] = f"{100 * x.over_old.mean():.1f} / {100 * x.over_new.mean():.1f}"
                r["180k - final4"] = boot(x.score_new - x.ctrl_new, x["clip"])
                t.append(r)
            L += [f"### {item}: {new} - {old}", "", f"(k, seed) pairs: {have}", "",
                  pd.DataFrame(t).round(3).to_markdown(index=False), ""]
    open(f"{ROOT}/results_v1/w5/gates_37_38.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
