"""Experiment 5a (revision 2): smooth 4-parameter shift, fitted on the Exp 5 labels. PREREG: exp_next/exp5/PREREG_SHIFT.md.

shift_0 = I-frame offset, shift_1 = frame-1 offset, frames 2-29 = linear ramp from a (frame 2) to b (frame 29).
Fit: weighted (beta 0.1 BC weights) least squares of the clipped label on these 4 basis functions = the weighted
per-frame means for frames 0 and 1, and a weighted line through the per-frame means of frames 2-29. Pooled and per
budget level, per (encoder, k). Real-valued; added to final4's real-valued QP before its rounding (shift_eval.py).
Also reports how much of the per-frame means the line leaves and its correlation with the search's start-ramp
rounding error (the artefact that makes the per-frame means jagged).

  python -I exp_next/exp5/shift_smooth.py
Out: results_v1/next/exp5/shifts_smooth.json ({"enc|k|pooled" or "enc|k|L<lv>": [30 floats], "...|params": [4]}),
     shift_smooth.md
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp5")
from shift_fit import GOP, KS, LEVELS, OUT, weights  # noqa: E402

RAMP_ERR = np.round(np.array([-6.0] + list(np.linspace(-3, 3, 29)))) - np.array([-6.0] + list(np.linspace(-3, 3, 29)))


def fit(lab, w, t):
    d = pd.DataFrame({"y": lab * w, "w": w, "t": t}).groupby("t")[["y", "w"]].sum()
    m, W = (d.y / d.w).reindex(range(GOP)).to_numpy(), d.w.reindex(range(GOP)).to_numpy()
    tt = np.arange(2, GOP)
    X = np.stack([(GOP - 1 - tt) / (GOP - 3), (tt - 2) / (GOP - 3)], 1)
    sw = np.sqrt(W[2:])
    a, b = np.linalg.lstsq(X * sw[:, None], m[2:] * sw, rcond=None)[0]
    vec = np.r_[m[0], m[1], X @ [a, b]]
    return vec, [float(m[0]), float(m[1]), float(a), float(b)], m


def main():
    out, L = {}, ["# Exp 5a smooth 4-parameter shift (exp_next/exp5/shift_smooth.py)", "",
                  "Beta 0.1 weights, clipped labels, fitting clips only. Params = I offset, frame-1 offset, ramp value "
                  "at frame 2, ramp value at frame 29 (QP, real-valued).", "",
                  "| enc | k | variant | I | frame 1 | ramp f2 | ramp f29 | sd of per-frame means about the line (f2-29) "
                  "| corr(residual, ramp rounding error) |", "|---|---|---|---|---|---|---|---|---|"]
    for enc in ("x264", "x265"):
        psuf = "_k" + os.environ["EXP5_KS"].replace(",", "_") if "EXP5_KS" in os.environ else ""
        plans = pd.read_pickle(f"{OUT}/plans_{enc}{psuf}.pkl").set_index("pid")   # the plans file built with these npz
        for k in KS:
            z = np.load(f"{OUT}/data_{enc}_k{k}.npz")
            lab, t, pid = z["label"].astype(float), z["t"].astype(int), z["pid"]
            w = weights(z["delta"].astype(float), 0.1)
            lev = plans.level.reindex(pid).to_numpy()
            for name, msk in [("pooled", np.ones(len(lab), bool))] + [(f"L{lv}", lev == lv) for lv in LEVELS]:
                vec, par, m = fit(lab[msk], w[msk], t[msk])
                out[f"{enc}|{k}|{name}"] = [float(x) for x in vec]
                out[f"{enc}|{k}|{name}|params"] = par
                r = m[2:] - vec[2:]
                L.append(f"| {enc} | {k} | {name} | " + " | ".join(f"{p:+.2f}" for p in par) +
                         f" | {r.std():.2f} | {np.corrcoef(r, RAMP_ERR[2:])[0, 1]:+.2f} |")
    L += ["", "Per-level vs pooled (max |difference| of the smooth vectors): " + "; ".join(
        f"{e} k{k} {max(np.abs(np.array(out[f'{e}|{k}|L{lv}']) - np.array(out[f'{e}|{k}|pooled'])).max() for lv in LEVELS):.2f}"
        for e in ("x264", "x265") for k in KS), ""]
    if "EXP5_KS" in os.environ:     # final week 11-17: add the new k only; existing entries must not change
        prev = json.load(open(f"{OUT}/shifts_smooth.json"))
        clash = [key for key in out if key in prev and prev[key] != out[key]]
        assert not clash, f"would change existing entries: {clash[:4]}"
        new = [key for key in out if key not in prev]
        prev.update(out)
        tmp = f"{OUT}/shifts_smooth.json.part"
        json.dump(prev, open(tmp, "w"), indent=0)
        os.replace(tmp, f"{OUT}/shifts_smooth.json")
        open(f"{OUT}/shift_smooth_k{os.environ['EXP5_KS'].replace(',', '_')}.md", "w").write("\n".join(L) + "\n")
        print(f"added {len(new)} entries: {new}")
    else:
        json.dump(out, open(f"{OUT}/shifts_smooth.json", "w"), indent=0)
        open(f"{OUT}/shift_smooth.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
