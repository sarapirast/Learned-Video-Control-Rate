"""Re-analysis of finished results (no encodes, D30 step 1): do the headline claims survive clip-level CIs and
natural cuts only?

For each claim (a paired score difference A - B on the test cases both methods have):
  case CI      95 % bootstrap over (GOP, budget) cases, as every report so far
  clip CI      95 % cluster bootstrap over source clips (a clip contributes all its GOPs and budgets); a spliced GOP
               is its own cluster, since its frames come from two clips
  natural      the same difference with spliced GOPs removed (clip CI)
  seeds        the difference computed per training seed (seed i of A vs seed i of B, or vs B's single run)
Verdict: 'holds' if the clip CI on all cases and on natural GOPs both exclude 0 with the original sign.

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork RC_BUDGETS=30,38 python experiments/reanalysis.py
  (writes $RC_REPORTS/reanalysis_report.md; for the 5-budget work dirs it also pairs 5- vs 2-budget training)
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, metrics  # noqa: E402
from experiments.breakdown import case_budget, collect, group_of  # noqa: E402
from rclib import env as E  # noqa: E402

TWO_BUDGET_WORK = {"x265": "/scratch1/pbanga/rcwork", "x264": "/scratch1/pbanga/rcwork_x264"}

CLAIMS = [   # (A, B, what it supports)
    ("lagr fixed:0", "bc fixed:0", "constrained RL beats imitation (k=0)"),
    ("lagr fixed:5", "bc fixed:5", "constrained RL beats imitation (k=5)"),
    ("pid fixed:0", "bc fixed:0", "PID-Lagrangian beats imitation (k=0)"),
    ("lagr fixed:0", "bc_fb2 fixed:0", "constrained RL beats imitation + feedback control (k=0)"),
    ("lagr fixed:5", "bc_fb2 fixed:5", "constrained RL beats imitation + feedback control (k=5)"),
    ("bc_fb2 fixed:0", "bc fixed:0", "feedback control helps imitation (k=0)"),
    ("lagr fixed:5", "cql_ppo fixed:5", "constrained RL beats penalty RL (k=5)"),
    ("cql_ppo fixed:5", "bc fixed:5", "PPO fine-tuning beats imitation (k=5)"),
    ("bc fixed:5", "cql fixed:5", "imitation beats offline RL (k=5)"),
    ("cql_ppo fixed:1", "cql_ppo fixed:0", "lookahead: k 0 -> 1"),
    ("cql_ppo fixed:2", "cql_ppo fixed:1", "lookahead: k 1 -> 2"),
    ("cql_ppo fixed:3", "cql_ppo fixed:2", "lookahead: k 2 -> 3"),
    ("cql_ppo fixed:5", "cql_ppo fixed:3", "lookahead: k 3 -> 5"),
    ("cql_ppo fixed:29", "cql_ppo fixed:3", "lookahead: k 3 -> 29 (flat beyond 3)"),
    ("cql_ppo fixed:5", "cql_ppo fixed:0", "lookahead: k 0 -> 5"),
    ("lagr fixed:5", "lagr fixed:0", "lookahead for constrained RL: k 0 -> 5"),
    ("cql_ppo fixed:5", "la_rule k=5", "learned policy beats the hand lookahead rule (k=5)"),
    ("ensemble fixed:5", "cql_ppo fixed:5", "3-seed ensemble helps"),
    ("cql_ppo fixed:5", "cql_ppo fixed:5 no-fp", "first-pass features matter"),
    ("cql_ppo cut_trig:5", "cql_ppo fixed:0", "cut-triggered lookahead beats none"),
    ("cql_ppo scene_trunc:5", "cql_ppo fixed:5", "scene-truncated window vs fixed k=5"),
    ("hindsight search", "lagr fixed:5", "gap: search vs best learner"),
    ("lagr fixed:0", "own abr", "constrained RL vs the encoder's ABR (same budget)"),
    ("lagr fixed:5", "own 2pass", "constrained RL vs the encoder's two-pass (same budget)"),
    ("lagr fixed:5", "own 2pass +AQ", "constrained RL vs two-pass with the encoder's defaults"),
    ("lagr fixed:0", "rule k=0", "constrained RL vs the causal feedback rule"),
    ("bc_fb2 fixed:0", "rule k=0", "imitation + feedback vs the causal feedback rule"),
    ("lagr fixed:0", "static k=0", "constrained RL vs STATIC on the causal base QP (causal env)"),
    ("lagr fixed:0", "best constant QP (hindsight)", "constrained RL vs the best constant QP in hindsight (causal env)"),
]


def case_table(infos, items):
    """method -> DataFrame indexed by (gid, b) with per-seed scores (list) and their mean."""
    out = {}
    for name, d in items.items():
        rec = []
        for (g, b), lst in d.items():
            cv, B = infos[g]["curve"], case_budget(infos, g, b)
            rec.append((g, b, [float(metrics.score(bt, ps, cv, B)) for bt, ps in lst]))
        df = pd.DataFrame(rec, columns=["gid", "b", "seeds"]).set_index(["gid", "b"]).sort_index()
        df["score"] = df.seeds.apply(np.mean)
        out[name] = df
    return out


def cluster_of(info):
    g = info["gop"]
    if C.V1:              # dataset v1: resample by source group (film, shoot or uploader)
        return g["group"]
    return f"splice:{g['id']}" if g["family"] == "splice" else g["clip"]


def cboot(d, groups, n=4000, seed=0):
    d = np.asarray(d, float)
    u, inv = np.unique(np.asarray(groups), return_inverse=True)
    sums, cnt = np.bincount(inv, d), np.bincount(inv)
    idx = np.random.default_rng(seed).integers(len(u), size=(n, len(u)))
    m = sums[idx].sum(1) / cnt[idx].sum(1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), len(u)


def boot(d, n=4000, seed=0):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(seed).integers(0, len(d), (n, len(d)))].mean(1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def ci(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


def excludes0(t, sign):
    return (t[1] > 0) if sign > 0 else (t[2] < 0)


def assess(D, infos, a, b, sel=None):
    if a not in D or b not in D:
        return None
    j = D[a].index.intersection(D[b].index)
    if C.CAUSAL and "hindsight search" in (a, b):   # the search was run at the unscaled budget: s = 1 cases only
        j = [k for k in j if E.causal_scale(k[0], k[1]) == 1.0]
    if sel is not None:
        j = [k for k in j if sel(k)]
    if len(j) < 10:
        return None
    A, B = D[a].loc[j], D[b].loc[j]
    d = A.score.values - B.score.values
    grp = [cluster_of(infos[k[0]]) for k in j]
    nat = np.array([infos[k[0]]["gop"]["family"] != "splice" for k in j])
    r = {"cases": len(j), "case": boot(d), "clip": cboot(d, grp),
         "natural": cboot(d[nat], np.asarray(grp)[nat]) if nat.sum() >= 10 else None}
    na, nb = len(A.seeds.iloc[0]), len(B.seeds.iloc[0])
    if na > 1 and (nb == na or nb == 1):
        r["seeds"] = [float(np.mean([s[i] for s in A.seeds]) - np.mean([s[i if nb > 1 else 0] for s in B.seeds]))
                      for i in range(na)]
    return r


def rows_for(D, infos, claims, sel=None):
    rows = []
    for a, b, what in claims:
        r = assess(D, infos, a, b, sel)
        if r is None:
            continue
        sign = np.sign(r["case"][0]) or 1
        holds = excludes0(r["clip"], sign) and (r["natural"] is not None and excludes0(r["natural"], sign))
        rows.append({"claim": what, "A - B": f"{a} − {b}", "cases": r["cases"], "case CI": ci(r["case"]),
                     f"clip CI ({r['clip'][3]} clusters)": ci(r["clip"]),
                     "natural only (clip CI)": ci(r["natural"]) if r["natural"] else "–",
                     "per seed": ", ".join(f"{x:+.2f}" for x in r.get("seeds", [])) or "–",
                     "verdict": "holds" if holds else ("case-level only" if excludes0(r["case"], sign) else "n.s.")})
    return rows


def main():
    infos, test, items = collect(C.WORK)
    D = case_table(infos, items)
    gm = {g: group_of(infos[g]) for g in test}
    n_clips = len({cluster_of(infos[g]) for g in test})
    L = [f"# Re-analysis: clip-level CIs and natural cuts ({C.CODEC}, budgets {C.BUDGET_QPS}, test)", "",
         f"{len(test)} test GOPs in {n_clips} clusters ({sum(infos[g]['gop']['family'] == 'splice' for g in test)} "
         "spliced GOPs, each its own cluster). Score differences A − B, seeds averaged per case. 'holds' = the "
         "clip-level CI excludes 0 on all cases and on natural (non-spliced) GOPs.", "",
         "## All budgets", "", pd.DataFrame(rows_for(D, infos, CLAIMS)).to_markdown(index=False), ""]
    for b in C.BUDGET_QPS:
        if len(C.BUDGET_QPS) > 2:
            L += [f"## Budget QP {b}", "", pd.DataFrame(rows_for(D, infos, [c for c in CLAIMS if c[2].startswith(('constrained RL beats imitation', 'lookahead: k 0 -> 5', 'lookahead for', 'gap'))],
                                                                 sel=lambda k, b=b: k[1] == b)).to_markdown(index=False), ""]
    cut = [("cql_ppo fixed:5", "cql_ppo fixed:0", "lookahead k 0 -> 5")]
    for grp in ("stable", "natural cut", "spliced"):
        L += [f"## Lookahead by GOP type: {grp}", "",
              pd.DataFrame(rows_for(D, infos, cut, sel=lambda k, grp=grp: grp in gm[k[0]])).to_markdown(index=False), ""]
    if len(C.BUDGET_QPS) > 2 and not C.CAUSAL:   # 5- vs 2-budget training on the shared QP 30/38 test cases
        inf2, _, it2 = collect(TWO_BUDGET_WORK[C.CODEC])
        D2 = case_table(inf2, it2)
        both = {f"{m} [5 budgets]": D[m] for m in D}
        both.update({f"{m} [2 budgets]": D2[m] for m in D2})
        cl = [(f"{m} [5 budgets]", f"{m} [2 budgets]", f"5- vs 2-budget training: {m}")
              for m in ("cql_ppo fixed:0", "cql_ppo fixed:5", "bc fixed:5", "lagr fixed:5", "pid fixed:5")]
        L += ["## Training on 5 vs 2 budgets (QP 30/38 test cases)", "",
              pd.DataFrame(rows_for(both, infos, cl, sel=lambda k: k[1] in (30, 38))).to_markdown(index=False), ""]
    p = os.path.join(C.REPORTS, "reanalysis_report.md")
    os.makedirs(C.REPORTS, exist_ok=True)
    open(p, "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
