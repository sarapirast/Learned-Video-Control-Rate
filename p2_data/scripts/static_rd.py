"""STATIC (the pilot's spend-early pattern) R-D curves for every data-v1 GOP, x264 and x265, plus the two STATIC
baselines for every split, budget level and k.

STATIC = Pavneet's rclib/config.py STATIC = (-6, -3, +3), STATIC_SPLIT = 10: per-frame QP offsets on a base q of
  I frame -6, P frames 1-9 -3, P frames 10-29 +3        (a step, not a ramp)
It does not depend on the GOP or the budget, so it is encoded once per GOP at every base q in 12..51 (per-frame QPs
clipped to 0..51) and both baselines become lookups on that curve, for any budget and any k:
  static_best     lowest base q whose STATIC encode fits B (hindsight shift; the pilot's reference baseline). If none
                  fits, q = 51 (over budget).
  static_causal   base q = round(base_qp_est_k) from budgets.csv (causal estimator at lookahead k, no feedback).
These replace fixed_best / fixed_causal in scripts/baselines_v1.py, which used a linear ramp (-3 .. +3 over the P frames)
by mistake; those rows are kept in the table as ramp_best / ramp_causal.
Forced per-frame QPs use P1's method (x264 --qp 31 --ipratio 10 --pbratio 10 --qpfile; x265 --qp 31 --qpfile) and
P1's frozen settings (scripts/rd_native.py flags, preset medium).

  python scripts/static_rd.py --encoder x264 --nshards 8          one shard (= array task id), all splits
  python scripts/static_rd.py --encoder x264 --limit 1 --qps 24,36 --tag smoke
  python scripts/static_rd.py --gather
Outputs:
  data/v1/320x180/rd/static_shards/<enc>_<i>of<n>.parquet   per-frame rows
  data/v1/320x180/rd/static_frames.parquet   per frame: encoder, base_q, clip_id, gop, frame, qp, slice_bits,
                                             header_bits, mse_y/u/v
  data/v1/320x180/rd/static_rd.parquet       per GOP x encoder x base_q: bits, PSNR (mean over frames, YUV 6:1:1 and Y)
  results_v1/baselines_v1/rows_static_all.parquet   static_best / static_causal rows, all splits (picked up by
                                             scripts/baselines_v1.py --gather)
"""
import argparse
import glob
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
D = f"{ROOT}/data/v1/320x180"
OUT = f"{D}/rd"
GOP = 30
KS = (0, 2, 5, 10, 29)
BASE_QS = list(range(12, 52))
STATIC = np.array([-6] + [-3] * 9 + [3] * 20)   # = static_offsets() in repo-pavneet/rclib/config.py
assert len(STATIC) == GOP


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


BL = _load("baselines_v1", f"{ROOT}/scripts/baselines_v1.py")
RN, CR = BL.RN, BL.CR


def static_qps(q):
    return [int(x) for x in np.clip(q + STATIC, 0, 51)]


def one_gop(args):
    enc, g, qs, tmp = args
    src = RN.read_frames(g["y4m"], g["start_frame"], GOP, 320, 180)
    d = tempfile.mkdtemp(dir=tmp)
    rows = []
    try:
        yuv, out = os.path.join(d, "in.yuv"), os.path.join(d, "o.bin")
        src.tofile(yuv)
        for q in qs:
            qps = static_qps(q)
            BL.forced(enc, yuv, g["fps"], out, qps, d)
            sl, hd = RN.frame_bits(open(out, "rb").read(), enc)
            assert len(sl) == GOP, (enc, g["clip_id"], g["gop"], q, len(sl))
            my, mu, mv = RN.plane_mse(src, RN.decode(out, GOP, 320, 180), 320, 180)
            for i in range(GOP):
                rows.append({"encoder": enc, "base_q": q, "clip_id": g["clip_id"], "gop": g["gop"], "frame": i,
                             "qp": qps[i], "slice_bits": int(sl[i]), "header_bits": int(hd[i]),
                             "mse_y": my[i], "mse_u": mu[i], "mse_v": mv[i]})
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return rows


