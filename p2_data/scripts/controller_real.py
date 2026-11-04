"""Causal online base-QP controller, evaluated with REAL encodes (P2 baseline; supersedes the offline prototype in
scripts/controller_v1.py, whose PSNR side is invalid: a P frame's distortion depends on its reference's QP).

Per episode (GOP x budget level x lookahead k x setting): before frame t the controller picks q_t (rule below), then
frames 0..t are re-encoded with a qpfile (prefix property: frames < t are unchanged), and the real bits of frame t
are read back. After frame 29 the GOP is decoded for PSNR.
Encoders: P1's frozen settings (scripts/rd_native.py flags, preset medium) with forced per-frame QP:
  x264 --qp 31 --ipratio 10 --pbratio 10 --qpfile (Ahhana's method; checked 30/30 frames, QP 11-51)
  x265 --qp 31 --qpfile (checked 30/30 frames, QP 11-51)
Rule (rate model fitted on TRAIN constant-QP data only; nothing from the GOP being coded except its first pass):
  bits_j(q) = c_type x fp_j x 2^(-(q - 30) / s_type); c_P updated online with shrinkage w0 towards the train prior;
  frames beyond the lookahead get the mean first-pass bits of P frames seen so far (or fp_0 / I-P ratio);
  q = the constant P QP that spends margin x remaining budget over frames t..29 (frame 0: I at q - dI, and the I
  frame's predicted bits capped at i_cap x B); round; then a per-frame spend cap (fcap) and a limit on the QP
  change per frame (dmax); clip to 11..51. Unseen P frames get the visible P first-pass mean shrunk towards
  fp_0 / (train I-P ratio), so one odd frame cannot set the whole GOP's estimate.
Score: % saved at equal PSNR vs the GOP's own constant-QP curve (PSNR = mean of per-frame YUV 6:1:1 PSNR), minus
2 x % over budget. Budgets: data/v1/320x180/budgets.csv. Slice bits only.

  python scripts/controller_real.py --encoder x264 --split val --ks 0,5 --settings "1.0:3:1.0:2,0.97:3:0.6:2" \
      --shard 0 --nshards 8 --tag tune
  python scripts/controller_real.py --report
Settings string: margin:dI:i_cap:w0[:dmax:fcap[:init:pmin]] (comma-separated list); dmax = max QP change per frame,
fcap = max predicted bits of one frame as a multiple of its share of the remaining budget, init = 0 (I QP from the
solver) or 1 (I QP = GOP-start estimate base_qp_est_k from budgets.csv - dI), pmin = P QP >= I QP + pmin.
"""
import argparse
import glob
import importlib.util
import json
import os
import subprocess
import tempfile
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
D = f"{ROOT}/data/v1/320x180"
OUT = f"{ROOT}/results_v1/controller_real"
GOP, FPQ, QLO, QHI = 30, 32, 11, 51
spec = importlib.util.spec_from_file_location("rd_native", f"{ROOT}/scripts/rd_native.py")
RN = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RN)
MODEL_FILE = f"{D}/rd/controller_model.json"


def fit_model():
    """Slopes and calibration priors per encoder, from the TRAIN GOPs' constant-QP encodes (I frame at q-3)."""
    fr = pd.read_parquet(f"{D}/rd/rd_frames.parquet", filters=[("kind", "==", "cqp")])
    fp = pd.read_parquet(f"{D}/features/fp_bits.parquet")
    fp = fp[fp.fp_qp == FPQ]
    tr = pd.read_csv(f"{D}/gops.csv").query("split == 'train'")[["clip_id", "gop"]]
    fr = fr.merge(tr, on=["clip_id", "gop"]).merge(fp, on=["encoder", "clip_id", "gop", "frame"])
    out = {}
    for enc, d in fr.groupby("encoder"):
        lb = np.log2(np.maximum(d.slice_bits, 8) / np.maximum(d.fp_slice_bits, 8))
        i, p = d.frame == 0, d.frame > 0
        s_i = -1 / np.polyfit(d.qp[i] - 3 - 30, lb[i], 1)[0]
        s_p = -1 / np.polyfit(d.qp[p] - 30, lb[p], 1)[0]
        q30 = d[d.qp == 30]
        g = q30.groupby(["clip_id", "gop"])
        c_i = np.median(q30[q30.frame == 0].slice_bits / (np.maximum(q30[q30.frame == 0].fp_slice_bits, 8) * 2 ** (3 / s_i)))
        c_p = np.median(g.apply(lambda x: x[x.frame > 0].slice_bits.sum() / np.maximum(x[x.frame > 0].fp_slice_bits, 8).sum()))
        ip = np.median(g.apply(lambda x: max(x.fp_slice_bits.iloc[0], 8) / np.maximum(x[x.frame > 0].fp_slice_bits, 8).mean()))
        out[enc] = {"s_i": float(s_i), "s_p": float(s_p), "c_i": float(c_i), "c_p": float(c_p), "ip": float(ip)}
    json.dump(out, open(MODEL_FILE, "w"), indent=1)
    return out


