"""Phase K (#1): does constrained RL turn an imitation policy into a budget-safe one? No new encodes.

Per lookahead k, on test (GOP, budget) cases with seeds averaged: imitation (BC), offline RL + PPO (CQL->PPO), and the
budget-constrained RL variants (Lagrangian / PID trained from the offline start, and fine-tuned from CQL->PPO), plus
the 3-seed ensemble. Columns: score, saving, share of cases >1 % and >5 % over budget, mean and 95th-percentile
overshoot, and paired differences (95 % bootstrap over cases) against BC and against CQL->PPO.

  python experiments/constraint.py           # uses RC_CODEC / RC_WORK; writes results/<codec>/constraint_report.md
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, metrics  # noqa: E402
from experiments.breakdown import boot, collect, fmt_ci  # noqa: E402

KS = (0, 5, 10)
METHODS = ("bc", "cql_ppo", "lagr", "pid", "lagr_ft", "pid_ft", "ensemble")
NAMES = {"bc": "BC (imitation)", "cql_ppo": "CQL->PPO", "lagr": "Lagrangian RL", "pid": "PID-Lagrangian RL",
         "lagr_ft": "CQL->PPO + Lagrangian fine-tune", "pid_ft": "CQL->PPO + PID fine-tune",
         "ensemble": "CQL->PPO 3-seed ensemble"}


def cases(infos, d):
    rec = []
    for (g, b), lst in d.items():
        cv, B = infos[g]["curve"], infos[g]["budget"][b]
        sv = np.mean([float(metrics.saving(bt, ps, cv)) for bt, ps in lst])
        sc = np.mean([float(metrics.score(bt, ps, cv, B)) for bt, ps in lst])
        ov = np.mean([float(metrics.overshoot(bt, B)) for bt, _ in lst])
        o1 = np.mean([bt > 1.01 * B for bt, _ in lst])
        o5 = np.mean([bt > 1.05 * B for bt, _ in lst])
        rec.append((g, b, sc, sv, ov, o1, o5))
    return pd.DataFrame(rec, columns=["gid", "b", "score", "saving", "over", "o1", "o5"]).set_index(["gid", "b"]).sort_index()


def main():
    infos, _, items = collect(C.WORK)
    out = [f"# Constrained RL vs imitation ({C.CODEC}, test)", "",
           "Cases = (GOP, budget) pairs, seeds averaged. over % = % above budget (0 when within). "
           "Differences: 95 % bootstrap over cases; for the over-budget shares the difference is in percentage points.", ""]
    summary = []
    for k in KS:
        D = {m: cases(infos, items[f"{m} fixed:{k}"]) for m in METHODS if f"{m} fixed:{k}" in items}
        if "bc" not in D:
            continue
        rows = []
        for m, df in D.items():
            r = {"method": NAMES[m], "n": len(df), "score": df.score.mean(), "saving": df.saving.mean(),
                 ">1% over": f"{100 * df.o1.mean():.0f}%", ">5% over": f"{100 * df.o5.mean():.0f}%",
                 "mean over %": df.over.mean(), "p95 over %": np.percentile(df.over, 95)}
            for ref in ("bc", "cql_ppo"):
                if ref in D and m != ref:
                    j = df.index.intersection(D[ref].index)
                    a, b = df.loc[j], D[ref].loc[j]
                    r[f"score vs {ref}"] = fmt_ci(boot(a.score.values - b.score.values))
                    r[f"saving vs {ref}"] = fmt_ci(boot(a.saving.values - b.saving.values))
                    r[f">1% over vs {ref} (pp)"] = fmt_ci(tuple(100 * x for x in boot(a.o1.values - b.o1.values)))
            rows.append(r)
            summary.append({"k": k, "method": NAMES[m], "score": df.score.mean(), "saving": df.saving.mean(),
                            ">1% over": 100 * df.o1.mean()})
        out += [f"## k = {k}", "", pd.DataFrame(rows).round(2).to_markdown(index=False), ""]
    s = pd.DataFrame(summary)
    out += ["## Summary (score / saving / % of cases >1 % over)", "",
            s.pivot(index="method", columns="k", values="score").round(2).add_prefix("score k=").join(
                s.pivot(index="method", columns="k", values=">1% over").round(0).add_prefix(">1% over k=")).to_markdown(), ""]
    p = os.path.join(C.REPORTS, "constraint_report.md")
    open(p, "w").write("\n".join(out))
    print("\n".join(out))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
