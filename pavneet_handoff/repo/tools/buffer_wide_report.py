"""Report for the widened vbv2 / mpc retune (Aayush's checks 1-2): per setting and codec, the retuned values, which
grid edges are still hit, val gain over the D39 tuning, and the frozen RL policies (ppo_v2, il_ppo) against the D39
and the widened baselines on test (n = 8, overall / same-clip / mixed) and test16. Paired per case, seeds averaged,
95 % cluster bootstrap over source groups (mixed streams each their own group).

  /scratch1/pbanga/envs/rc/bin/python tools/buffer_wide_report.py > results/v1_buffer/baselines_wide_report.md
"""
import glob
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from buffer_split import cboot, fmt, key  # noqa: E402

ROOT = "/scratch1/pbanga/rcwork_v1"
SETTINGS = ["ladder", "trace_ladder", "", "trace", "sig0.15", "sig0.5", "cap0.5", "cap2", "lam0.25", "lam1"]


def comp(runs, R, split, kind=None):
    M = {}
    for r in runs:
        for x in r[split]:
            M.setdefault(key(x), []).append(x["score"])
    Rk = {key(x): x for x in R}
    ks = [k for k in M if k in Rk and (kind is None or Rk[k]["kind"] == kind)]
    if not ks:
        return ""
    d = [np.mean(M[k]) - Rk[k]["score"] for k in ks]
    g = [Rk[k]["group"] if Rk[k]["kind"] != "mixed" else f"mix:{k[0]}" for k in ks]
    return fmt(cboot(d, g))


def main():
    L = ["# Live-stream baselines on wider grids (Aayush's checks 1-2)", "",
         "vbv2 retuned on val by coordinate search over wider grids from the D39 optimum; mpc on a wider (gamma, H) "
         "grid. RL policies unchanged (trained on the D39 vbv2). Differences = RL - baseline, test, dB; * = 95 % CI "
         "excludes 0.", ""]
    for tag in SETTINGS:
        L += [f"## Setting: {tag or 'default (AR(1) 0.8 / 0.3, cap 1 s, 0.5 dB per % stalled)'}", ""]
        for codec in ("x265", "x264"):
            d = os.path.join(ROOT, codec, "results_buffer" + (f"_{tag}" if tag else ""))
            pw = os.path.join(d, "baselines2_wide.pkl")
            if not os.path.exists(pw):
                L += [f"{codec}: not run", ""]
                continue
            w, b2 = pickle.load(open(pw, "rb")), pickle.load(open(os.path.join(d, "baselines2.pkl"), "rb"))
            L += [f"**{codec}**: vbv2 D39 {b2['vbv2']} -> wide {w['vbv2']} (val {w['val_d39']['vbv2']:+.3f} -> "
                  f"{max(w['val_vbv2'].values()):+.3f}); mpc gamma/H {b2['mpc']['gamma']}/{b2['mpc']['H']} -> "
                  f"{w['mpc']['gamma']}/{w['mpc']['H']} (val {w['val_d39']['mpc']:+.3f} -> {max(w['val_mpc'].values()):+.3f}); "
                  f"edges still hit: {', '.join(w['edges']) or 'none'}", "",
                  "| comparison | test all | test same-clip | test mixed | test16 |", "|---|---|---|---|---|"]
            for m in ("ppo_v2", "il_ppo"):
                runs = [pickle.load(open(p, "rb"))["res"] for p in sorted(glob.glob(os.path.join(d, f"{m}_L2_s*", "eval.pkl")))]
                if not runs:
                    continue
                for ref, rows in (("vbv2 (D39)", b2["rows"]), ("vbv2 wide", w["rows"]), ("mpc (D39)", b2["rows"]),
                                  ("mpc wide", w["rows"])):
                    rk = {"vbv2 (D39)": "vbv2", "vbv2 wide": "vbv2w", "mpc (D39)": "mpc", "mpc wide": "mpcw"}[ref]
                    cells = [comp(runs, rows[(rk, 2, "test")], "test"), comp(runs, rows[(rk, 2, "test")], "test", "clip"),
                             comp(runs, rows[(rk, 2, "test")], "test", "mixed"), comp(runs, rows[(rk, 2, "test16")], "test16")]
                    L.append(f"| {m} ({len(runs)} seeds) - {ref} | " + " | ".join(cells) + " |")
            L.append("")
    print("\n".join(L))


if __name__ == "__main__":
    main()
