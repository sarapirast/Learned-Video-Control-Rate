"""Smooth pooled mean shift for x264 at the k in EXP5_KS, with the fit of p2_data/exp_next/exp5/shift_smooth.py (fit()
copied verbatim; weights = shift_fit.weights: exp(delta / beta) clipped at the 99th percentile), from the v1 data that
bc_data_build.py wrote to <dir>. Writes <dir>/shifts_smooth.json = Aayush's file + the new "x264|<k>|pooled" entries.
--check: compare the fitted vectors with Aayush's entries for the same k (for k5 / k0 validation) instead of writing.
  python -I bc_shift_fit.py <dir> [--check] [--base <shifts json to extend; default Aayush's>]
"""
import json
import os
import sys

import numpy as np
import pandas as pd

GOP = 30
SRC = "/scratch1/aayushso/ee599/results_v1/next/exp5/shifts_smooth.json"


def weights(delta, beta):
    w = np.exp(delta / beta)
    return np.minimum(w, np.percentile(w, 99))


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
    d, check = sys.argv[1], "--check" in sys.argv
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else SRC
    ks = [int(x) for x in os.environ["EXP5_KS"].split(",")]
    ref = json.load(open(SRC))
    out = dict(json.load(open(base)))
    for k in ks:
        z = np.load(f"{d}/data_x264_k{k}.npz")
        vec, par, _ = fit(z["label"].astype(float), weights(z["delta"].astype(float), 0.1), z["t"].astype(int))
        key = f"x264|{k}|pooled"
        if check:
            dv = np.abs(vec - np.asarray(ref[key])).max()
            print(f"{key}: max |mine - stored| = {dv:.2e} ({'OK' if dv < 1e-6 else 'DIFFERENT'})")
            if dv >= 1e-6:
                sys.exit(1)
        else:
            assert key not in out, f"{key} already in {base}"
            out[key], out[key + "|params"] = [float(x) for x in vec], par
            print(f"{key}: params {np.round(par, 3).tolist()}")
    if not check:
        dest = f"{d}/shifts_smooth.json"
        assert not os.path.exists(dest), f"{dest} exists"
        json.dump(out, open(dest, "w"), indent=0)
        print(f"-> {dest}")


if __name__ == "__main__":
    main()
