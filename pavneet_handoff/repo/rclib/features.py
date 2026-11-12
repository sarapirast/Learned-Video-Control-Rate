"""Per-frame analysis of a GOP: pixel complexity, first-pass cost, and scene structure (cuts, flashes, fades).

Everything here is computed from the source frames (and one ultrafast first-pass encode) only — never from the plan
being scored — so it is available to a causal controller with a k-frame lookahead buffer. Which frames' features a
policy may see is decided in `env.py`, not here.
"""
import numpy as np

from . import config as C

YS = C.W * C.H
HIST_BINS = 32


def _planes(frames):
    y = frames[:, :YS].reshape(-1, C.H, C.W).astype(np.float32)
    u = frames[:, YS:YS + YS // 4].reshape(-1, C.H // 2, C.W // 2).astype(np.float32)
    v = frames[:, YS + YS // 4:].reshape(-1, C.H // 2, C.W // 2).astype(np.float32)
    return y, u, v


def pixel_features(frames):
    """Arrays of length GOP (index t = frame t)."""
    y, u, v = _planes(frames)
    n = len(y)
    gx = np.abs(np.diff(y, axis=2)).mean((1, 2))
    gy = np.abs(np.diff(y, axis=1)).mean((1, 2))
    spatial = gx + gy                                     # mean absolute gradient
    var = y.var((1, 2))
    mean = y.mean((1, 2))
    sad = np.zeros(n, np.float32)
    sad[1:] = np.abs(np.diff(y, axis=0)).mean((1, 2))      # temporal: mean abs frame difference
    # block-motion proxy: SAD after the best of 9 global shifts (+-4 px) — separates pans from new content
    msad = np.zeros(n, np.float32)
    for t in range(1, n):
        best = np.inf
        for dy in (-4, 0, 4):
            for dx in (-4, 0, 4):
                a = y[t, 8 + dy:C.H - 8 + dy, 8 + dx:C.W - 8 + dx]
                b = y[t - 1, 8:C.H - 8, 8:C.W - 8]
                best = min(best, float(np.abs(a - b).mean()))
        msad[t] = best
    # colour histograms (luma 32 bins + 2x8 chroma) and their chi-square distance to the previous frame
    h = np.stack([np.concatenate([np.histogram(y[t], HIST_BINS, (0, 256))[0] / y[t].size,
                                  np.histogram(u[t], 8, (0, 256))[0] / u[t].size * 0.5,
                                  np.histogram(v[t], 8, (0, 256))[0] / v[t].size * 0.5]) for t in range(n)])
    hd = np.zeros(n, np.float32)
    hd[1:] = 0.5 * (((h[1:] - h[:-1]) ** 2) / (h[1:] + h[:-1] + 1e-9)).sum(1)
    return {"spatial": spatial.astype(np.float32), "var": var.astype(np.float32), "mean": mean.astype(np.float32),
            "sad": sad, "msad": msad, "hist_d": hd, "hist": h.astype(np.float32)}


# ---------------------------------------------------------------- scene structure

# defaults; experiments/scenes.py fits these on the training splices and rewrites every GOP's cut/flash/fade flags
# (and records the fitted values in docs/DECISIONS.md)
DETECT = {"hist": 0.30, "msad_ratio": 3.0, "fp_ratio": 2.5, "flash_back": 0.12}


def detect_cuts(px, fp_bits, params=None, causal_window=None):
    """Cut at frame t means frames t-1 and t belong to different shots. Frame 0 is never a cut (IDR anyway).

    Combined detector: a cut needs a large histogram change AND (a motion-compensated difference spike OR a first-pass
    cost spike); a flash (frame t differs from t-1 but t+1 or t+2 looks like t-1 again) is not a cut.
    Returns dict of int8 arrays: cut, flash, fade, and the three single-detector votes (for the detector study).
    """
    p = {**DETECT, **(params or {})}
    n = len(px["hist_d"])
    hd, ms = px["hist_d"], px["msad"]
    fp = np.asarray(fp_bits, float)
    # local reference levels from the previous few P frames (causal)
    v_hist = (hd > p["hist"]).astype(np.int8)
    v_msad = np.zeros(n, np.int8)
    v_fp = np.zeros(n, np.int8)
    for t in range(1, n):
        lo = max(1, t - 5)
        ref_m = np.median(ms[lo:t]) if t > lo else ms[t]
        ref_f = np.median(fp[lo:t]) if t > lo else fp[t]
        v_msad[t] = ms[t] > p["msad_ratio"] * max(ref_m, 1.0)
        v_fp[t] = fp[t] > p["fp_ratio"] * max(ref_f, 1.0) if t > 1 else fp[t] > 0.5 * fp[0]
    cut = ((v_hist == 1) & ((v_msad == 1) | (v_fp == 1))).astype(np.int8)
    cut[0] = 0
    # flashes: a "cut" at t followed by a return to the t-1 look within 2 frames
    flash = np.zeros(n, np.int8)
    h = px["hist"]
    for t in np.flatnonzero(cut):
        for back in (1, 2):
            if t + back < n and t >= 1:
                d = 0.5 * (((h[t + back] - h[t - 1]) ** 2) / (h[t + back] + h[t - 1] + 1e-9)).sum()
                if d < p["flash_back"]:
                    flash[t:t + back] = 1
                    cut[t] = 0
                    if t + back < n:
                        cut[t + back] = 0
                    break
    # fades: >= 5 consecutive frames whose mean luma moves the same way by > 1.5 levels per frame
    fade = np.zeros(n, np.int8)
    dm = np.diff(px["mean"], prepend=px["mean"][0])
    run = 0
    for t in range(1, n):
        run = run + 1 if (abs(dm[t]) > 1.5 and np.sign(dm[t]) == np.sign(dm[t - 1])) else 0
        if run >= 4:
            fade[t - run:t + 1] = 1
    return {"cut": cut, "flash": flash, "fade": fade, "v_hist": v_hist, "v_msad": v_msad, "v_fp": v_fp}


def scene_ids(cut):
    return np.cumsum(cut).astype(np.int16)


def gop_analysis(frames, fp_bits, params=None):
    px = pixel_features(frames)
    sc = detect_cuts(px, fp_bits, params)
    return {**px, **sc, "scene": scene_ids(sc["cut"]), "fp_bits": np.asarray(fp_bits, np.int64)}
