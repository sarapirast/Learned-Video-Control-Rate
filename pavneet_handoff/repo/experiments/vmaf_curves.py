"""D49: VMAF constant-QP curves for dataset v1 (evaluation metric only; nothing is retrained).

For every val / test GOP and every QP 18..50, the encoder's constant-QP encode (the same command as the PSNR curves:
FORCED_ARGS + --qp q, v1 settings) is decoded and scored with Netflix's VMAF (default model vmaf_v0.6.1) at
  native : 320x180, as coded
  1080   : reference and decoded frames both upscaled to 1920x1080 (bicubic, ffmpeg), the viewing condition the
           default model was trained for
Bits are checked against the stored PSNR curve's bits (same encodes), so the VMAF curve lines up with every lookup the
stream / live levels already do: a GOP coded at constant QP q has per-frame VMAF row q.

  RC_V1=1 RC_PRESET=medium RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 \
      python experiments/vmaf_curves.py --scale native|1080 --shard i --nshards N [--limit G]
Output: $RC_WORK/results_vmaf/<scale>/<i>of<N>.pkl  {gid: {"bits": int[33], "vmaf": float[33, 30]}}; --limit -> _debug.
"""
import argparse
import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import codec, config as C, data  # noqa: E402

VMAF = os.environ.get("RC_VMAF", "/scratch1/pbanga/envs/vmaf/bin/vmaf")
SPLITS = ("val", "test")
UP = (1920, 1080)


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def upscale(src, dst):
    codec._run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p",
                "-s", f"{C.W}x{C.H}", "-i", src, "-vf", f"scale={UP[0]}:{UP[1]}:flags=bicubic",
                "-f", "rawvideo", "-pix_fmt", "yuv420p", dst])


def vmaf(ref, dist, w, h, d):
    out = os.path.join(d, "v.json")
    subprocess.run([VMAF, "-r", ref, "-d", dist, "-w", str(w), "-h", str(h), "-p", "420", "-b", "8",
                    "--threads", "1", "--json", "-o", out, "-q"], check=True, capture_output=True)
    fr = json.load(open(out))["frames"]
    return np.array([f["metrics"]["vmaf"] for f in sorted(fr, key=lambda f: f["frameNum"])], float)


def gop_curve(info, scale, d):
    p = data.gop_path(info["gop"])
    ref = p
    if scale == "1080":
        ref = os.path.join(d, "ref_up.yuv")
        upscale(p, ref)
    w, h = (C.W, C.H) if scale == "native" else UP
    bits, v = [], []
    out = os.path.join(d, "out." + ("hevc" if C.CODEC == "x265" else "264"))
    dec = os.path.join(d, "dec.yuv")
    for q in C.QPS:
        codec._run(codec._cmd(C.CODEC, p, C.GOP, out, [*codec.FORCED_ARGS[C.CODEC], "--qp", str(int(q))]))
        with open(out, "rb") as f:
            b = codec.frame_bits(f.read(), C.CODEC)
        assert len(b) == C.GOP, len(b)
        bits.append(int(b.sum()))
        codec.decode(out, C.GOP).tofile(dec)
        dist = dec
        if scale == "1080":
            dist = os.path.join(d, "dec_up.yuv")
            upscale(dec, dist)
        v.append(vmaf(ref, dist, w, h, d))
    return np.array(bits), np.stack(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", choices=("native", "1080"), required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="debug: first G GOPs of the shard, output under _debug")
    a = ap.parse_args()
    assert C.V1, "run with RC_V1=1 (v1 encoder settings, as the curves)"
    assert os.access(VMAF, os.X_OK), f"VMAF binary not found: {VMAF}"
    od = os.path.join(C.results_dir("vmaf"), a.scale + ("_debug" if a.limit else ""))
    os.makedirs(od, exist_ok=True)
    p = os.path.join(od, f"{a.shard}of{a.nshards}.pkl")
    if os.path.exists(p):
        log(f"{p}: done")
        return
    infos = pickle.load(open(os.path.join(C.WORK, "results_infos", "infos.pkl"), "rb"))
    gids = sorted(g for g, x in infos.items() if x["gop"]["split"] in SPLITS)
    gids = data.shard(gids, a.nshards, a.shard)
    if a.limit:
        gids = gids[:a.limit]
    t0, R, bad = time.time(), {}, 0
    d = tempfile.mkdtemp(dir=codec._tmpdir())
    try:
        for j, g in enumerate(gids):
            b, v = gop_curve(infos[g], a.scale, d)
            ref = np.asarray(infos[g]["curve"]["bits"])
            bad += int(not np.array_equal(b, ref))
            R[g] = {"bits": b, "vmaf": v}
            if j % 10 == 0 or a.limit:
                log(f"{a.scale} shard {a.shard}: {j + 1}/{len(gids)} GOPs, {(time.time() - t0) / 60:.1f} min; "
                    f"{g} VMAF at QP 18/30/42/50 {v[[0, 12, 24, 32]].mean(1).round(1).tolist()}; bits mismatch {bad}")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    pickle.dump({"rows": R, "bits_mismatch": bad, "seconds": time.time() - t0, "vmaf": VMAF}, open(p, "wb"))
    log(f"{p}: {len(R)} GOPs, bits mismatch vs PSNR curve {bad}, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
