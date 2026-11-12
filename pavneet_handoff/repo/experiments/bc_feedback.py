"""BC + feedback control (D30 step 3): does imitation plus a simple closed-loop budget correction match constrained RL?

Takes the finished BC policies (results_rl/bc_k{k}_fixed_s{seed}/policy.pt), wraps each in policies.Feedback, tunes
(gain, margin) on val with seed 0, and evaluates every seed on val + test with the chosen setting. Results are
written as results_rl/bc_fb_k{k}_fixed_s{seed}/eval.pkl in the format of experiments/rl.py, so every report
(breakdown, reanalysis, budgets) picks them up as method 'bc_fb'. Real encodes; no training.

  python experiments/bc_feedback.py --k 0          # one job per k
"""
import os
import pickle
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, offrl, policies as P, runner  # noqa: E402
from rclib.runner import log  # noqa: E402

MODES = ("cum", "rem")   # v1 (13729082-93) had only 'cum': overshoot grew with the gain, hence 'rem' (D30)
GAINS = (0.5, 1.0, 2.0, 3.0)
MARGINS = (0.0, 0.03)
QUICK_GRID = (("rem", 2.0, 0.0),)
METHOD = "bc_fb2"


def cli(ap):
    ap.add_argument("--k", type=int, default=0)
    ap.add_argument("--seeds", default="0,1,2")


def mean_score(rows):
    return float(np.mean([r["score"] for r in rows]))


def main():
    a = runner.args(cli)
    rl = runner.Stages("rl")                      # BC models always from the real run
    out = runner.Stages("rl", a.quick)            # --quick: 6 val/test GOPs, one setting, results in results_rl_quick
    infos_st = runner.Stages("infos")
    infos = {g: offrl.slim(x) for g, x in infos_st.load("infos").items()}
    ipath = P.save_infos_for_workers(infos, os.path.join(infos_st.dir, "infos_slim.pkl"))
    curve = runner.Stages("baselines").load("spend_curve")
    ids = {s: sorted(g for g, x in infos.items() if x["gop"]["split"] == s) for s in ("val", "test")}
    if a.quick:
        ids = {s: v[:6] for s, v in ids.items()}
    seeds = [int(x) for x in a.seeds.split(",")]
    envkw = {"k": a.k, "mode": "fixed"}

    def spec(seed, md, g, m):
        base = {"kind": "torch", "path": os.path.join(rl.dir, f"bc_k{a.k}_fixed_s{seed}", "policy.pt")}
        return {"kind": "fb", "base": base, "mode": md, "gain": g, "margin": m, "curve": curve}
    t0 = time.time()
    grid = QUICK_GRID if a.quick else [(md, g, m) for md in MODES for g in GAINS for m in MARGINS]
    tune = {}
    for md, g, m in grid:
        rows = P.evaluate(spec(seeds[0], md, g, m), ipath, ids["val"], desc=f"val {md} gain {g} margin {m}",
                          workers=None, **envkw)
        tune[(md, g, m)] = rows
        log(f"k={a.k} val {md} gain {g} margin {m}: score {mean_score(rows):.2f} "
            f"over {100 * np.mean([r['over'] for r in rows]):.1f}%")
    md, g, m = max(tune, key=lambda x: mean_score(tune[x]))
    log(f"chosen {md} gain {g} margin {m}")
    for seed in seeds:
        name = f"{METHOD}_k{a.k}_fixed_s{seed}"
        if out.done(f"{name}/eval"):
            log(f"{name}: done")
            continue
        src = pickle.load(open(os.path.join(rl.dir, f"bc_k{a.k}_fixed_s{seed}", "eval.pkl"), "rb"))
        args = {**src["args"], "method": METHOD}
        res = {("fixed", a.k, s): P.evaluate(spec(seed, md, g, m), ipath, ids[s], desc=f"{name} {s}", **envkw)
               for s in ("val", "test")}
        for s in ("val", "test"):
            log(f"{name} {s}: score {mean_score(res[('fixed', a.k, s)]):.2f}")
        os.makedirs(os.path.join(out.dir, name), exist_ok=True)
        out.save(f"{name}/eval", {"args": args, "cfg": {"mode": md, "gain": g, "margin": m, "grid": grid}, "res": res,
                                 "spec": spec(seed, md, g, m), "tune": {k: mean_score(v) for k, v in tune.items()},
                                 "seconds": time.time() - t0})


if __name__ == "__main__":
    main()
