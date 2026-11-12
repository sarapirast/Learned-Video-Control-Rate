"""Wide-budget study (D28): results per budget QP, from the same test cases as breakdown.py (no new encodes).

Per budget QP b (RC_BUDGETS), on test GOPs with seeds averaged:
  1. score / saving / >1 % over for the reference points (constant QP, STATIC, encoders' own rate control, hand rules,
     hindsight search) and the learned policies (BC, CQL->PPO, Lagrangian, PID at k = 0, 5, 10)
  2. the lookahead curve of CQL->PPO per budget and the share of the search's saving it captures
  3. paired differences (95 % bootstrap over GOPs) Lagrangian - BC and CQL->PPO k=5 - k=0, per budget

  RC_BUDGETS=26,30,34,38,42 RC_WORK=... RC_REPORTS=results/x265_wide python experiments/budgets.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C  # noqa: E402
from experiments.breakdown import boot, collect, fmt_ci, per_case  # noqa: E402

MAIN = ["constant QP", "STATIC", "own abr", "own 2pass", "own abr_vbv", "rule k=0", "la_rule k=0", "la_rule k=5",
        "bc fixed:0", "bc fixed:5", "bc fixed:10", "cql_ppo fixed:0", "cql_ppo fixed:5", "cql_ppo fixed:10",
        "lagr fixed:0", "lagr fixed:5", "lagr fixed:10", "pid fixed:0", "pid fixed:5", "pid fixed:10",
        "hindsight search"]


def main():
    infos, test, items = collect(C.WORK)
    D = per_case(infos, items)
    bs = list(C.BUDGET_QPS)
    out = [f"# Results per budget QP ({C.CODEC}, test, budgets {bs})", "",
           f"{len(test)} test GOPs; each budget = bits of the encoder's constant QP b on that GOP. score = saving − 2 × % "
           "over budget; >1% = share of GOPs more than 1 % over budget. Seeds averaged per GOP.", ""]
    for col, name in (("score", "Score"), ("saving", "Saving (%) at equal PSNR"), ("over1", "Share >1 % over budget")):
        rows = []
        for m in MAIN:
            if m not in D:
                continue
            g = D[m][col].groupby(level="b").mean()
            rows.append({"method": m, **{f"b={b}": (100 * g.get(b, np.nan) if col == "over1" else g.get(b, np.nan))
                                         for b in bs},
                         "all": 100 * D[m][col].mean() if col == "over1" else D[m][col].mean()})
        out += [f"## {name}", "", pd.DataFrame(rows).round(2).to_markdown(index=False), ""]

    ks = sorted({int(m.split(":")[1]) for m in D if m.startswith("cql_ppo fixed:") and len(m.split()) == 2})
    if ks and "hindsight search" in D:
        hs = D["hindsight search"].saving.groupby(level="b").mean()
        rows = []
        for k in ks:
            g = D[f"cql_ppo fixed:{k}"]
            sc, sv = g.score.groupby(level="b").mean(), g.saving.groupby(level="b").mean()
            rows.append({"k": k, **{f"score b={b}": sc.get(b) for b in bs},
                         **{f"share b={b}": f"{100 * sv.get(b) / hs.get(b):.0f}%" for b in bs}})
        out += ["## Lookahead curve per budget (CQL->PPO)", "",
                "share = CQL->PPO saving / hindsight-search saving at that budget.", "",
                pd.DataFrame(rows).round(2).to_markdown(index=False), ""]

    rows = []
    for a, b_, lab in (("lagr fixed:0", "bc fixed:0", "Lagrangian − BC, k=0"), ("lagr fixed:5", "bc fixed:5", "Lagrangian − BC, k=5"),
                       ("cql_ppo fixed:5", "cql_ppo fixed:0", "CQL->PPO k=5 − k=0"),
                       ("cql_ppo fixed:5", "la_rule k=5", "CQL->PPO − lookahead rule, k=5"),
                       ("hindsight search", "cql_ppo fixed:5", "search − CQL->PPO k=5")):
        if a not in D or b_ not in D:
            continue
        r = {"comparison": lab}
        for b in bs:
            x, y = D[a].xs(b, level="b").score, D[b_].xs(b, level="b").score
            r[f"b={b}"] = fmt_ci(boot((x - y.reindex(x.index)).values))
        rows.append(r)
    if rows:
        out += ["## Paired score differences per budget (95 % bootstrap over GOPs)", "",
                pd.DataFrame(rows).to_markdown(index=False), ""]
    os.makedirs(C.REPORTS, exist_ok=True)
    p = os.path.join(C.REPORTS, "budgets_report.md")
    open(p, "w").write("\n".join(out))
    print("\n".join(out))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
