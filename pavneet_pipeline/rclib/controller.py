"""P2's causal online base-QP controller, for the residual RL arm (RC_ARM=res; v1-data branch, P2 2026-11-09).

`decide` is copied verbatim from P2's scripts/controller_real.py (the version that produced results_v1/controller_final.md
and the controller_real/final2_* runs), so that with all residual offsets at 0 the env replays the published controller
exactly (checked by tools/res_parity.py). Keep the two in sync.

Rate model, fitted on TRAIN constant-QP encodes only (data/v1/320x180/rd/controller_model.json):
  bits_j(q) = c_type x fp_j x 2^(-(q - 30) / s_type), fp = P1-settings first-pass slice bits at QP 32 (>= 8)
Before frame t it solves for the constant P-frame QP that spends margin x the remaining budget over frames t..29, with
online calibration of c_P on the frames already coded. It sees first-pass bits of frames t..t+k only.
"""
import json

import numpy as np

GOP, QLO, QHI = 30, 11, 51


def load_model(codec, path):
    with open(path) as f:
        return json.load(f)[codec]


def decide(t, bits, qps, fp, B, k, M, margin, dI, i_cap, w0, dmax=51, fcap=1e9, init=0, pmin=-99, a=0.0, b=0.0,
           h=0.0, qhat=None, cut=None, wfp=2.0, diag=None):
    # diag (P2 next-exp R2, 11-13): optional dict filled with the controller's internal state for frame t (level,
    # calibrated c_P, remaining budget, the plan's predicted spend ratio, the QP-step reference, the fcap floor). It
    # never changes the returned QP.
    # h = previous-GOP history mode: applied by the caller through qhat and M (as scripts/controller_real.py chain())
    vis = min(k, GOP - 1 - t)
    known = fp[1:t + vis + 1]
    prior_p = fp[0] / M["ip"]                         # P-frame first-pass cost implied by the I frame (train ratio)
    # mean P first-pass cost for frames beyond the lookahead, shrunk towards prior_p with wfp pseudo-frames
    fh = fp.copy()
    fh[t + vis + 1:] = (known.sum() + wfp * prior_p) / (len(known) + wfp)
    if t >= 2:
        pp = fp[1:t] * 2 ** (-(np.array(qps[1:t], float) - 30) / M["s_p"])
        mp = pp.mean()
        c_p = (sum(bits[1:t]) + w0 * M["c_p"] * mp) / (pp.sum() + w0 * mp)
    else:
        c_p = M["c_p"]
    rem = margin * B - sum(bits)
    if diag is not None:
        diag.update(c_p=float(c_p), rem=float(rem), level=float(QHI), plan_ratio=1.0, ref=None, q_fcap_min=QLO,
                    q_real=float(QHI))
    # q_real (P2 next-exp Exp 5a, 11-13): the real-valued QP before the final rounding; equal to the returned integer
    # whenever a cap or clip set the QP, so round(q_real) == returned QP always
    if rem <= 0:
        return QHI
    jj = np.arange(max(t, 1), GOP)
    off = np.zeros(GOP)
    off[1:] = -a + 2 * a * np.arange(GOP - 1) / (GOP - 2)
    is_cut = np.zeros(GOP, bool)
    if cut is not None and b:
        is_cut[t:t + vis + 1] = cut[t:t + vis + 1]
        is_cut[0] = False
        off[is_cut] -= b

    def spend(q):
        s = c_p * (fh[jj] * 2 ** (-(q + off[jj] - 30) / M["s_p"])).sum()
        if t == 0:
            s += min(M["c_i"] * fp[0] * 2 ** (-(q - dI - 30) / M["s_i"]), i_cap * B)
        return s
    lo, hi = 0.0, 60.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if spend(mid) <= rem else (mid, hi)
    q = hi
    if diag is not None:
        diag["level"] = float(q)
    if t == 0:
        q_i = (qhat - dI) if (init == 1 and qhat is not None) else (q - dI)
        while M["c_i"] * fp[0] * 2 ** (-(q_i - 30) / M["s_i"]) > i_cap * B and q_i < QHI:
            q_i += 0.5
        qi = int(np.clip(round(q_i), QLO, QHI))
        if diag is not None:
            diag["q_real"] = float(q_i) if qi == round(q_i) else float(qi)
        return qi
    q_raw = q + off[t]
    qt = round(q_raw)
    share = rem / (GOP - t)
    if diag is not None:   # lowest QP whose predicted frame-t bits respect the fcap share
        diag["q_fcap_min"] = int(np.ceil(30 - M["s_p"] * np.log2(max(fcap * share, 1e-9) / (c_p * fp[t]))))
    while c_p * fp[t] * 2 ** (-(qt - 30) / M["s_p"]) > fcap * share and qt < QHI:
        qt += 1
    ref = qps[-1] if t >= 2 else qps[0] + dI
    boost = b if is_cut[t] else 0.0
    if dmax < 51:
        qt = int(np.clip(qt, ref - dmax - boost, ref + dmax))
    qt = max(qt, qps[0] + pmin - boost)
    if diag is not None:
        qf = int(np.clip(qt, QLO, QHI))
        plan = c_p * (fh[jj] * 2 ** (-(qf - off[t] + off[jj] - 30) / M["s_p"])).sum()
        diag.update(ref=float(ref), plan_ratio=float(plan / rem), q_real=float(q_raw) if qf == round(q_raw) else float(qf))
    return int(np.clip(qt, QLO, QHI))
