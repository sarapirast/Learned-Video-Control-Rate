"""Causal online base-QP controller (P2 baseline "causal fixed pattern", done with an online rate model).

OFFLINE PROTOTYPE: frames are not re-encoded. A frame's bits and distortion at QP q are read from the stored
per-frame constant-QP encodes (rd_frames.parquet), which ignores that in a real encode a P frame's bits depend on
the QP of the frame it predicts from. Use it to compare settings and controllers; confirm with real encodes.

Controller, before frame t of a GOP with budget B and lookahead k:
  rate model   bits_j(q) = c_type x fp_j x 2^(-(q - 30) / s_type), types I (frame 0) and P; slopes s and priors
               c fitted on TRAIN; online c_P = (sum real P bits + w0 x prior x mean pred) / (sum pred + w0 x mean pred)
  visibility   first-pass bits of frames t..t+k are used as they are; later frames get the mean first-pass bits of
               the P frames seen so far (past + visible), or fp_0 / (I/P ratio on train) before any P frame
  decision     solve for the constant P-frame QP q that spends margin x remaining budget over frames t..29
               (frame 0: I at q - dI); round; limit the change vs the previous P frame to dmax
References (same simulator):
  oracle_cqp   best constant QP in hindsight: the lowest integer QP whose own constant-QP encode fits B
  est_cqp      constant QP = round(base_qp_est_k) from budgets.csv (GOP-start estimate, no feedback)
Score: % bits saved at equal PSNR vs the GOP's own constant-QP curve (PSNR = mean over frames of YUV 6:1:1 PSNR),
minus 2 x % over budget (Pavneet's score, rclib/metrics.py).

  python scripts/controller_v1.py   -> results_v1/controller_v1_prototype.md (+ .csv)
"""
import itertools
import time

import numpy as np
import pandas as pd

D = "/scratch1/aayushso/ee599/data/v1/320x180"
R = "/scratch1/aayushso/ee599/results_v1"
GOP, QLO, QHI, I_OFF = 30, 18, 50, 3          # CQP encodes put the I frame ~3 QP below the P QP (ipratio 1.4)
KS = (0, 2, 5, 10, 29)
FPQ = 32

fr = pd.read_parquet(f"{D}/rd/rd_frames.parquet")
fpd = pd.read_parquet(f"{D}/features/fp_bits.parquet")
bud = pd.read_csv(f"{D}/budgets.csv")
gops = pd.read_csv(f"{D}/gops.csv").set_index(["clip_id", "gop"])

# ---------------------------------------------------------------- per-GOP arrays
cq = fr[fr.kind == "cqp"]
G = {}
for (enc, c, g), d in cq.groupby(["encoder", "clip_id", "gop"]):
    d = d.sort_values(["qp", "frame"])
    nq = d.qp.nunique()
    bits = d.slice_bits.to_numpy(float).reshape(nq, GOP)
    mse = np.stack([d[m].to_numpy(float).reshape(nq, GOP) for m in ("mse_y", "mse_u", "mse_v")], -1)
    G[(enc, c, g)] = {"bits": bits, "mse": mse}
fpw = {(e, c, g): np.maximum(d.sort_values("frame").fp_slice_bits.to_numpy(float), 8)
       for (e, q, c, g), d in fpd[fpd.fp_qp == FPQ].groupby(["encoder", "fp_qp", "clip_id", "gop"])}


def psnr_yuv(mse):
    p = 10 * np.log10(255.0 ** 2 / np.maximum(mse, 1e-10))
    return (6 * p[..., 0] + p[..., 1] + p[..., 2]) / 8


for v in G.values():
    v["cqp_bits"] = v["bits"].sum(1)                      # own constant-QP curve (QP 18..50)
    v["cqp_psnr"] = psnr_yuv(v["mse"]).mean(1)


def frame_at(v, j, q):
    """bits and mse of frame j coded at QP q (I frame: row q + I_OFF of the CQP table)."""
    row = int(np.clip(q + (I_OFF if j == 0 else 0), QLO, QHI)) - QLO
    return v["bits"][row, j], v["mse"][row, j]