def gather():
    parts = sorted(glob.glob(f"{OUT}/static_shards/*.parquet"))
    fr = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    fr = fr.drop_duplicates(["encoder", "base_q", "clip_id", "gop", "frame"])
    gops = pd.read_csv(f"{D}/gops.csv")
    for e, x in fr.groupby("encoder"):
        n = x[["clip_id", "gop"]].drop_duplicates().shape[0]
        nq = x.groupby(["clip_id", "gop"]).base_q.nunique()
        print(f"{e}: {n} of {len(gops)} GOPs, base q per GOP min {nq.min()} max {nq.max()} (expect {len(BASE_QS)})")
    fr.to_parquet(f"{OUT}/static_frames.parquet", index=False)
    fr["psnr_y"] = RN.psnr(fr.mse_y)
    fr["psnr_yuv"] = (6 * RN.psnr(fr.mse_y) + RN.psnr(fr.mse_u) + RN.psnr(fr.mse_v)) / 8
    gl = fr.groupby(["encoder", "clip_id", "gop", "base_q"]).agg(
        slice_bits=("slice_bits", "sum"), header_bits=("header_bits", "sum"),
        psnr_yuv_mean_frames=("psnr_yuv", "mean"), psnr_y_mean_frames=("psnr_y", "mean"),
        clipped=("qp", lambda s: bool(((s == 0) | (s == 51)).any()))).reset_index()
    gl = gl.merge(gops[["clip_id", "gop", "split", "label"]], on=["clip_id", "gop"], how="left")
    gl.to_parquet(f"{OUT}/static_rd.parquet", index=False)
    print(f"wrote static_frames ({len(fr)} rows), static_rd ({len(gl)} rows)")

    # baselines, every split: lookups on the STATIC curve
    rows = []
    bud = pd.read_csv(f"{D}/budgets.csv")
    for enc in ("x264", "x265"):
        _, cur = BL.curves_for(enc)
        si = gl[gl.encoder == enc].set_index(["clip_id", "gop", "base_q"]).sort_index()
        for r in bud[bud.encoder == enc].itertuples():
            g = {"split": r.split, "clip_id": r.clip_id, "gop": r.gop, "label": r.label}
            c = si.loc[(r.clip_id, r.gop)]
            ok = c.index[c.slice_bits.to_numpy() <= r.budget_bits]
            choices = [("static_best", 29, False, int(ok.min()) if len(ok) else int(c.index.max()))]
            choices += [("static_causal", k, True,
                         int(np.clip(round(getattr(r, f"base_qp_est_k{k}")), BASE_QS[0], BASE_QS[-1]))) for k in KS]
            for method, k, causal, q in choices:
                x = c.loc[q]
                rows.append(BL.row(method, enc, g, r.level_q0, k, r.budget_bits, int(x.slice_bits),
                                   int(x.header_bits), float(x.psnr_yuv_mean_frames), float(x.psnr_y_mean_frames),
                                   cur[(r.clip_id, r.gop)], causal, q))
    df = pd.DataFrame(rows)
    os.makedirs(BL.OUT, exist_ok=True)
    df.to_parquet(f"{BL.OUT}/rows_static_all.parquet", index=False)
    s = df.groupby(["split", "method", "k", "encoder"]).agg(score=("score", "mean"),
                                                             pct_over=("over", lambda v: 100 * v.mean()))
    print(s.unstack("encoder").round(2).to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", choices=("x264", "x265"))
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", 2)))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--qps", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--gather", action="store_true")
    a = ap.parse_args()
    if a.gather:
        return gather()
    man = {r.clip_id: r for r in pd.read_csv(f"{D}/manifest.csv").itertuples()}
    glist = list(pd.read_csv(f"{D}/gops.csv").itertuples())[a.shard::a.nshards]   # all splits, interleaved
    if a.limit:
        glist = glist[:a.limit]
    qs = [int(q) for q in a.qps.split(",")] if a.qps else BASE_QS
    tmp = os.environ.get("RC_TMP") or os.environ.get("TMPDIR", "/tmp")
    items = [(a.encoder, {"clip_id": g.clip_id, "gop": g.gop, "start_frame": g.start_frame,
                          "fps": man[g.clip_id].fps, "y4m": os.path.join(D, man[g.clip_id].path)}, qs, tmp)
             for g in glist]
    t0 = time.time()
    with Pool(a.workers) as p:
        rows = [r for part in p.imap_unordered(one_gop, items) for r in part]
    sub = "smoke_static" if a.tag else "static_shards"
    os.makedirs(f"{OUT}/{sub}", exist_ok=True)
    dest = f"{OUT}/{sub}/{a.encoder}_{a.shard}of{a.nshards}{('_' + a.tag) if a.tag else ''}.parquet"
    if os.path.exists(dest):
        dest = dest.replace(".parquet", f"_{os.environ.get('SLURM_JOB_ID') or time.strftime('%H%M%S')}.parquet")
    pd.DataFrame(rows).to_parquet(dest + ".tmp", index=False)
    os.replace(dest + ".tmp", dest)
    json.dump({"encoder": a.encoder, "shard": a.shard, "nshards": a.nshards, "gops": len(glist), "base_qs": qs,
               "static": STATIC.tolist(), "seconds": round(time.time() - t0, 1), "host": os.uname().nodename},
              open(dest.replace(".parquet", ".json"), "w"), indent=1)
    print(f"{a.encoder} shard {a.shard}/{a.nshards}: {len(glist)} GOPs x {len(qs)} base q, {len(rows)} rows, "
          f"{time.time() - t0:.0f}s -> {dest}")


if __name__ == "__main__":
    sys.exit(main())
