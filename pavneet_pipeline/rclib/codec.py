"""Encoder harness for x265 and x264: per-frame forced QPs, the encoders' own rate control, real bits, real PSNR.

Every encode reads a raw 320x180 yuv420p GOP file, writes an Annex-B bitstream into a private temp dir, counts each
frame's bits from that bitstream (VCL + parameter-set NAL units; SEI/AUD excluded, see D9), and decodes the bitstream
with ffmpeg to measure per-frame PSNR against the source. Both encoders obey per-frame QPs exactly only with adaptive
quantisation and cutree/mb-tree off, which FORCED_ARGS sets; `tools/codec_check.py` verifies it.
"""
import os
import shutil
import subprocess
import tempfile
import time

import numpy as np

from . import config as C

PRESET = os.environ.get("RC_PRESET", "fast")
FPS = 30
TIMEOUT, RETRIES = 120, 3

COMMON = {
    "x265": ["--input-res", f"{C.W}x{C.H}", "--input-csp", "i420", "--fps", str(FPS), "--preset", PRESET,
             "--keyint", str(C.GOP), "--min-keyint", str(C.GOP), "--no-scenecut", "--bframes", "0", "--no-open-gop",
             "--frame-threads", "1", "--no-wpp", "--pools", "none", "--no-info", "--log-level", "error"],
    "x264": ["--demuxer", "raw", "--input-res", f"{C.W}x{C.H}", "--input-csp", "i420", "--fps", str(FPS),
             "--preset", PRESET, "--keyint", str(C.GOP), "--min-keyint", str(C.GOP), "--no-scenecut", "--bframes", "0",
             "--threads", "1", "--quiet"],
}
FORCED_ARGS = {
    "x265": ["--aq-mode", "0", "--no-cutree"],
    "x264": ["--aq-mode", "0", "--no-mbtree"],
}
# rate-control mode that carries the qpfile: x264 ignores qpfile QPs under --qp but obeys them exactly under --crf
# (with AQ and mb-tree off); x265 obeys them under --qp. Verified by tools/codec_check.py (L3 in docs/LEARNINGS.md).
def _carrier(codec, q):
    return ["--qp", str(q)] if codec == "x265" else ["--crf", str(q)]


# the encoders' own adaptive tools, used only by the "own rate control" baselines
OWN_AQ_ARGS = {
    "x265": ["--aq-mode", "2", "--cutree"],
    "x264": ["--aq-mode", "1", "--mbtree"],
}


def _tmpdir():
    d = os.path.join(C.TMP, f"rc_{os.getuid()}_{os.getpid()}")
    os.makedirs(d, exist_ok=True)
    return d


