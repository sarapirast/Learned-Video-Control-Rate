"""Tracker item 39: Lagrangian over-budget price sweep for the CQL->PPO learner with the previous-GOP base (@prev).

lam = price per unit over-budget in the training reward. Arms (rcwork_v1/<codec>_lfqp): cql_ppo@prev (relative reward,
no extra price), lagr_lam0.17@prev, lagr@prev (lam 0.34, rl.py default), lagr_lam0.68@prev; k 0/5/29 x 3 seeds.
On x265, lam 0.17 is the same run as cql_ppo@prev (the relative reward differs from the Lagrangian only by
0.17 x over_ref, which is 0 on x265 train references; tracker 31).
Input: results_v1/lfq_compare_<codec>_final4.csv (scripts/lfq_compare.py <codec> --ctrl-tag final4; one row per
episode; 'ctrl' = the frozen controller final4 on the same GOP x level x k). Seeds averaged per GOP x level x k, then
pooled over k 0/5/29. lam is picked on val by pooled score; test is reported for that pick.
CIs: 95% bootstrap over clips, paired.

  python -I scripts/lam_sweep.py
Out: results_v1/w5/lam_sweep.md
"""
import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
KS = (0, 5, 29)
ARMS = {"cql_ppo@prev": "rel (cql_ppo)", "lagr_lam0.17@prev": "0.17", "lagr@prev": "0.34", "lagr_lam0.68@prev": "0.68"}
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    return f"{d.mean():+.3f} [{np.percentile(ms, 2.5):+.3f}, {np.percentile(ms, 97.5):+.3f}]"


def main():
    L = ["# Item 39: over-budget price (lam) sweep, CQL->PPO @prev (scripts/lam_sweep.py)", "",
         "Score in dB (dPSNR_B - 0.17 per 1% over). k 0/5/29 pooled, seeds averaged, flat GOPs excluded. "
         "diff vs final4 / vs lam 0.17: paired on GOP x level x k, 95% bootstrap over clips. "
         "Source: results_v1/lfq_compare_<codec>_final4.csv.", ""]
    for e in ("x264", "x265"):
        d = pd.read_csv(f"{ROOT}/results_v1/lfq_compare_{e}_final4.csv",
                        usecols=["method", "k", "seed", "split", "gid", "clip", "budget", "score", "use", "over",
                                 "ctrl"])
        d = d[d.method.isin(ARMS) & d.k.isin(KS)]
        g = d.groupby(["method", "split", "k", "gid", "clip", "budget"], as_index=False)[
            ["score", "use", "over", "ctrl"]].mean()
        L += [f"## {e}", ""]
        if e == "x265":
            L += ["lam 0.17 = cql_ppo@prev on x265 (identical runs, see docstring).", ""]
        pick = None
        for split in ("val", "test"):
            t = []
            ref = g[(g.method == "lagr_lam0.17@prev") & (g.split == split)].set_index(["k", "gid", "budget"])
            for m, lab in ARMS.items():
                x = g[(g.method == m) & (g.split == split)]
                if x.empty:
                    continue
                r = {"lam": lab, "n": len(x), "score": x.score.mean(), "use": x.use.mean(),
                     "over_%": 100 * x.over.mean()}
                for k in KS:
                    r[f"k{k}"] = x[x.k == k].score.mean()
                r["vs final4"] = boot(x.score - x.ctrl, x["clip"])
                if m != "lagr_lam0.17@prev":
                    b = ref.reindex(list(zip(x.k, x.gid, x.budget)))
                    r["vs lam 0.17"] = boot(x.score.to_numpy() - b.score.to_numpy(), x["clip"])
                t.append(r)
            T = pd.DataFrame(t)
            if split == "val":
                pick = T.loc[T.score.idxmax(), "lam"]
            L += [f"### {split}" + (f" (pick on val: lam {pick})" if split == "test" else ""), "",
                  T.round(3).to_markdown(index=False), ""]
            if split == "val":
                L += [f"final4 on these rows: {g[(g.split == split) & (g.method == 'lagr@prev')].ctrl.mean():.3f}",
                      ""]
    open(f"{ROOT}/results_v1/w5/lam_sweep.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
