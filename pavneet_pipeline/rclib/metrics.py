"""Scoring: % bits saved at equal PSNR against the encoder's own constant-QP curve, with a budget penalty (D13).

RC_METRIC=dpsnr (default for RC_ARM=lfq; P2 2026-11-09): score() returns QUALITY AT THE BUDGET instead,
  dPSNR_B = PSNR - PSNR_CQP(B) - OVER_PENALTY_DB x %over      (dB)
where PSNR_CQP(B) is the GOP's constant-QP curve at exactly the budget (same interpolation / linear extrapolation as
_interp_logbits). The old score does not penalise unused budget (spending less at lower PSNR is free), and a policy
trained on it learned to under-spend (P2 results_v1/res_offsets_x264.md, results_v1/rescore_budget/).
OVER_PENALTY_DB = 0.17 dB per 1% over is the old 2 points per 1% converted at ~6 dB per doubling of bits (1% of bits
~ 0.086 dB), i.e. about 2x what the extra bits buy.
"""
import os

import numpy as np

OVER_PENALTY = 2.0      # points of score lost per 1 % over budget
OVER_PENALTY_DB = 0.17  # dB lost per 1 % over budget (RC_METRIC=dpsnr)
METRIC = os.environ.get("RC_METRIC") or ("dpsnr" if os.environ.get("RC_ARM") == "lfq" else "score")
assert METRIC in ("score", "dpsnr"), METRIC


def _interp_logbits(curve, psnr):
    """log(bits) the constant-QP curve needs to reach `psnr` (piecewise linear in PSNR, linear extrapolation)."""
    p = np.asarray(curve["psnr"], float)
    lb = np.log(np.asarray(curve["bits"], float))
    o = np.argsort(p)
    p, lb = p[o], lb[o]
    psnr = np.asarray(psnr, float)
    y = np.interp(psnr, p, lb)
    lo, hi = psnr < p[0], psnr > p[-1]
    if np.any(lo):
        y = np.where(lo, lb[0] + (psnr - p[0]) * (lb[1] - lb[0]) / max(p[1] - p[0], 1e-9), y)
    if np.any(hi):
        y = np.where(hi, lb[-1] + (psnr - p[-1]) * (lb[-1] - lb[-2]) / max(p[-1] - p[-2], 1e-9), y)
    return y


def saving(bits, psnr, curve):
    """% bits saved vs constant QP at the same PSNR (positive = better than constant QP)."""
    return 100.0 * (1.0 - np.asarray(bits, float) / np.exp(_interp_logbits(curve, psnr)))


def psnr_at_bits(curve, bits):
    """PSNR of the constant-QP curve at exactly `bits` (inverse of _interp_logbits; linear extrapolation)."""
    p = np.asarray(curve["psnr"], float)
    lb = np.log(np.asarray(curve["bits"], float))
    o = np.argsort(lb)
    p, lb = p[o], lb[o]
    x = np.log(np.asarray(bits, float))
    y = np.interp(x, lb, p)
    y = np.where(x < lb[0], p[0] + (x - lb[0]) * (p[1] - p[0]) / max(lb[1] - lb[0], 1e-9), y)
    y = np.where(x > lb[-1], p[-1] + (x - lb[-1]) * (p[-1] - p[-2]) / max(lb[-1] - lb[-2], 1e-9), y)
    return y


def dpsnr_budget(psnr, curve, budget):
    """dB vs the constant QP that spends exactly the budget (no over penalty)."""
    return np.asarray(psnr, float) - psnr_at_bits(curve, budget)


def overshoot(bits, budget):
    """% over budget (0 when within)."""
    return 100.0 * np.maximum(0.0, np.asarray(bits, float) / budget - 1.0)


def score(bits, psnr, curve, budget):
    """Penalised score used by the search, the rewards and every report's headline number (see METRIC)."""
    if METRIC == "dpsnr":
        return dpsnr_budget(psnr, curve, budget) - OVER_PENALTY_DB * overshoot(bits, budget)
    return saving(bits, psnr, curve) - OVER_PENALTY * overshoot(bits, budget)


def score_old(bits, psnr, curve, budget):
    """The original project score, whatever METRIC is (for continuity in reports)."""
    return saving(bits, psnr, curve) - OVER_PENALTY * overshoot(bits, budget)


def summarize(rows):
    """rows: iterable of dicts with saving, over (bool), score. Returns mean/CI summary."""
    s = np.array([r["score"] for r in rows], float)
    sv = np.array([r["saving"] for r in rows], float)
    ov = np.array([r["over"] for r in rows], float)
    n = len(s)
    ci = 1.96 * s.std(ddof=1) / np.sqrt(n) if n > 1 else float("nan")
    return {"n": n, "score": float(s.mean()), "score_ci": float(ci), "median": float(np.median(s)),
            "saving": float(sv.mean()),
            "over_pct": 100.0 * float(ov.mean())}


def paired_ci(a, b):
    """Mean difference a-b with 95 % CI over paired items (same GOP and budget)."""
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    return float(d.mean()), float(1.96 * d.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
