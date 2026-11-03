# Encoder settings (frozen)

Applied by `encoder_shim.c` (`FROZEN_OPTS`) via `x264_param_parse`, on top of
`--preset medium`. Library: CARC module `x264/20250608` (API build 165), loaded
by `env.sh`. Keep this file and `FROZEN_OPTS` in sync.

| Setting | Value | Why |
|---|---|---|
| preset | medium | Agreed baseline. |
| bframes | 0 | One frame in, one frame out; no reordering. |
| keyint / min-keyint | 30 / 30 | One IDR per 30-frame GOP = one RL episode. |
| scenecut | 0 | GOP structure must not depend on content. |
| aq-mode | 0 | Uniform QP inside a frame, so the chosen QP is the frame's QP. |
| mbtree | 0 | No lookahead-driven QP changes. |
| psy | 0 | Optimise for PSNR, the reward metric. |
| threads | 1 | Deterministic output; light on shared nodes. |
| format | 8-bit 4:2:0, 320x180 | Set as struct fields in the shim (width, height, `X264_CSP_I420`, bitdepth 8). |
| rate control | CQP (`qp=31`) | Every frame's QP is forced through `pic.i_qpplus1`. |
| ipratio / pbratio | 10 / 10 | See "QP range" below. |
| force-cfr | 1 | See "Zero delay" below. |

## QP range: `qp=31`, `ipratio=10`, `pbratio=10`

In CQP mode x264 ignores `qpmin`/`qpmax`. It replaces them with
`[qp - 6*log2(ipratio), qp + 6*log2(pbratio)]` and **silently clamps** forced
per-frame QPs into that window. With x264's default `qp=26`, `ipratio=1.4` and
`pbratio=1.3`, the window was only **[23, 29]**. x264 caps both ratios at 10
(±19.9 QP), so `qp=31` gives the widest useful window: **[11, 51]**.
The ratios have no other effect here: there are no B-frames, and no QP is
left to x264.

`Encoder.qp_range` reports the window read back from x264 after opening.
`encode()` raises `ValueError` for a QP outside it, and the C shim also
returns error -3.

Verified (2026-11-03, testsrc 320x180):
- Every QP from 11 to 51 is honoured exactly (x264's per-frame debug log).
  QPs 10 and 52 are rejected.
- At constant QP 26, the old window (qp=26) and the new one give identical
  reconstructions. Each slice is **exactly 1 byte larger** with the new
  settings, on every frame. Cause: the PPS initial QP is now 31, so
  `slice_qp_delta` is coded as -5 (7 bits) instead of 0 (1 bit), which rounds
  up to 1 byte at CABAC alignment. The cost depends on |QP - 31|: zero at
  QP 31, and at most about 10 bits per frame.

## Zero delay: `force-cfr=1`

In its default variable-frame-rate input mode, x264 keeps each frame until
the next one arrives, to learn its duration, so `encode()` would return frame
t-1. The agent needs frame t's bits before it picks QP t+1. `force-cfr`
removes the delay. Only the SPS timing flag (`fixed_frame_rate_flag`)
changes; slice data is byte-identical.

## Bits per frame

`EncodedFrame` reports `bits = slice_bits + header_bits`. Both include Annex-B
start codes.
- `slice_bits`: the coded picture.
- `header_bits`: SPS + PPS + SEI. SPS and PPS are repeated on every IDR. The
  SEI on the first frame is x264's version-and-options text, about 4.4 kbit.
  At QP 26, frame 0 is 23,136 bits: 18,464 slice + 4,672 header.

Decide per experiment which of these counts against the GOP budget.

## Recon

The shim returns x264's reconstruction converted from NV12 to I420. It is
byte-identical to ffmpeg's decode of the shim's bitstream.
