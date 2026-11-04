"""Compare the k curve of the two budget arms (orig = own-GOP CQP spend, dec = spend x s, s~U(0.8,1.25)) on data v1.

Reads Pavneet's RL eval.pkl files through his experiments/analysis.py helpers (no encodes).
  python scripts/v1_arm_compare.py x264      -> results_v1/x264_arm_compare.md
Test split, seeds averaged per (GOP, budget) first. 'vs k=0' is the paired difference to the same method at k=0
in the same arm (95% CI, normal approx as in his metrics.paired_ci). Cut/stable use the v1 GOP label
(cut + gradual vs stable).
"""
import os
import sys

import numpy as np
import pandas as pd

REPO = "/scratch1/aayushso/ee599/repo-pavneet"
sys.path.insert(0, REPO)
from experiments import analysis as A  # noqa: E402
from rclib import config as C, runner  # noqa: E402

codec = sys.argv[1] if len(sys.argv) > 1 else "x264"
ROOT = "/scratch1/aayushso/rcwork_v1"
METHODS = [("bc", "BC"), ("lagr", "Lagrangian PPO"), ("cql_ppo", "CQL->PPO")]
rows, missing = [], []
for arm in ("orig", "dec"):
    C.WORK = os.path.join(ROOT, f"{codec}_{arm}")
    df = A.load_runs(False)
    if not len(df):
        continue
    sa = A.seed_avg(df)
    ceil = A.ceiling(False)
    infos = runner.Stages("infos", False).load("infos")
    lab = {g: x["gop"].get("label", "") for g, x in infos.items()}
    for m, name in METHODS:
        ks = sorted(sa.loc[sa["method"] == m, "train_k"].unique())
        base = None
        for k in ks:
            sub = A.pick(sa, "test", method=m, train_k=k, mode="fixed", k=k)
            if not len(sub):
                continue
            s = A.summarize(sub, ceil)
            nseed = df[(df.method == m) & (df.train_k == k)]["seed"].nunique()
            if nseed < 3:
                missing.append(f"{arm} {m} k={k}: {nseed} of 3 seeds")
            if base is None:
                base, d = sub, (np.nan, np.nan)
            else:
                d = A.paired(sub, base)
            is_cut = sub["gid"].map(lab).isin(["cut", "gradual"])
            rows.append({"arm": arm, "method": name, "k": int(k), "seeds": nseed, "n": s["n"],
                         "score": s["score"], "ci": s["ci"], "saving": s["saving"], "over %": s["over %"],
                         "share of search gain": s.get("share of search gain", np.nan),
                         "vs k=0": "" if k == ks[0] else f"{d[0]:+.2f} ± {d[1]:.2f}",
                         "score stable": sub.loc[~is_cut, "score"].mean(), "score cut": sub.loc[is_cut, "score"].mean()})

t = pd.DataFrame(rows)
lines = [f"# Budget arms compared ({codec}, data v1, test)", "",
         "- orig: budget = the GOP's own constant-QP spend (Pavneet's definition; leaks the whole-GOP cost, C1).",
         "- dec: budget = that spend x s, s ~ U(0.8, 1.25) per (GOP, budget QP); per-frame costs normalised by the "
         "episode's own budget. Removes the exact-spend leak; does not remove the GOP-level cost signal entirely.",
         "- score = % saving at equal PSNR vs constant QP - 2 x % over budget; 'vs k=0' = paired diff, same method/arm.",
         "- search gain share is against each arm's own hindsight search.", ""]
for m in t["method"].unique() if len(t) else []:
    lines += [f"## {m}", "", t[t.method == m].drop(columns="method").round(3).to_markdown(index=False), ""]
lines += ["## Missing seeds", ""] + ([f"- {x}" for x in missing] or ["- none"])
t.to_csv(f"/scratch1/aayushso/ee599/results_v1/{codec}_arm_compare.csv", index=False)
out = f"/scratch1/aayushso/ee599/results_v1/{codec}_arm_compare.md"
open(out, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
