"""D51: final-report checks for the leak-fixed live stream (RC_BUF_LADDER=1), no new runs.

1. il_ppo (all 3 seeds, seeds averaged per case) and ppo_v2 vs the encoder's own whole-stream ABR+VBV (E2, target
   f x channel mean, f tuned on val incl. the e2x extension), paired on the cases the real-encoder run covered (every
   3rd test case). Policy rows are curve lookups; D47 showed lookup = real encode exactly (replay diff 0.000).
2. Selection check on VALIDATION: il_ppo vs ppo_v2 and vs vbv2 (il_ppo was picked as best learner in D42).
Output: results/v1_buffer/live_vs_encoder.md

  python tools/live_vs_encoder.py      (in the project env; reads rcwork_v1/<codec>/results_buffer{,_trace}_ladder)
"""
import glob
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("RC_V1", "1")
from experiments import stream_rl as S  # noqa: E402

W = "/scratch1/pbanga/rcwork_v1"
E2_F = (0.6, 0.7, 0.8, 0.9, 1.0, 0.2, 0.3, 0.4, 0.5)
key = lambda r: (tuple(r["stream"]), r["q0"], r["s"])  # noqa: E731


def seeds(d, m, split):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, f"{m}_L2_s*", "eval.pkl"))):
        for r in pickle.load(open(p, "rb"))["res"][split]:
            out.setdefault(key(r), []).append(r)
    return {k: (np.mean([x["score"] for x in v]), v[0]["group"], len(v)) for k, v in out.items()}


def real_rows(d, split):
    R = {}
    for p in sorted(glob.glob(os.path.join(d, "real", f"{split}_*of*.pkl"))):
        if "_il_ppo_rr" in p:
            continue
        for name, rows in pickle.load(open(p, "rb"))["rows"].items():
            R.setdefault(name, []).extend(rows)
    return R


def best_f(d):
    V = real_rows(d, "val")
    vm = {f: np.mean([r["score"] for r in V[f"enc_vbv_f{f:g}"]]) for f in E2_F if V.get(f"enc_vbv_f{f:g}")}
    return max(vm, key=vm.get)


def ci(a, b):
    ks = [k for k in a if k in b]
    d = np.array([a[k][0] - b[k][0] for k in ks])
    t = S.cboot(d, np.array([a[k][1] for k in ks]))
    star = "*" if t[1] > 0 or t[2] < 0 else ""
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]{star} (n={len(ks)})"


def main():
    L = ["# Leak-fixed live stream: 3-seed learners vs the encoder's own ABR+VBV, and the validation selection check",
         "", "Score = luma dPSNR_B - 0.17 dB per % over - 0.5 dB per % stalled. Paired on identical cases; 95 % cluster "
         "bootstrap over source groups (mixed streams own cluster); * = CI excludes 0. Learner rows: seeds averaged per "
         "case (curve lookups, = real encodes, D47). Encoder: whole-stream ABR+VBV, 1 s buffer, target f x channel mean, "
         "f tuned on val.", ""]
    for E in ("x265", "x264"):
        for ch, tag in (("AR(1)", "results_buffer_ladder"), ("LTE", "results_buffer_trace_ladder")):
            d = os.path.join(W, E, tag)
            f = best_f(d)
            L += [f"## {E}, {ch} (encoder f = {f:g})", "", "| comparison | test n=8 | test playlists n=16 |",
                  "|---|---|---|"]
            enc = {s: {key(r): (r["score"], r["group"], 1) for r in real_rows(d, s).get(f"enc_vbv_f{f:g}", [])}
                   for s in ("test", "test16")}
            for m in ("il_ppo", "ppo_v2"):
                cells = [ci(seeds(d, m, s), enc[s]) if enc[s] else "--" for s in ("test", "test16")]
                L.append(f"| {m} (3 seeds) - encoder ABR+VBV | {cells[0]} | {cells[1]} |")
            b2 = pickle.load(open(os.path.join(d, "baselines2.pkl"), "rb"))["rows"]
            vb = {key(r): (r["score"], r["group"], 1) for r in b2[("vbv2", 2, "val")]}
            il, pv = seeds(d, "il_ppo", "val"), seeds(d, "ppo_v2", "val")
            L += ["", f"Validation (selection check): il_ppo - ppo_v2 {ci(il, pv)}; il_ppo - vbv2 {ci(il, vb)}; "
                  f"ppo_v2 - vbv2 {ci(pv, vb)}", ""]
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "v1_buffer",
                       "live_vs_encoder.md")
    open(out, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
