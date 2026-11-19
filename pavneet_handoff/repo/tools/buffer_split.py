"""Aayush's check 4 on the live-stream results (team update 2026-11-16): RL - vbv2 / mpc split by stream type.
No new runs: reads results_buffer[_trace]/{baselines2.pkl, <method>_L2_s*/eval.pkl}. Paired per (stream, q0, s),
seeds averaged, 95 % cluster bootstrap over source groups (each mixed stream is its own group, as in the reports).

  /scratch1/pbanga/envs/rc/bin/python tools/buffer_split.py > results/v1_buffer/split_by_stream_type.md
"""
import glob
import os
import pickle

import numpy as np

ROOT = "/scratch1/pbanga/rcwork_v1"
METHODS = ("ppo_v2", "il_ppo")
REFS = ("vbv2", "mpc")


def key(x):
    return (str(x["stream"]), x["q0"], x["s"])


def cboot(d, g, n=4000, seed=0):
    d, g = np.asarray(d, float), np.asarray(g)
    u, inv = np.unique(g, return_inverse=True)
    s, c = np.bincount(inv, d), np.bincount(inv)
    idx = np.random.default_rng(seed).integers(len(u), size=(n, len(u)))
    m = s[idx].sum(1) / c[idx].sum(1)
    return d.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5), len(d)


def fmt(t):
    star = "*" if t[1] > 0 or t[2] < 0 else ""
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]{star} (n={t[3]})"


def main():
    L = ["# Live-stream RL gain split by stream type (test)", "",
         "Paired score difference (dB), seeds averaged, 95 % cluster bootstrap over source groups; * = CI excludes 0. "
         "'clip' = 8 consecutive GOPs of one v1 test clip; 'mixed' = 8 GOPs from different test clips (spliced "
         "stress test); 'playlist' = n = 16 test playlists (consecutive clips).", ""]
    for setting in ("results_buffer", "results_buffer_trace"):
        L += [f"## {'AR(1) channel (default)' if setting == 'results_buffer' else 'LTE traces'}", "",
              "| codec | comparison | clip (n=8) | mixed (n=8) | playlist (n=16) |", "|---|---|---|---|---|"]
        for codec in ("x265", "x264"):
            d = os.path.join(ROOT, codec, setting)
            b2 = pickle.load(open(os.path.join(d, "baselines2.pkl"), "rb"))["rows"]
            for m in METHODS:
                runs = [pickle.load(open(p, "rb"))["res"] for p in sorted(glob.glob(os.path.join(d, f"{m}_L2_s*", "eval.pkl")))]
                if not runs:
                    continue
                for ref in REFS:
                    cells = []
                    for split, kinds in (("test", ("clip", "mixed")), ("test16", (None,))):
                        R = {key(x): x for x in b2[(ref, 2, split)]}
                        M = {}
                        for r in runs:
                            for x in r[split]:
                                M.setdefault(key(x), []).append(x["score"])
                        for kind in kinds:
                            ks = [k for k in M if k in R and (kind is None or R[k]["kind"] == kind)]
                            diff = [np.mean(M[k]) - R[k]["score"] for k in ks]
                            grp = [R[k]["group"] if R[k]["kind"] != "mixed" else f"mix:{k[0]}" for k in ks]
                            cells.append(fmt(cboot(diff, grp)) if ks else "")
                    L.append(f"| {codec} | {m} ({len(runs)} seeds) - {ref} | " + " | ".join(cells) + " |")
        L.append("")
    print("\n".join(L))


if __name__ == "__main__":
    main()
