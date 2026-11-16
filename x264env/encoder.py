"""ctypes wrapper around build/libx264shim.so (see encoder_shim.c).

Frames are contiguous 8-bit I420 ``bytes``: Y (w*h), U, V (w/2*h/2 each).
No third-party dependencies (numpy is not in CARC's python/3.12.12 module).
"""
from __future__ import annotations

import ctypes as C
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_LIB = _REPO / "build" / "libx264shim.so"

# X264_TYPE_* values from x264.h (build 165)
FRAME_TYPES = {1: "IDR", 2: "I", 3: "P", 4: "BREF", 5: "B", 6: "KEYFRAME"}


def _load(path: str | os.PathLike | None = None) -> C.CDLL:
    lib = C.CDLL(str(path or os.environ.get("X264SHIM_LIB", _DEFAULT_LIB)))
    u8p, ip, llp = C.POINTER(C.c_uint8), C.POINTER(C.c_int), C.POINTER(C.c_longlong)
    lib.shim_api_version.restype = C.c_int
    lib.shim_open.argtypes = [C.c_int] * 7
    lib.shim_open.restype = C.c_void_p
    lib.shim_frame_size.argtypes = [C.c_void_p]
    lib.shim_frame_size.restype = C.c_int
    lib.shim_delayed_frames.argtypes = [C.c_void_p]
    lib.shim_delayed_frames.restype = C.c_int
    lib.shim_qp_range.argtypes = [C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_int)]
    lib.shim_qp_range.restype = None
    lib.shim_encode.argtypes = [C.c_void_p, C.c_char_p, C.c_int,
                                u8p, C.c_int, ip, ip, u8p, ip, llp]
    lib.shim_encode.restype = C.c_int
    lib.shim_flush.argtypes = [C.c_void_p, u8p, C.c_int, ip, ip, u8p, ip, llp]
    lib.shim_flush.restype = C.c_int
    lib.shim_close.argtypes = [C.c_void_p]
    lib.shim_close.restype = None
    return lib


@dataclass
class EncodedFrame:
    pts: int            # index of the input frame this output belongs to
    qp: int             # QP used for that frame (always honoured exactly)
    bits: int           # all NALs for this frame = slice_bits + header_bits
    slice_bits: int     # coded picture data (slice NALs)
    header_bits: int    # SPS/PPS/SEI; nonzero only on the first frame / IDRs
    frame_type: str     # "IDR", "P", ...
    recon: bytes        # reconstructed frame, contiguous I420
    bitstream: bytes    # Annex-B bytes for this frame


