"""Per-frame first-pass statistics for every data-v1 GOP, x264 and x265 (richer first-pass features; see
docs/lit-survey-features-2026-11-04.md, "cheapest real upgrade").

The first pass is the same ultrafast constant-QP encode as features/fp_bits.parquet (scripts/rd_native.py flags,
P1's frozen settings), run with --pass 1 --stats; each frame's stats line is parsed:
  x264: q, tex (texture bits), mv (motion-vector bits), misc (other bits), imb / pmb / smb (intra / inter / skipped
        macroblocks, 16x16)
  x265: q, tex, mv, misc, icu / pcu / scu (intra / inter / skipped CUs, in 16x16 units)
Columns are unified: intra_blocks, inter_blocks, skip_blocks (out of 20 x 12 = 240 blocks at 320x180).
slice_bits = the frame's VCL bits counted from the stream (as in fp_bits.parquet).

  python scripts/fp_stats.py --encoder x264 --nshards 4        one shard (= array task id)
  python scripts/fp_stats.py --encoder x264 --limit 2 --tag smoke
  python scripts/fp_stats.py --gather                          -> data/v1/320x180/features/fp_stats.parquet
"""
import argparse
import glob
import importlib.util
import os
import re
import subprocess
import tempfile
import time
from multiprocessing import Pool

import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
spec = importlib.util.spec_from_file_location("rd_native", f"{ROOT}/scripts/rd_native.py")
RN = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RN)
OUT = os.path.join(RN.DATA, "features", "fp_stats_shards")
FP_QPS = (30, 32)
KEYS = {"x264": ("imb", "pmb", "smb"), "x265": ("icu", "pcu", "scu")}
LINE = re.compile(r"(\w[\w-]*):([^\s;]+)")


def parse_stats(path, enc):
    rows = []
    for ln in open(path):
        if not ln.startswith("in:"):
            continue
        f = dict(LINE.findall(ln))
        i, p, s = KEYS[enc]
        rows.append({"frame": int(f["in"]), "type": f["type"], "q": float(f["q"]), "tex": float(f["tex"]),
                     "mv": float(f["mv"]), "misc": float(f["misc"]), "intra_blocks": float(f[i]),
                     "inter_blocks": float(f[p]), "skip_blocks": float(f[s])})
    return sorted(rows, key=lambda r: r["frame"])


def first_pass(enc, yuv, fps, qp, d):
    st, out = os.path.join(d, "fp.stats"), os.path.join(d, "fp.bin")
    if enc == "x264":
        cmd = ["x264", *RN.X264, "--input-res", "320x180", "--fps", fps, "--preset", "ultrafast", "--qp", str(qp),
               "--pass", "1", "--stats", st, "--frames", str(RN.GOP), "-o", out, yuv]
    else:
        cmd = ["x265", "--input", yuv, "--input-res", "320x180", "--fps", fps, *RN.X265, "--preset", "ultrafast",
               "--qp", str(qp), "--pass", "1", "--stats", st, "--frames", str(RN.GOP), "-o", out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    rows = parse_stats(st, enc)
    sl, _ = RN.frame_bits(open(out, "rb").read(), enc)
    assert len(rows) == RN.GOP == len(sl), (enc, len(rows), len(sl))
    for r, b in zip(rows, sl):
        r["slice_bits"] = int(b)
    return rows


def one_gop(args):
    enc, g, tmp = args
    src = RN.read_frames(g["y4m"], g["start_frame"], RN.GOP, g["w"], g["h"])
    d = tempfile.mkdtemp(dir=tmp)
    out = []
    try:
        yuv = os.path.join(d, "in.yuv")
        src.tofile(yuv)
        for qp in FP_QPS:
            for r in first_pass(enc, yuv, g["fps"], qp, d):
                out.append({"encoder": enc, "fp_qp": qp, "clip_id": g["clip_id"], "gop": g["gop"], **r})
    finally:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        os.rmdir(d)
    return out


def gather():
    df = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(os.path.join(OUT, "*.parquet")))], ignore_index=True)
    df = df.drop_duplicates(["encoder", "fp_qp", "clip_id", "gop", "frame"])
    n = df.groupby("encoder").apply(lambda d: d[["clip_id", "gop"]].drop_duplicates().shape[0]).to_dict()
    dest = os.path.join(RN.DATA, "features", "fp_stats.parquet")
    df.to_parquet(dest, index=False)
    print(f"GOPs per encoder: {n}; wrote {dest} ({len(df)} rows)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", choices=("x264", "x265"))
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", 2)))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--gather", action="store_true")
    a = ap.parse_args()
    if a.gather:
        return gather()
    gops = RN.load_gops()[a.shard::a.nshards]
    if a.limit:
        gops = gops[:a.limit]
    tmp = os.environ.get("RC_TMP") or os.environ.get("TMPDIR", "/tmp")
    t0 = time.time()
    with Pool(a.workers) as p:
        rows = [r for part in p.imap_unordered(one_gop, [(a.encoder, g, tmp) for g in gops]) for r in part]
    dest_dir = OUT + ("_" + a.tag if a.tag else "")
    os.makedirs(dest_dir, exist_ok=True)
    name = f"{a.encoder}_{a.shard}of{a.nshards}.parquet"
    pd.DataFrame(rows).to_parquet(os.path.join(dest_dir, name), index=False)
    print(f"{a.encoder} shard {a.shard}/{a.nshards}: {len(gops)} GOPs, {len(rows)} rows, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