def _run(cmd, **kw):
    last = None
    for attempt in range(RETRIES):
        try:
            return subprocess.run(cmd, check=True, timeout=TIMEOUT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            last = e
            time.sleep(0.5 * (attempt + 1))
    err = getattr(last, "stderr", b"") or b""
    raise RuntimeError(f"failed after {RETRIES} tries: {' '.join(cmd)}\n{err.decode(errors='replace')[-2000:]}")


# ---------------------------------------------------------------- bitstream parsing

def _nal_units(buf):
    """Yield (offset, length incl. start code) for every Annex-B NAL unit."""
    b = np.frombuffer(buf, np.uint8)
    # positions of 00 00 01
    z = np.flatnonzero((b[:-2] == 0) & (b[1:-1] == 0) & (b[2:] == 1))
    starts = []
    for p in z:
        starts.append(p - 1 if p > 0 and b[p - 1] == 0 else p)   # 4-byte start code
    starts.append(len(b))
    for i in range(len(starts) - 1):
        hdr = starts[i] + (4 if b[starts[i] + 2] == 0 else 3)
        yield starts[i], starts[i + 1] - starts[i], hdr


def frame_bits(buf, codec):
    """Bits per frame (decode order == display order: no B-frames). Parameter sets count toward the next frame.
    NAL payload only (start codes excluded), which matches x265's own per-frame CSV bits exactly for P frames."""
    out, pending = [], 0
    b = buf
    for off, ln, hdr in _nal_units(b):
        ln -= hdr - off
        if codec == "x265":
            t = (b[hdr] >> 1) & 0x3F
            vcl, params, first = t < 32, t in (32, 33, 34), None
            if vcl:
                first = b[hdr + 2] & 0x80   # first_slice_segment_in_pic_flag
        else:
            t = b[hdr] & 0x1F
            vcl, params = t in (1, 5), t in (7, 8)
            first = None
            if vcl:
                first = _h264_first_mb_is_zero(b, hdr + 1)
        if params:
            pending += ln
        elif vcl:
            if first or not out:
                out.append(pending + ln)
                pending = 0
            else:
                out[-1] += ln
    return np.asarray(out, np.int64) * 8


def _h264_first_mb_is_zero(b, p):
    # first_mb_in_slice is ue(v); value 0 is coded as a single '1' bit
    return bool(b[p] & 0x80)


# ---------------------------------------------------------------- decoding + PSNR

def _read_frames(path, n):
    raw = np.fromfile(path, np.uint8, count=n * C.FRAME_BYTES)
    return raw.reshape(n, C.FRAME_BYTES)


def _psnr(src, rec):
    """Per-frame PSNR: Y, U, V and the 6:1:1 weighted YUV PSNR used as the score's quality metric (D10)."""
    ys = C.W * C.H
    cs = ys // 4
    d = src.astype(np.int32) - rec.astype(np.int32)
    d2 = d * d
    mse = np.stack([d2[:, :ys].mean(1), d2[:, ys:ys + cs].mean(1), d2[:, ys + cs:].mean(1)], 1)
    p = 10 * np.log10(255.0 ** 2 / np.maximum(mse, 1e-10))
    p = np.minimum(p, 100.0)
    return (6 * p[:, 0] + p[:, 1] + p[:, 2]) / 8, p


def decode(bitstream, n):
    r = _run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", bitstream, "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"])
    rec = np.frombuffer(r.stdout, np.uint8)
    assert rec.size == n * C.FRAME_BYTES, (rec.size, n)
    return rec.reshape(n, C.FRAME_BYTES)


# ---------------------------------------------------------------- encodes

def _qpfile(path, qps):
    with open(path, "w") as f:
        for i, q in enumerate(qps):
            f.write(f"{i} {'I' if i == 0 else 'P'} {int(q)}\n")


def _cmd(codec, gop_path, n, out, extra):
    if codec == "x265":
        return ["x265", "--input", gop_path, "--frames", str(n), *COMMON["x265"], *extra, "-o", out]
    return ["x264", *COMMON["x264"], "--frames", str(n), *extra, "-o", out, gop_path]


def encode(gop_path, qps, codec=None, preset_args=(), measure=True, src=None):
    """Encode the first len(qps) frames of a GOP at exactly these QPs.

    Returns dict(bits=int64[n], psnr=float[n] (weighted YUV), psnr_yuv=float[n,3], total_bits, mean_psnr).
    """
    codec = codec or C.CODEC
    qps = [int(np.clip(q, 0, 51)) for q in qps]
    n = len(qps)
    d = tempfile.mkdtemp(dir=_tmpdir())
    try:
        qf, out = os.path.join(d, "qp.txt"), os.path.join(d, "out." + ("hevc" if codec == "x265" else "264"))
        _qpfile(qf, qps)
        _run(_cmd(codec, gop_path, n, out, [*FORCED_ARGS[codec], *_carrier(codec, qps[0]), "--qpfile", qf, *preset_args]))
        return _measure(out, gop_path, n, codec, measure, src)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _measure(out, gop_path, n, codec, measure, src):
    with open(out, "rb") as f:
        buf = f.read()
    bits = frame_bits(buf, codec)
    assert len(bits) == n, (len(bits), n, out)
    res = {"bits": bits, "total_bits": int(bits.sum())}
    if measure:
        if src is None:
            src = _read_frames(gop_path, n)
        p, pyuv = _psnr(src[:n], decode(out, n))
        res.update(psnr=p, psnr_yuv=pyuv, mean_psnr=float(p.mean()))
    return res


def encode_cqp(gop_path, qp, codec=None, n=C.GOP, measure=True, src=None):
    """The encoder's own constant-QP mode (--qp): P frames at qp, the IDR frame lower by the default ipratio.
    This defines the budgets and the scoring curve ("constant QP" in every report)."""
    codec = codec or C.CODEC
    d = tempfile.mkdtemp(dir=_tmpdir())
    try:
        out = os.path.join(d, "out." + ("hevc" if codec == "x265" else "264"))
        _run(_cmd(codec, gop_path, n, out, [*FORCED_ARGS[codec], "--qp", str(int(qp))]))
        return _measure(out, gop_path, n, codec, measure, src)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def encode_own_rc(gop_path, target_bits, mode="abr", aq=False, codec=None, n=C.GOP, src=None):
    """The encoder's own rate control on the same per-GOP budget.

    mode: 'abr' (single pass, average bitrate), '2pass' (two-pass ABR), 'abr_vbv' (ABR with a VBV buffer of one GOP).
    aq:   False = AQ and cutree/mb-tree off (same tools as the forced-QP encodes); True = the encoder's defaults.
    """
    codec = codec or C.CODEC
    kbps = max(1, round(target_bits * FPS / n / 1000.0))   # both encoders take integer kbps (<1% at our budgets)
    d = tempfile.mkdtemp(dir=_tmpdir())
    try:
        out = os.path.join(d, "out." + ("hevc" if codec == "x265" else "264"))
        tools = OWN_AQ_ARGS[codec] if aq else FORCED_ARGS[codec]
        rc = ["--bitrate", str(kbps)]
        if mode == "abr_vbv":
            rc += ["--vbv-maxrate", str(kbps), "--vbv-bufsize", str(max(1, round(kbps * n / FPS)))]
        if mode == "2pass":
            stats = os.path.join(d, "stats.log")
            for p in (1, 2):
                _run(_cmd(codec, gop_path, n, out, [*tools, *rc, "--pass", str(p), "--stats", stats]))
        else:
            _run(_cmd(codec, gop_path, n, out, [*tools, *rc]))
        return _measure(out, gop_path, n, codec, True, src)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def first_pass(gop_path, qp=30, codec=None):
    """Cheap complexity features: an ultrafast constant-QP encode's per-frame bits (no decode)."""
    codec = codec or C.CODEC
    d = tempfile.mkdtemp(dir=_tmpdir())
    try:
        out = os.path.join(d, "fp")
        extra = [*FORCED_ARGS[codec], "--qp", str(qp)]
        cmd = _cmd(codec, gop_path, C.GOP, out, extra)
        i = cmd.index("--preset")
        cmd[i + 1] = "ultrafast"
        _run(cmd)
        with open(out, "rb") as f:
            return frame_bits(f.read(), codec)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def versions():
    v = {}
    for exe, args in (("x265", ["--version"]), ("x264", ["--version"]), ("ffmpeg", ["-version"])):
        try:
            r = subprocess.run([exe, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
            v[exe] = r.stdout.decode(errors="replace").strip().splitlines()[0]
        except Exception as e:  # noqa: BLE001
            v[exe] = f"unavailable ({e})"
    return v
