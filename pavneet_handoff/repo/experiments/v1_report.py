"""Dataset v1, Stage 1 report (D31): every learner against the online controller on the test split. Differences are
paired per (GOP, budget level), averaged over seeds, with a source-group bootstrap; the per-seed differences are listed
as well, since the success criterion needs all seeds to agree.

  RC_V1=1 RC_WORK=... RC_REPORTS=... python experiments/v1_report.py [--quick]
"""
import glob
import json
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, metrics, runner  # noqa: E402


def rows_of(p, split):
    r = pickle.load(open(p, "rb"))
    return next((v for k, v in r["res"].items() if k[2] == split), None)


def table(rows):
    return {(x["gid"], x["budget"]): (x["score"], x["saving"], float(x["over"]), x["bits"] / x["budget_bits"], x["psnr"])
            for x in rows}


def boot(d, groups, n=4000):
    u, inv = np.unique(groups, return_inverse=True)
    s, c = np.bincount(inv, d, len(u)), np.bincount(inv, minlength=len(u))
    w = np.random.default_rng(0).multinomial(len(u), [1 / len(u)] * len(u), n)
    m = (w @ s) / (w @ c)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    a = runner.args()
    assert C.V1, "run with RC_V1=1"
    gops = json.load(open(os.path.join(C.WORK, "manifest.json")))["gops"]
    gops = gops if isinstance(gops, list) else list(gops.values())
    group = {g["id"]: g["group"] for g in gops}
    runs = defaultdict(dict)
    for p in glob.glob(os.path.join(C.WORK, "results_rl" + ("_quick" if a.quick else ""), "*", "eval.pkl")):
        base, seed = os.path.basename(os.path.dirname(p)).rsplit("_s", 1)
        runs[base][int(seed)] = p
    out = ["# Dataset v1, Stage 1", "", f"Under-budget penalty: {metrics.UNDER_PENALTY} point per % unused beyond "
           f"{metrics.UNDER_TOL}% (0 = off).", "", f"Encoder {C.CODEC}. Score 0 = best constant QP in hindsight. Differences are against the "
           "controller at the same k; the interval is a 95% source-group bootstrap over the seed mean.", "",
           "| Method | k | Seeds | Val score | Test score | Saving | Over % | Spend / budget | PSNR vs controller (dB) | "
           "Diff vs controller | 95% CI | Diff per seed |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for base in sorted(runs, key=lambda b: (int(b.split("_k")[1].split("_")[0]), b)):
        method, k = base.split("_k")[0], int(base.split("_k")[1].split("_")[0])
        te = {s: table(rows_of(p, "test")) for s, p in runs[base].items()}
        va = [np.mean([v[0] for v in table(rows_of(p, "val")).values()]) for p in runs[base].values()]
        keys = sorted(next(iter(te.values())))
        m = np.mean([[t[x] for x in keys] for t in te.values()], axis=0)
        diff, ci, per, dp = "", "", "", ""
        ref = runs.get(f"ctrl_k{k}_fixed", {}).get(0)
        if ref and method != "ctrl":
            c = table(rows_of(ref, "test"))
            d = m[:, 0] - np.array([c[x][0] for x in keys])
            lo, hi = boot(d, np.array([group[x[0]] for x in keys]))
            diff, ci = f"{d.mean():+.2f}", f"{lo:+.2f} to {hi:+.2f}"
            dp = f"{np.mean(m[:, 4] - np.array([c[x][4] for x in keys])):+.2f}"
            per = " ".join(f"{np.mean([t[x][0] - c[x][0] for x in keys]):+.2f}" for _, t in sorted(te.items()))
        out.append(f"| {method} | {k} | {len(te)} | {np.mean(va):.2f} | {m[:, 0].mean():.2f} | {m[:, 1].mean():.2f} | "
                   f"{100 * m[:, 2].mean():.1f} | {100 * m[:, 3].mean():.1f}% | {dp} | {diff} | {ci} | {per} |")
    os.makedirs(C.REPORTS, exist_ok=True)
    p = os.path.join(C.REPORTS, "v1_stage1_report.md")
    open(p, "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
