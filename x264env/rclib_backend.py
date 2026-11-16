"""P1 shim as the encoder behind rclib's codec.encode (team pipeline, pavneet_pipeline/rclib/codec.py).

Switched on in rclib with RC_BACKEND=shim (default: the x264 CLI). x264 only, P1's frozen settings only (rclib's
lf / res / lfq arms), which is what the shim hard-codes.

rclib's env calls encode(gop, qps[:t+1]) once per step, i.e. it re-encodes the whole prefix 0..t with the CLI. Here
one encoder is kept open per episode and only the newest frame is encoded; a call whose QPs do not extend an open
encoder's QPs (new episode, other GOP, changed prefix) starts a fresh encoder and replays the prefix, so the result
never depends on the call pattern, only on (gop, qps).

Kept identical to rclib on purpose (the functions are rclib's own, passed in as `codec`):
  - bits: codec.frame_bits() on the shim's Annex-B bytes for that frame (NAL payload without start codes, slice NALs
    only under lf). The shim's own slice_bits count the start codes, so they are NOT used here.
  - PSNR: codec._psnr(src, recon) = per-frame 6:1:1 YUV PSNR, capped at 100, against codec._read_frames(gop), with
    the shim's reconstructed frames in place of an ffmpeg decode of the bitstream.
"""
from collections import OrderedDict

import numpy as np

from .encoder import Encoder

MAX_OPEN = 32   # open encoders kept per process (vectorised envs interleave several episodes)


class _Episode:
    def __init__(self, gop_path, w, h, frames):
        self.gop_path, self.frames = gop_path, frames
        self.enc = Encoder(w, h, 30, 1)          # rclib's CLI runs at --fps 30 on raw input, no SAR
        self.qps, self.bits, self.recon = [], [], []

    def extend(self, codec, q):
        t = len(self.qps)
        fr = self.enc.encode(self.frames[t].tobytes(), q)
        if fr is None or fr.qp != q or fr.frame_type != ("IDR" if t == 0 else "P"):
            raise RuntimeError(f"shim frame {t}: got {None if fr is None else (fr.qp, fr.frame_type)}, wanted qp {q}")
        b = codec.frame_bits(fr.bitstream, "x264")
        if len(b) != 1:
            raise RuntimeError(f"shim frame {t}: frame_bits found {len(b)} pictures")
        self.qps.append(q)
        self.bits.append(int(b[0]))
        self.recon.append(np.frombuffer(fr.recon, np.uint8))

    def close(self):
        self.enc.close()


_open = OrderedDict()   # id -> _Episode, oldest first


def _find(gop_path, qps):
    """Open episode on this GOP whose QPs are a prefix of `qps` (longest one), or None."""
    best = None
    for key, ep in _open.items():
        n = len(ep.qps)
        if ep.gop_path == gop_path and n <= len(qps) and ep.qps == qps[:n] and (best is None or n > len(best[1].qps)):
            best = (key, ep)
    return best


def encode(codec, gop_path, qps, measure=True, src=None):
    """Same contract as rclib codec.encode for x264 under lf settings: dict(bits, total_bits[, psnr, psnr_yuv,
    mean_psnr]) for frames 0..len(qps)-1. qps are already clipped by the caller."""
    C = codec.C
    qps = [int(q) for q in qps]
    n = len(qps)
    hit = _find(gop_path, qps)
    if hit is None:
        frames = codec._read_frames(gop_path, C.GOP)
        ep = _Episode(gop_path, C.W, C.H, frames)
        key = id(ep)
        _open[key] = ep
        while len(_open) > MAX_OPEN:
            _open.popitem(last=False)[1].close()
    else:
        key, ep = hit
        _open.move_to_end(key)
    for t in range(len(ep.qps), n):
        ep.extend(codec, qps[t])
    bits = np.asarray(ep.bits[:n], np.int64)
    res = {"bits": bits, "total_bits": int(bits.sum())}
    if measure:
        if src is None:
            src = ep.frames
        p, pyuv = codec._psnr(src[:n], np.stack(ep.recon[:n]))
        res.update(psnr=p, psnr_yuv=pyuv, mean_psnr=float(p.mean()))
    if n == C.GOP:          # episode finished: free the encoder
        _open.pop(key).close()
    return res
