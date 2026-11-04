"""P2 work-queue item 13: native constant-QP R-D curves and first-pass bits for every data-v1 GOP, x264 and x265.

Encoder settings (P1's frozen x264 settings, docs/Ahhana_update.txt; x265 mirrors them):
  common     IPPP (bframes 0), keyint = min-keyint = 30 (one IDR per GOP), no scenecut, AQ off, mb-tree/cutree off,
             psy off, single thread, the clip's own frame rate
  x264       module x264/20250608 (0.165.3222): --preset medium --no-psy --threads 1
  x265       4.1 (copy of Pavneet's build): --preset medium --psy-rd 0 --psy-rdoq 0 --frame-threads 1 --no-wpp
             --pools none --no-open-gop --no-info
  cqp        the encoder's own constant-QP mode, --qp q for q = 18..50 (I frame lower by the default ipratio,
             as in the pilot and Pavneet's "constant QP" curve); decoded with ffmpeg for PSNR
  fp         first pass: --preset ultrafast --qp 30 and --qp 32 (bits only; the team hasn't picked 30 vs 32)
Bits: per frame, from the Annex-B stream. slice_bits = VCL NAL units of the frame; header_bits = the other NAL units
(SPS/PPS/VPS/SEI) sent before it. NAL bytes include the NAL header, exclude start codes.
PSNR: per frame Y/U/V MSE against the source; GOP values in both conventions (mean of per-frame PSNR, PSNR of mean MSE),
for Y and for YUV weighted 6:1:1.

  python scripts/rd_native.py --encoder x264 --shard 3 --nshards 16          one shard (job array task)
  python scripts/rd_native.py --encoder x264 --limit 2 --qps 22,34 --tag smoke   smoke test
  python scripts/rd_native.py --gather                                       merge shards of both encoders
Outputs under data/v1/320x180/rd/:
  shards/<encoder>_<shard>of<n>.parquet   per-frame rows
  rd_frames.parquet     per frame: encoder, kind (cqp|fp), qp, clip_id, gop, frame, slice_bits, header_bits, mse_y/u/v
  rd_native.parquet     per GOP x encoder x QP (cqp): bits and PSNR in both conventions
  ../features/fp_bits.parquet   per frame: encoder, fp_qp, clip_id, gop, frame, fp_slice_bits, fp_header_bits
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
DATA = os.path.join(ROOT, "data", "v1", "320x180")
OUT = os.path.join(DATA, "rd")
GOP = 30
CQP_QPS = list(range(18, 51))
FP_QPS = (30, 32)
X264 = ["--demuxer", "raw", "--input-csp", "i420", "--bframes", "0", "--keyint", "30", "--min-keyint", "30",
        "--no-scenecut", "--aq-mode", "0", "--no-mbtree", "--no-psy", "--threads", "1", "--quiet"]
X265 = ["--input-csp", "i420", "--bframes", "0", "--keyint", "30", "--min-keyint", "30", "--no-scenecut",
        "--no-open-gop", "--aq-mode", "0", "--no-cutree", "--psy-rd", "0", "--psy-rdoq", "0", "--frame-threads", "1",
        "--no-wpp", "--pools", "none", "--no-info", "--log-level", "error"]


def read_frames(y4m, start, n, w, h):
    """n frames from a y4m file starting at frame `start` (plain 'FRAME\\n' markers), as uint8 (n, w*h*3/2)."""
    fs = w * h * 3 // 2
    with open(y4m, "rb") as f:
        hdr = f.readline()
        f.seek(len(hdr) + start * (6 + fs))
        out = np.empty((n, fs), np.uint8)
        for i in range(n):
            mark = f.read(6)
            assert mark == b"FRAME\n", (y4m, start + i, mark)
            out[i] = np.frombuffer(f.read(fs), np.uint8)
    return out


def nal_units(buf):
    b = np.frombuffer(buf, np.uint8)
    z = np.flatnonzero((b[:-2] == 0) & (b[1:-1] == 0) & (b[2:] == 1))
    starts = [p - 1 if p > 0 and b[p - 1] == 0 else p for p in z] + [len(b)]
    for i in range(len(starts) - 1):
        hdr = starts[i] + (4 if b[starts[i] + 2] == 0 else 3)
        yield hdr, starts[i + 1]


def frame_bits(buf, enc):
    """(slice_bits[n], header_bits[n]) per frame in decode order (= display order, no B frames)."""
    sl, hd, pending = [], [], 0
    for s, e in nal_units(buf):
        ln = 8 * (e - s)
        if enc == "x264":
            t = buf[s] & 0x1F
            vcl = 1 <= t <= 5
            first = vcl and bool(buf[s + 1] & 0x80)          # first_mb_in_slice == 0
        else:
            t = (buf[s] >> 1) & 0x3F
            vcl = t < 32
            first = vcl and bool(buf[s + 2] & 0x80)          # first_slice_segment_in_pic_flag
        if not vcl:
            pending += ln
        elif first:
            sl.append(ln)
            hd.append(pending)
            pending = 0
        else:
            sl[-1] += ln
    return np.array(sl, np.int64), np.array(hd, np.int64)


def encode(enc, yuv, w, h, fps, qp, preset, out):
    if enc == "x264":
        cmd = ["x264", *X264, "--input-res", f"{w}x{h}", "--fps", fps, "--preset", preset, "--qp", str(qp),
               "--frames", str(GOP), "-o", out, yuv]
    else:
        cmd = ["x265", "--input", yuv, "--input-res", f"{w}x{h}", "--fps", fps, *X265, "--preset", preset,
               "--qp", str(qp), "--frames", str(GOP), "-o", out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    with open(out, "rb") as f:
        return f.read()


def decode(path, n, w, h):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "yuv420p", "pipe:"],
                       check=True, capture_output=True)
    d = np.frombuffer(r.stdout, np.uint8)
    assert d.size == n * w * h * 3 // 2, (path, d.size)
    return d.reshape(n, -1)


def plane_mse(src, rec, w, h):
    y = w * h
    s, r = src.astype(np.float64), rec.astype(np.float64)
    e = (s - r) ** 2
    return e[:, :y].mean(1), e[:, y:y + y // 4].mean(1), e[:, y + y // 4:].mean(1)


def one_gop(args):
    enc, g, qps, tmpdir = args
    w, h, fps = g["w"], g["h"], g["fps"]
    src = read_frames(g["y4m"], g["start_frame"], GOP, w, h)
    d = tempfile.mkdtemp(dir=tmpdir)
    rows = []
    try:
        yuv = os.path.join(d, "in.yuv")
        src.tofile(yuv)
        out = os.path.join(d, "out.bin")
        base = {"encoder": enc, "clip_id": g["clip_id"], "gop": g["gop"]}
        for qp in qps:
            sl, hd = frame_bits(encode(enc, yuv, w, h, fps, qp, "medium", out), enc)
            assert len(sl) == GOP, (enc, g["clip_id"], g["gop"], qp, len(sl))
            my, mu, mv = plane_mse(src, decode(out, GOP, w, h), w, h)
            for i in range(GOP):
                rows.append({**base, "kind": "cqp", "qp": qp, "frame": i, "slice_bits": sl[i], "header_bits": hd[i],
                             "mse_y": my[i], "mse_u": mu[i], "mse_v": mv[i]})
        for qp in FP_QPS:
            sl, hd = frame_bits(encode(enc, yuv, w, h, fps, qp, "ultrafast", out), enc)
            assert len(sl) == GOP
            for i in range(GOP):
                rows.append({**base, "kind": "fp", "qp": qp, "frame": i, "slice_bits": sl[i], "header_bits": hd[i],
                             "mse_y": np.nan, "mse_u": np.nan, "mse_v": np.nan})
    finally:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        os.rmdir(d)
    return rows


def load_gops():
    man = {r["clip_id"]: r for r in csv.DictReader(open(os.path.join(DATA, "manifest.csv")))}
    gops = []
    for r in csv.DictReader(open(os.path.join(DATA, "gops.csv"))):
        m = man[r["clip_id"]]
        gops.append({"clip_id": r["clip_id"], "gop": int(r["gop"]), "start_frame": int(r["start_frame"]),
                     "w": int(m["width"]), "h": int(m["height"]), "fps": m["fps"],
                     "y4m": os.path.join(DATA, m["path"])})
    return gops


def psnr(m):
    return 10 * np.log10(255.0 ** 2 / np.maximum(m, 1e-10))


def gather():
    import glob
    parts = sorted(glob.glob(os.path.join(OUT, "shards", "*.parquet")))
    df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    n_exp = {e: 0 for e in df.encoder.unique()}
    gops = pd.read_csv(os.path.join(DATA, "gops.csv"))
    for e in n_exp:
        got = df[df.encoder == e][["clip_id", "gop"]].drop_duplicates()
        print(f"{e}: {len(got)} of {len(gops)} GOPs")
    df = df.drop_duplicates(["encoder", "kind", "qp", "clip_id", "gop", "frame"])
    df.to_parquet(os.path.join(OUT, "rd_frames.parquet"), index=False)
    c = df[df.kind == "cqp"].copy()
    c["psnr_y"] = psnr(c.mse_y)
    c["psnr_yuv"] = (6 * psnr(c.mse_y) + psnr(c.mse_u) + psnr(c.mse_v)) / 8
    gl = c.groupby(["encoder", "clip_id", "gop", "qp"]).agg(
        slice_bits=("slice_bits", "sum"), header_bits=("header_bits", "sum"), i_slice_bits=("slice_bits", "first"),
        psnr_y_mean_frames=("psnr_y", "mean"), psnr_yuv_mean_frames=("psnr_yuv", "mean"),
        mse_y=("mse_y", "mean"), mse_u=("mse_u", "mean"), mse_v=("mse_v", "mean")).reset_index()
    gl["psnr_y_from_mse"] = psnr(gl.mse_y)
    gl["psnr_yuv_from_mse"] = (6 * psnr(gl.mse_y) + psnr(gl.mse_u) + psnr(gl.mse_v)) / 8
    gl = gl.merge(gops[["clip_id", "gop", "split", "label"]], on=["clip_id", "gop"], how="left")
    gl.to_parquet(os.path.join(OUT, "rd_native.parquet"), index=False)
    fp = df[df.kind == "fp"].rename(columns={"qp": "fp_qp", "slice_bits": "fp_slice_bits",
                                             "header_bits": "fp_header_bits"})
    fp[["encoder", "fp_qp", "clip_id", "gop", "frame", "fp_slice_bits", "fp_header_bits"]].to_parquet(
        os.path.join(DATA, "features", "fp_bits.parquet"), index=False)
    print(f"wrote rd_frames ({len(df)} rows), rd_native ({len(gl)} rows), features/fp_bits ({len(fp)} rows)")


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
    gops = load_gops()
    mine = gops[a.shard::a.nshards]                   # interleaved, so every shard gets a mix of clips
    if a.limit:
        mine = mine[:a.limit]
    qps = [int(q) for q in a.qps.split(",")] if a.qps else CQP_QPS
    tmp = os.environ.get("RC_TMP") or os.environ.get("TMPDIR", "/tmp")
    os.makedirs(os.path.join(OUT, "shards"), exist_ok=True)
    name = f"{a.encoder}_{a.shard}of{a.nshards}{('_' + a.tag) if a.tag else ''}"
    t0 = time.time()
    with Pool(a.workers) as pool:
        rows = [r for part in pool.imap_unordered(one_gop, [(a.encoder, g, qps, tmp) for g in mine]) for r in part]
    df = pd.DataFrame(rows)
    dest = os.path.join(OUT, "smoke" if a.tag else "shards", name + ".parquet")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    df.to_parquet(dest + ".tmp", index=False)
    os.replace(dest + ".tmp", dest)
    meta = {"encoder": a.encoder, "shard": a.shard, "nshards": a.nshards, "gops": len(mine), "qps": qps,
            "fp_qps": FP_QPS, "seconds": round(time.time() - t0, 1), "host": os.uname().nodename,
            "x264_flags": X264, "x265_flags": X265}
    json.dump(meta, open(dest.replace(".parquet", ".json"), "w"), indent=1)
    print(f"{name}: {len(mine)} GOPs, {len(df)} rows, {time.time() - t0:.0f}s -> {dest}")


if __name__ == "__main__":
    sys.exit(main())
