"""Per-frame Y rate-distortion data for dataset v1 and the frame-level GOP controller used by D37 (hierarchical) and
D38 (buffer). Read-only source: the v1 per-frame constant-QP table rd_frames.parquet (kind = cqp: bits and luma MSE of
every frame of every GOP at QP 18..50, same encodes as our curves; slice + header bits match our curve bits).

Quality is luma PSNR of the pooled MSE (Aayush's dPSNR_B definition). D34-D36 used our 6:1:1 weighted YUV PSNR; on v1
the chroma error is 0, so chroma PSNR is pinned at 100 dB and those dB numbers are about 3/4 of the Y-PSNR dB.

Frame lookup as in a constant-QP simulator: a P frame at QP q costs row q of its constant-QP encode, the I frame at QP q
costs row q + I_OFF (constant-QP encodes code the I frame ~3 QP below the P frames). A frame's cost does not depend on
its reference's QP.

Inner controller: our D31 port of Aayush's online controller (rclib/controller.decide) with the final3 settings
margin 1.0, dI 9, i_cap 1, w0 2, dmax 3, fcap 4, pmin 1 (final3's init / a / b are not in our port).
"""
import os
import pickle

import numpy as np

from . import config as C, controller as CT

RD = os.environ.get("RC_V1_RD", "/scratch1/aayushso/ee599/data/v1/320x180/rd/rd_frames.parquet")
QLO, QHI, I_OFF, GOP = 18, 50, 3, 30
NQ = QHI - QLO + 1
FINAL3 = {"margin": 1.0, "dI": 9.0, "i_cap": 1.0, "w0": 2.0, "dmax": 3, "fcap": 4.0, "pmin": 1}
K = 2                      # frames of lookahead inside the GOP (final3 headline setting)
GRID = 48                  # budget points per GOP in the training tables


def psnr(mse):
    return 10 * np.log10(255.0 ** 2 / np.maximum(np.asarray(mse, float), 1e-10))


def load(infos):
    """gid -> {bits [33, 30], mse [33, 30], fp [30], cq_bits [33], cq_psnr [33]} for the GOPs in infos (cached)."""
    p = os.path.join(C.results_dir("yrd"), "frames.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    import pandas as pd
    want = {(x["gop"]["clip"], int(x["gop"]["v1_gop"])): g for g, x in infos.items() if "v1_gop" in x["gop"]}
    df = pd.read_parquet(RD, columns=["encoder", "clip_id", "gop", "kind", "qp", "frame", "slice_bits", "header_bits",
                                      "mse_y"], filters=[("encoder", "==", C.CODEC), ("kind", "==", "cqp")])
    df = df.sort_values(["clip_id", "gop", "qp", "frame"])
    out = {}
    for (c, gi), d in df.groupby(["clip_id", "gop"], sort=False):
        g = want.get((c, int(gi)))
        if g is None or len(d) != NQ * GOP:
            continue
        b = (d.slice_bits.to_numpy(float) + d.header_bits.to_numpy(float)).reshape(NQ, GOP)
        m = d.mse_y.to_numpy(float).reshape(NQ, GOP)
        out[g] = {"bits": np.maximum(b, 8), "mse": m, "fp": np.maximum(np.asarray(infos[g]["fp_bits"], float), 8),
                  "cq_bits": b.sum(1), "cq_psnr": psnr(m.mean(1))}
    pickle.dump(out, open(p, "wb"))
    return out


def frame_at(v, t, q):
    row = int(np.clip(q + (I_OFF if t == 0 else 0), QLO, QHI)) - QLO
    return v["bits"][row, t], v["mse"][row, t]


def run_gop(v, budget, M=None, k=K, P=FINAL3):
    """Code one GOP with the controller under `budget`; returns (bits, sum of frame MSE, QPs)."""
    M = M or CT.model()
    bits, qps, ms = [], [], 0.0
    fp = v["fp"]
    for t in range(GOP):
        q = CT.decide(t, bits, qps, fp, budget, k, M, **P)
        b, m = frame_at(v, t, q)
        bits.append(b)
        qps.append(q)
        ms += m
    return float(sum(bits)), ms, qps


def const_gop(v, q):
    """Constant QP q for the whole GOP (the curve point): bits, MSE sum."""
    r = int(np.clip(q, QLO, QHI)) - QLO
    return float(v["cq_bits"][r]), float(v["mse"][r].sum())


def budget_grid(v):
    lo, hi = v["cq_bits"][-1] * 0.6, v["cq_bits"][0] * 1.3
    return np.geomspace(lo, hi, GRID)


def tables(Y, ids):
    """Training tables: per GOP the controller's (bits, MSE sum) on a log-spaced budget grid (cached per call site)."""
    p = os.path.join(C.results_dir("yrd"), "tables.pkl")
    T = pickle.load(open(p, "rb")) if os.path.exists(p) else {}
    todo = [g for g in ids if g not in T]
    if todo:
        M = CT.model()
        for g in todo:
            v = Y[g]
            bg = budget_grid(v)
            r = np.array([run_gop(v, b, M)[:2] for b in bg])
            T[g] = {"lb": np.log(bg), "bits": r[:, 0], "mse": r[:, 1]}
        pickle.dump(T, open(p, "wb"))
    return T


def table_gop(T, g, budget):
    """Interpolated controller outcome for budget (training only; evaluation runs the controller exactly)."""
    t = T[g]
    x = np.log(max(budget, 1.0))
    return float(np.exp(np.interp(x, t["lb"], np.log(t["bits"])))), float(np.interp(x, t["lb"], t["mse"]))


def stream_curve(Y, stream):
    """Stream constant-QP curve: total bits and pooled luma PSNR at every QP."""
    b = np.sum([Y[g]["cq_bits"] for g in stream], 0)
    m = np.sum([Y[g]["mse"].sum(1) for g in stream], 0) / (GOP * len(stream))
    return {"bits": b, "psnr": psnr(m)}