def decide(t, bits, qps, fp, B, k, M, margin, dI, i_cap, w0, dmax=51, fcap=1e9, init=0, pmin=-99, qhat=None,
           wfp=2.0):
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
    if rem <= 0:
        return QHI
    jj = np.arange(max(t, 1), GOP)

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
        # init 0: I QP from the solver; init 1: from the GOP-start estimator (budgets.csv base_qp_est_k, train-fitted)
        q_i = (qhat - dI) if (init == 1 and qhat is not None) else (q - dI)
        while M["c_i"] * fp[0] * 2 ** (-(q_i - 30) / M["s_i"]) > i_cap * B and q_i < QHI:
            q_i += 0.5
        return int(np.clip(round(q_i), QLO, QHI))
    qt = round(q)
    # per-frame spend cap: frame t may not be predicted to use more than fcap x its share of what is left
    share = rem / (GOP - t)
    while c_p * fp[t] * 2 ** (-(qt - 30) / M["s_p"]) > fcap * share and qt < QHI:
        qt += 1
    # limit the QP change: vs the previous P frame, or vs I QP + dI at frame 1
    ref = qps[-1] if t >= 2 else qps[0] + dI
    if dmax < 51:
        qt = int(np.clip(qt, ref - dmax, ref + dmax))
    qt = max(qt, qps[0] + pmin)                      # P frames never get a lower QP than I QP + pmin
    return int(np.clip(qt, QLO, QHI))


def saving(bits, psnr, curve):
    """% bits saved vs the GOP's constant-QP curve at equal PSNR; piecewise linear in log bits, extrapolated linearly
    beyond the curve's ends (same as Pavneet's rclib/metrics.saving, so scores are comparable)."""
    o = np.argsort(curve["psnr"])
    p, lb = curve["psnr"][o], np.log(curve["bits"][o])
    if psnr > p[-1]:
        y = lb[-1] + (psnr - p[-1]) * (lb[-1] - lb[-2]) / max(p[-1] - p[-2], 1e-9)
    elif psnr < p[0]:
        y = lb[0] + (psnr - p[0]) * (lb[1] - lb[0]) / max(p[1] - p[0], 1e-9)
    else:
        y = np.interp(psnr, p, lb)
    return 100 * (1 - bits / np.exp(y))