def score(v, bits, psnr, B):
    o = np.argsort(v["cqp_psnr"])
    lb = np.interp(psnr, v["cqp_psnr"][o], np.log(v["cqp_bits"][o]))
    sav = 100 * (1 - bits / np.exp(lb))
    over = 100 * max(0.0, bits / B - 1)
    return sav, over, sav - 2 * over


# ---------------------------------------------------------------- rate model fitted on train
def fit_model(enc):
    xi, yi, xp, yp, ci, cp, ip = [], [], [], [], [], [], []
    for (e, c, g), v in G.items():
        if e != enc or gops.loc[(c, g), "split"] != "train":
            continue
        fp = fpw[(e, c, g)]
        ip.append(fp[0] / fp[1:].mean())
        for r, q in enumerate(range(QLO, QHI + 1)):
            xi.append(q - I_OFF - 30); yi.append(np.log2(max(v["bits"][r, 0], 8) / fp[0]))
            xp.append(q - 30); yp.append(np.log2(np.maximum(v["bits"][r, 1:], 8) / fp[1:]).mean())
    s_i, s_p = -1 / np.polyfit(xi, yi, 1)[0], -1 / np.polyfit(xp, yp, 1)[0]
    for (e, c, g), v in G.items():
        if e != enc or gops.loc[(c, g), "split"] != "train":
            continue
        fp, r = fpw[(e, c, g)], 30 - QLO
        ci.append(v["bits"][r, 0] / (fp[0] * 2 ** (I_OFF / s_i)))
        cp.append(v["bits"][r, 1:].sum() / fp[1:].sum())
    return {"s_i": s_i, "s_p": s_p, "c_i": float(np.median(ci)), "c_p": float(np.median(cp)), "ip": float(np.median(ip))}


def run_controller(v, fp, B, k, M, margin, dI, dmax, w0):
    bits, mses, qps = [], [], []
    for t in range(GOP):
        vis = min(k, GOP - 1 - t)
        known = fp[1:t + vis + 1]
        fh = fp.copy()
        fh[t + vis + 1:] = known.mean() if len(known) else fp[0] / M["ip"]
        if t >= 2:
            pp = fp[1:t] * 2 ** (-(np.array(qps[1:t]) - 30) / M["s_p"])
            mp = pp.mean()
            c_p = (sum(bits[1:t]) + w0 * M["c_p"] * mp) / (pp.sum() + w0 * mp)
        else:
            c_p = M["c_p"]
        rem = margin * B - sum(bits)
        jj = np.arange(t, GOP)

        def spend(q):
            s = c_p * (fh[jj[jj > 0]] * 2 ** (-(q - 30) / M["s_p"])).sum()
            if t == 0:
                s += M["c_i"] * fp[0] * 2 ** (-(q - dI - 30) / M["s_i"])
            return s
        lo, hi = 10.0, 51.0
        if rem <= 0:
            q = hi
        else:
            for _ in range(30):
                mid = (lo + hi) / 2
                lo, hi = (lo, mid) if spend(mid) <= rem else (mid, hi)
            q = hi
        qt = int(round(q - dI)) if t == 0 else int(round(q))
        if t >= 2 and dmax < 51:
            qt = int(np.clip(qt, qps[-1] - dmax, qps[-1] + dmax))
        qt = int(np.clip(qt, QLO - (I_OFF if t == 0 else 0), 51))
        b, m = frame_at(v, t, qt)
        bits.append(b); mses.append(m); qps.append(qt)
    tot = sum(bits)
    return tot, psnr_yuv(np.array(mses)).mean(), qps


