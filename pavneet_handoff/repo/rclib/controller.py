"""Causal online QP controller (D31), ported from Aayush's scripts/controller_real.py (setting v1, chosen on val).

Before frame t it solves for the constant P-frame QP that spends margin x the remaining budget over frames t..29, using a
rate model bits_j(q) = c_type x fp_j x 2^(-(q - 30) / s_type) fitted on train (experiments/v1_prep.py) with c_P updated
online from the frames already coded. Frames beyond the visible window get the mean visible P cost, shrunk towards
fp_0 / (train I:P ratio). In RC_V1 mode the policy's action is a residual on this QP, so action 0 everywhere = the controller.
"""
import json
import os

import numpy as np

from . import config as C

QLO, QHI = 11, 51
_M = None


def model():
    global _M
    if _M is None:
        with open(os.path.join(C.WORK, "controller_model.json")) as f:
            _M = json.load(f)
    return _M


def decide(t, bits, qps, fp, B, k, M=None, margin=0.97, dI=3.0, i_cap=1.0, w0=2.0, dmax=3, fcap=4.0, pmin=1, wfp=2.0):
    M = M or model()
    n = C.GOP
    vis = min(k, n - 1 - t)
    known = fp[1:t + vis + 1]
    prior_p = fp[0] / M["ip"]
    fh = np.array(fp, float)
    fh[t + vis + 1:] = (known.sum() + wfp * prior_p) / (len(known) + wfp)
    if t >= 2:
        pp = fp[1:t] * 2 ** (-(np.array(qps[1:t], float) - 30) / M["s_p"])
        mp = pp.mean()
        c_p = (sum(bits[1:t]) + w0 * M["c_p"] * mp) / (pp.sum() + w0 * mp)
    else:
        c_p = M["c_p"]
    rem = margin * B - sum(bits)
    if rem <= 0:
        return QHI
    jj = np.arange(max(t, 1), n)

    def spend(q):
        s = c_p * (fh[jj] * 2 ** (-(q - 30) / M["s_p"])).sum()
        if t == 0:
            s += min(M["c_i"] * fp[0] * 2 ** (-(q - dI - 30) / M["s_i"]), i_cap * B)
        return s
    lo, hi = 0.0, 60.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if spend(mid) <= rem else (mid, hi)
    q = hi
    if t == 0:
        q_i = q - dI
        while M["c_i"] * fp[0] * 2 ** (-(q_i - 30) / M["s_i"]) > i_cap * B and q_i < QHI:
            q_i += 0.5
        return int(np.clip(round(q_i), QLO, QHI))
    qt = round(q)
    share = rem / (n - t)
    while c_p * fp[t] * 2 ** (-(qt - 30) / M["s_p"]) > fcap * share and qt < QHI:
        qt += 1
    ref = qps[-1] if t >= 2 else qps[0] + dI
    qt = int(np.clip(qt, ref - dmax, ref + dmax))
    qt = max(qt, qps[0] + pmin)
    return int(np.clip(qt, QLO, QHI))


def fit(infos):
    """Slopes and priors from the train GOPs' constant-QP frame bits (I frame near q - 3), as Aayush's fit_model."""
    qi, qs = C.QPS.index(30), np.array(C.QPS, float)
    xi, yi, xp, yp, ci, cp, ip = [], [], [], [], [], [], []
    for x in infos.values():
        if x["gop"]["split"] != "train":
            continue
        fp = np.maximum(np.asarray(x["fp_bits"], float), 8)
        fb = np.maximum(np.asarray(x["curve"]["frame_bits"], float), 8)
        xi += list(qs - 3 - 30); yi += list(np.log2(fb[:, 0] / fp[0]))
        xp += list(np.repeat(qs - 30, C.GOP - 1)); yp += list(np.log2(fb[:, 1:] / fp[1:]).ravel())
        ci.append((fb[qi, 0], fp[0])); cp.append(fb[qi, 1:].sum() / fp[1:].sum()); ip.append(fp[0] / fp[1:].mean())
    s_i, s_p = -1 / np.polyfit(xi, yi, 1)[0], -1 / np.polyfit(xp, yp, 1)[0]
    c_i = float(np.median([a / (b * 2 ** (3 / s_i)) for a, b in ci]))
    return {"s_i": float(s_i), "s_p": float(s_p), "c_i": c_i, "c_p": float(np.median(cp)), "ip": float(np.median(ip))}
