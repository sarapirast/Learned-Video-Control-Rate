"""Figure 1 of the milestone report: share of the search's score captured against lookahead k, with the range over seeds.
Stage 1 (per encoder, rc env): RC_CODEC=.. RC_WORK=.. RC_BUDGETS=30,38 python tools/milestone3_fig.py dump OUT.json
Stage 2:                       python tools/milestone3_fig.py plot x265.json x264.json OUT.png"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
K = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 29]
if sys.argv[1] == "dump":
    from rclib import config as C, metrics
    from experiments.breakdown import collect, case_budget
    infos, test, items = collect(C.WORK)
    def seeds(name):
        d = items[name]; n = max(len(v) for v in d.values()); o = [[] for _ in range(n)]
        for (g, b), l in d.items():
            for i, (bt, ps) in enumerate(l):
                o[i].append(float(metrics.score(bt, ps, infos[g]["curve"], case_budget(infos, g, b))))
        return [float(np.mean(x)) for x in o]
    out = {"search": seeds("hindsight search")[0] if len(seeds("hindsight search")) == 1 else float(np.mean(seeds("hindsight search"))),
           "cql_ppo": {k: seeds(f"cql_ppo fixed:{k}") for k in K}, "lagr": {k: seeds(f"lagr fixed:{k}") for k in (0, 5, 10)}}
    json.dump(out, open(sys.argv[2], "w")); print(C.CODEC, out["search"])
else:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 7.5, "font.family": "DejaVu Sans"})
    f, ax = plt.subplots(1, 2, figsize=(6.6, 1.12), sharey=True)
    for a, p, name in zip(ax, sys.argv[2:4], ("x265", "x264")):
        d = json.load(open(p)); s = 100 / d["search"]
        for key, col, m, lab in (("cql_ppo", "#2A78D6", "o", "CQL→PPO"), ("lagr", "#EE6C35", "s", "Lagrangian PPO")):
            ks = [k for k in K if str(k) in d[key]]; x = [K.index(k) for k in ks]
            v = np.array([d[key][str(k)] for k in ks]) * s; y = v.mean(1)
            a.errorbar(x, y, yerr=[y - v.min(1), v.max(1) - y], color=col, lw=1.2, marker=m, ms=2.8, elinewidth=0.6, capsize=1.2, label=lab)
        a.axhline(0, color="#777777", lw=0.6, ls=":")
        a.set_xticks(range(len(K))); a.set_xticklabels(K); a.set_xlabel("lookahead k", labelpad=1); a.set_title(name, fontsize=7.5, pad=2)
        a.grid(axis="y", color="#E6E6E6", lw=0.5); a.set_axisbelow(True); a.tick_params(length=2, pad=1.5)
        for sp in ("top", "right"): a.spines[sp].set_visible(False)
    ax[0].set_ylabel("% of search score"); ax[1].legend(frameon=False, loc="lower right", fontsize=6.5, handlelength=1.6, borderpad=0, ncol=2)
    f.savefig(sys.argv[4], dpi=300, bbox_inches="tight", pad_inches=0.02)