def evaluate(enc, split, k, params, M, rows_bud):
    out = []
    for r in rows_bud.itertuples():
        v, fp = G[(enc, r.clip_id, r.gop)], fpw[(enc, r.clip_id, r.gop)]
        tot, ps, _ = run_controller(v, fp, r.budget_bits, k, M, *params)
        sav, over, sc = score(v, tot, ps, r.budget_bits)
        out.append((sav, over, sc, tot > r.budget_bits))
    a = np.array(out, float)
    return {"saving": a[:, 0].mean(), "mean over %": a[:, 1].mean(), "score": a[:, 2].mean(), "% over": 100 * a[:, 3].mean()}


def reference(enc, split, k, rows_bud, kind):
    out = []
    for r in rows_bud.itertuples():
        v = G[(enc, r.clip_id, r.gop)]
        if kind == "oracle_cqp":
            ok = np.flatnonzero(v["cqp_bits"] <= r.budget_bits)
            row = ok[0] if len(ok) else len(v["cqp_bits"]) - 1
        else:
            row = int(np.clip(round(getattr(r, f"base_qp_est_k{k}")), QLO, QHI)) - QLO
        tot, ps = v["cqp_bits"][row], v["cqp_psnr"][row]
        sav, over, sc = score(v, tot, ps, r.budget_bits)
        out.append((sav, over, sc, tot > r.budget_bits))
    a = np.array(out, float)
    return {"saving": a[:, 0].mean(), "mean over %": a[:, 1].mean(), "score": a[:, 2].mean(), "% over": 100 * a[:, 3].mean()}


GRID = list(itertools.product((0.97, 1.0), (3, 5), (2, 51), (2.0, 6.0)))   # margin, dI, dmax, w0
res = []
t0 = time.time()
for enc in ("x264", "x265"):
    M = fit_model(enc)
    print(enc, "rate model (train):", {k: round(v, 3) for k, v in M.items()}, flush=True)
    b = bud[bud.encoder == enc]
    val, test = b[b.split == "val"], b[b.split == "test"]
    # tune on val at k = 0 and 5 (pooled), then apply the chosen setting to every k
    tune = []
    for p in GRID:
        s = np.mean([evaluate(enc, "val", k, p, M, val)["score"] for k in (0, 5)])
        tune.append((s, p))
    best = max(tune)[1]
    print(f"  {enc} chosen on val (margin, dI, dmax, w0) = {best}  ({time.time() - t0:.0f}s)", flush=True)
    for split, rb in (("val", val), ("test", test)):
        for k in KS:
            res.append({"encoder": enc, "split": split, "k": k, "method": "online controller",
                        "setting": str(best), **evaluate(enc, split, k, best, M, rb)})
            res.append({"encoder": enc, "split": split, "k": k, "method": "GOP-start estimate, constant",
                        "setting": "linear est.", **reference(enc, split, k, rb, "est")})
        res.append({"encoder": enc, "split": split, "k": "-", "method": "best constant QP (hindsight)",
                    "setting": "", **reference(enc, split, 0, rb, "oracle_cqp")})
    for s, p in sorted(tune, reverse=True)[:5]:
        res.append({"encoder": enc, "split": "val (tuning, k=0/5 mean)", "k": "0,5", "method": "grid top-5",
                    "setting": str(p), "score": s})
T = pd.DataFrame(res)
T.to_csv(f"{R}/controller_v1_prototype.csv", index=False)
L = ["# Online base-QP controller: offline prototype", "",
     "Generated by `scripts/controller_v1.py` (definitions in its docstring). PROTOTYPE: bits and distortion per "
     "frame come from stored constant-QP encodes, not re-encodes, so mixed-QP effects are ignored. Budgets: "
     "`budgets.csv` (clip-level, 4 levels). Settings chosen on val at k = 0 and 5.", ""]
for enc in ("x264", "x265"):
    sub = T[(T.encoder == enc) & (T.split.isin(["val", "test"]))]
    L += [f"## {enc}", "", sub.drop(columns="encoder").round(2).to_markdown(index=False), "",
          "Tuning grid, top 5 on val:", "",
          T[(T.encoder == enc) & (T.method == "grid top-5")][["setting", "score"]].round(3).to_markdown(index=False), ""]
open(f"{R}/controller_v1_prototype.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