class Encoder:
    """One x264 encoder with the project's frozen settings.

    ``encode(frame, qp)`` returns the EncodedFrame that came out of x264 for
    this call, or None if x264 buffered it. The shim sets force-cfr, so x264
    has zero frame delay: each call returns the frame just submitted.
    """

    LOG_NONE, LOG_ERROR, LOG_WARNING, LOG_INFO, LOG_DEBUG = -1, 0, 1, 2, 3

    def __init__(self, width: int, height: int, fps_num: int = 30, fps_den: int = 1,
                 log_level: int = LOG_ERROR, lib_path: str | None = None,
                 sar: tuple[int, int] = (0, 0)):
        """sar: sample aspect ratio for the SPS VUI, (0, 0) = not written. Pass
        the y4m "A" value (see y4m_header) to match the x264 CLI's stream."""
        self._lib = _load(lib_path)
        self._h = self._lib.shim_open(width, height, fps_num, fps_den, sar[0], sar[1], log_level)
        if not self._h:
            raise RuntimeError("shim_open failed (see stderr)")
        self.width, self.height = width, height
        self.frame_size = self._lib.shim_frame_size(self._h)
        # Generous output cap: a raw frame plus headroom for headers.
        self._bs_cap = self.frame_size * 2 + 4096
        self._bs = (C.c_uint8 * self._bs_cap)()
        self._recon = (C.c_uint8 * self.frame_size)()
        self._qp_by_pts: dict[int, int] = {}
        self._next_pts = 0
        lo, hi = C.c_int(), C.c_int()
        self._lib.shim_qp_range(self._h, C.byref(lo), C.byref(hi))
        # x264 silently clamps forced QPs to this range; encode() refuses
        # anything outside it rather than mislabel the frame.
        self.qp_range = (lo.value, hi.value)

    @property
    def api_version(self) -> int:
        return self._lib.shim_api_version()

    @property
    def delayed_frames(self) -> int:
        self._check_open()
        return self._lib.shim_delayed_frames(self._h)

    def _check_open(self) -> None:
        if not self._h:
            raise RuntimeError("encoder is closed")

    def _result(self, rc: int, nbytes: C.c_int, nslice: C.c_int, ftype: C.c_int,
                pts: C.c_longlong) -> EncodedFrame | None:
        if rc < 0:
            raise RuntimeError(f"x264 shim error {rc}")
        if rc == 0:
            return None
        n, ns = nbytes.value, nslice.value
        return EncodedFrame(
            pts=pts.value,
            qp=self._qp_by_pts.pop(pts.value, -1),
            bits=8 * n,
            slice_bits=8 * ns,
            header_bits=8 * (n - ns),
            frame_type=FRAME_TYPES.get(ftype.value, str(ftype.value)),
            recon=bytes(self._recon),
            bitstream=bytes(self._bs[:n]),
        )

    def encode(self, frame: bytes, qp: int) -> EncodedFrame | None:
        self._check_open()
        if len(frame) != self.frame_size:
            raise ValueError(f"frame is {len(frame)} bytes, expected {self.frame_size}")
        lo, hi = self.qp_range
        if not lo <= qp <= hi:
            raise ValueError(f"qp {qp} outside the range x264 honours here [{lo}, {hi}]; "
                             "it would be silently clamped")
        self._qp_by_pts[self._next_pts] = qp
        self._next_pts += 1
        nbytes, nslice, ftype, pts = C.c_int(), C.c_int(), C.c_int(), C.c_longlong()
        rc = self._lib.shim_encode(self._h, frame, qp, self._bs, self._bs_cap,
                                   C.byref(nbytes), C.byref(nslice), self._recon,
                                   C.byref(ftype), C.byref(pts))
        return self._result(rc, nbytes, nslice, ftype, pts)

    def flush(self) -> Iterator[EncodedFrame]:
        """Yield any frames x264 is still holding."""
        self._check_open()
        while True:
            nbytes, nslice, ftype, pts = C.c_int(), C.c_int(), C.c_int(), C.c_longlong()
            rc = self._lib.shim_flush(self._h, self._bs, self._bs_cap, C.byref(nbytes),
                                      C.byref(nslice), self._recon, C.byref(ftype),
                                      C.byref(pts))
            out = self._result(rc, nbytes, nslice, ftype, pts)
            if out is None:
                return
            yield out

    def close(self) -> None:
        if self._h:
            self._lib.shim_close(self._h)
            self._h = None

    def __enter__(self) -> "Encoder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def read_y4m(path: str | os.PathLike) -> tuple[int, int, int, int, Iterator[bytes]]:
    """Return (width, height, fps_num, fps_den, frame_iterator) for an 8-bit 4:2:0 y4m."""
    f = open(path, "rb")
    header = f.readline().split()
    if not header or header[0] != b"YUV4MPEG2":
        f.close()
        raise ValueError(f"{path}: not a YUV4MPEG2 file")
    w = h = 0
    fps_num, fps_den, csp = 30, 1, b"420"
    for tok in header[1:]:
        key, val = tok[:1], tok[1:]
        if key == b"W":
            w = int(val)
        elif key == b"H":
            h = int(val)
        elif key == b"F":
            fps_num, fps_den = (int(x) for x in val.split(b":"))
        elif key == b"C":
            csp = val
    if not csp.startswith(b"420"):
        f.close()
        raise ValueError(f"{path}: colorspace C{csp.decode()} is not 8-bit 4:2:0")
    size = w * h * 3 // 2

    def frames() -> Iterator[bytes]:
        with f:
            while True:
                line = f.readline()
                if not line:
                    return
                if not line.startswith(b"FRAME"):
                    raise ValueError(f"{path}: bad frame marker {line[:20]!r}")
                data = f.read(size)
                if len(data) != size:
                    raise ValueError(f"{path}: truncated frame")
                yield data

    return w, h, fps_num, fps_den, frames()


def y4m_header(path: str | os.PathLike) -> dict:
    """Header fields of a y4m: width, height, fps (num, den), sar (w, h; (0, 0)
    if absent or unknown) and the raw token list."""
    with open(path, "rb") as f:
        toks = f.readline().split()
    if not toks or toks[0] != b"YUV4MPEG2":
        raise ValueError(f"{path}: not a YUV4MPEG2 file")
    out = {"width": 0, "height": 0, "fps": (30, 1), "sar": (0, 0),
           "tokens": [t.decode() for t in toks[1:]]}
    for tok in toks[1:]:
        key, val = tok[:1], tok[1:]
        if key == b"W":
            out["width"] = int(val)
        elif key == b"H":
            out["height"] = int(val)
        elif key == b"F":
            out["fps"] = tuple(int(x) for x in val.split(b":"))
        elif key == b"A":
            out["sar"] = tuple(int(x) for x in val.split(b":"))
    return out


def psnr_i420(ref: bytes, rec: bytes, width: int, height: int) -> dict[str, float]:
    """Per-plane and combined (6:1:1 weighted) PSNR in dB for 8-bit I420 frames."""
    ys = width * height
    cs = ys // 4
    planes = {"y": (0, ys), "u": (ys, ys + cs), "v": (ys + cs, ys + 2 * cs)}
    out: dict[str, float] = {}
    mse = {}
    for name, (a, b) in planes.items():
        sse = sum((x - y) * (x - y) for x, y in zip(ref[a:b], rec[a:b]))
        mse[name] = sse / (b - a)
        out[name] = _psnr(mse[name])
    out["yuv"] = _psnr((6 * mse["y"] + mse["u"] + mse["v"]) / 8)
    return out


def _psnr(mse: float) -> float:
    return float("inf") if mse == 0 else 10 * math.log10(255 * 255 / mse)