def encode_prefix(enc, yuv, n, qps, fps, d):
    qf, out = os.path.join(d, "qp.txt"), os.path.join(d, "out.bin")
    with open(qf, "w") as f:
        for i, q in enumerate(qps):
            f.write(f"{i} {'I' if i == 0 else 'P'} {int(q)}\n")
    if enc == "x264":
        cmd = ["x264", *RN.X264, "--input-res", "320x180", "--fps", fps, "--preset", "medium", "--qp", "31",
               "--ipratio", "10", "--pbratio", "10", "--qpfile", qf, "--frames", str(n), "-o", out, yuv]
    else:
        cmd = ["x265", "--input", yuv, "--input-res", "320x180", "--fps", fps, *RN.X265, "--preset", "medium",
               "--qp", "31", "--qpfile", qf, "--frames", str(n), "-o", out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    buf = open(out, "rb").read()
    return RN.frame_bits(buf, enc)[0], out


def episode(args):
    enc, g, B, level, k, setting, M, curve, tmp, qhat = args
    src = RN.read_frames(g["y4m"], g["start_frame"], GOP, 320, 180)
    fp = np.maximum(np.asarray(g["fp"], float), 8)
    d = tempfile.mkdtemp(dir=tmp)
    try:
        yuv = os.path.join(d, "in.yuv")
        src.tofile(yuv)
        bits, qps = [], []
        for t in range(GOP):
            qps.append(decide(t, bits, qps, fp, B, k, M, *setting, qhat=qhat))
            sl, out = encode_prefix(enc, yuv, t + 1, qps, g["fps"], d)
            assert len(sl) == t + 1 and (t == 0 or list(sl[:t]) == bits), "prefix property broken"
            bits = [int(x) for x in sl]
        my, mu, mv = RN.plane_mse(src, RN.decode(out, GOP, 320, 180), 320, 180)
        ps = (6 * RN.psnr(my) + RN.psnr(mu) + RN.psnr(mv)) / 8
        tot, psnr = float(sum(bits)), float(ps.mean())
        sav = saving(tot, psnr, curve)
        over = 100 * max(0.0, tot / B - 1)
        return {"encoder": enc, "clip_id": g["clip_id"], "gop": g["gop"], "level_q0": level, "k": k,
                "setting": ":".join(map(str, setting)), "budget_bits": B, "bits": tot, "psnr_yuv": psnr,
                "saving": sav, "over_pct": over, "over": tot > B, "score": sav - 2 * over, "qps": qps}
    finally:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        os.rmdir(d)


def run(a):
    M = json.load(open(MODEL_FILE))[a.encoder] if os.path.exists(MODEL_FILE) else fit_model()[a.encoder]
    man = {r.clip_id: r for r in pd.read_csv(f"{D}/manifest.csv").itertuples()}
    gops = pd.read_csv(f"{D}/gops.csv")
    gops = gops[gops.split == a.split]
    bud = pd.read_csv(f"{D}/budgets.csv").query("encoder == @a.encoder")
    rd = pd.read_parquet(f"{D}/rd/rd_native.parquet").query("encoder == @a.encoder")
    fp = pd.read_parquet(f"{D}/features/fp_bits.parquet").query("encoder == @a.encoder and fp_qp == @FPQ")
    fpd = {k: v.sort_values("frame").fp_slice_bits.to_numpy() for k, v in fp.groupby(["clip_id", "gop"])}
    curves = {k: {"bits": v.slice_bits.to_numpy(float), "psnr": v.psnr_yuv_mean_frames.to_numpy(float)}
              for k, v in rd.groupby(["clip_id", "gop"])}
    glist = list(gops.itertuples())[a.shard::a.nshards]
    if a.every > 1:
        glist = glist[::a.every]
    if a.limit:
        glist = glist[:a.limit]
    levels = [int(x) for x in a.levels.split(",")]
    ks = [int(x) for x in a.ks.split(",")]
    settings = [tuple(float(x) for x in s.split(":")) for s in a.settings.split(",")]
    tmp = os.environ.get("RC_TMP") or os.environ.get("TMPDIR", "/tmp")
    items = []
    for g in glist:
        m = man[g.clip_id]
        gd = {"clip_id": g.clip_id, "gop": g.gop, "start_frame": g.start_frame, "fps": m.fps,
              "y4m": os.path.join(D, m.path), "fp": fpd[(g.clip_id, g.gop)]}
        bb = bud[(bud.clip_id == g.clip_id) & (bud.gop == g.gop)].set_index("level_q0")
        for lv in levels:
            for k in ks:
                for s in settings:
                    items.append((a.encoder, gd, float(bb.budget_bits[lv]), lv, k, s, M, curves[(g.clip_id, g.gop)],
                                  tmp, float(bb[f"base_qp_est_k{k}"][lv])))
    t0 = time.time()
    with Pool(a.workers) as p:
        rows = list(p.imap_unordered(episode, items, chunksize=1))
    os.makedirs(OUT, exist_ok=True)
    name = f"{a.tag + '_' if a.tag else ''}{a.encoder}_{a.split}_{a.shard}of{a.nshards}"
    pd.DataFrame(rows).to_parquet(f"{OUT}/{name}.parquet", index=False)
    print(f"{name}: {len(rows)} episodes from {len(glist)} GOPs in {time.time() - t0:.0f}s "
          f"({(time.time() - t0) * a.workers / max(len(rows), 1):.1f} CPU-s/episode)")


def report():
    rows = pd.concat([pd.read_parquet(p).assign(file=os.path.basename(p)) for p in glob.glob(f"{OUT}/*.parquet")])
    rows["run"] = rows.file.str.split("_").str[0]
    agg = rows.groupby(["run", "encoder", "setting", "k"]).agg(
        episodes=("score", "size"), score=("score", "mean"), saving=("saving", "mean"),
        pct_over=("over", lambda s: 100 * s.mean()), mean_over=("over_pct", "mean")).reset_index()
    print(agg.round(2).to_string(index=False))
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", choices=("x264", "x265"))
    ap.add_argument("--split", default="val")
    ap.add_argument("--ks", default="0,2,5,10,29")
    ap.add_argument("--levels", default="24,30,36,42")
    ap.add_argument("--settings", default="1.0:3:1.0:2")
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--every", type=int, default=1, help="use every n-th GOP of the shard (tuning subsets)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", 2)))
    ap.add_argument("--tag", default="")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--fit", action="store_true", help="(re)fit the train-only rate model")
    a = ap.parse_args()
    if a.fit:
        print(json.dumps(fit_model(), indent=1))
    elif a.report:
        report()
    else:
        run(a)


if __name__ == "__main__":
    main()
