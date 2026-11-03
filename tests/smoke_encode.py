"""Smoke test: encode N frames of a y4m at constant QP, print bits and PSNR per frame.

    source env.sh && make
    python3 tests/smoke_encode.py /path/to/clip.y4m --qp 26 --frames 30 [--save out.264]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from x264env import Encoder, psnr_i420, read_y4m  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("y4m")
    ap.add_argument("--qp", type=int, default=26)
    ap.add_argument("--frames", type=int, default=30)
    ap.add_argument("--save", help="optional path for the .264 bitstream (keep it out of the repo)")
    args = ap.parse_args()

    w, h, fn, fd, frames = read_y4m(args.y4m)
    src = {}
    rows = []
    bitstream = bytearray()
    with Encoder(w, h, fn, fd) as enc:
        print(f"x264 build {enc.api_version}, {w}x{h} @ {fn}/{fd} fps, QP {args.qp} "
              f"(honoured range {enc.qp_range[0]}..{enc.qp_range[1]})")

        def record(out):
            if out is None:
                return
            p = psnr_i420(src.pop(out.pts), out.recon, w, h)
            rows.append((out, p))
            bitstream.extend(out.bitstream)

        for i, frame in enumerate(frames):
            if i >= args.frames:
                break
            src[i] = frame
            record(enc.encode(frame, args.qp))
            if enc.delayed_frames:
                print(f"note: {enc.delayed_frames} frame(s) buffered after input {i}")
        for out in enc.flush():
            record(out)

    print(f"{'frame':>5} {'type':>4} {'qp':>3} {'bits':>8} {'slice':>8} {'header':>7} "
          f"{'PSNR-Y':>7} {'PSNR-YUV':>8}")
    for out, p in rows:
        print(f"{out.pts:5d} {out.frame_type:>4} {out.qp:3d} {out.bits:8d} "
              f"{out.slice_bits:8d} {out.header_bits:7d} {p['y']:7.2f} {p['yuv']:8.2f}")
    total = sum(o.bits for o, _ in rows)
    sl = sum(o.slice_bits for o, _ in rows)
    print(f"total {len(rows)} frames, {total} bits ({sl} slice + {total - sl} header), "
          f"mean PSNR-Y {sum(p['y'] for _, p in rows) / len(rows):.2f} dB")

    if args.save:
        Path(args.save).write_bytes(bitstream)
        print(f"wrote {args.save}")
    if src:  # every submitted frame must come back out
        print(f"FAIL: {len(src)} frame(s) never returned by the encoder")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
