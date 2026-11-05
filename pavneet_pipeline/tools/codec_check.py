"""Checks that the encoder harness measures what the study assumes. All lines must end in PASS.

  1. forced per-frame QPs are obeyed exactly (x265: its CSV QP column; x264: --verbose per-frame QP)
  2. bits counted from the bitstream match x265's own per-frame CSV bits (x265 only; x264 has no per-frame log)
  3. prefix property: encoding the first n frames gives the same per-frame bits as the first n of the full GOP
     (the Gym env relies on this: each step is one prefix encode)
  4. determinism: the same encode twice gives identical bits and PSNR
  5. PSNR: our Y-PSNR matches ffmpeg's psnr filter on the same decode
  6. constant-QP bits fall monotonically from QP 18 to 50
  7. the encoder's own rate control lands near the target (reported, not a pass/fail on accuracy)
usage: python tools/codec_check.py [gop .yuv file]   (default: frames 0-29 of the first clip in $RC_WORK/clips)
"""
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import codec, config as C, data  # noqa: E402

ok_all = True


def check(name, ok, detail=""):
    global ok_all
    ok_all &= bool(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")


def gop_file():
    if len(sys.argv) > 1:
        return sys.argv[1]
    clip = sorted(f for f in os.listdir(C.CLIPS) if f.endswith(".y4m"))[0]
    p = os.path.join(C.TMP, "codec_check_gop.yuv")
    data.read_frames(os.path.join(C.CLIPS, clip), 0, C.GOP).tofile(p)
    print(f"GOP: {clip} frames 0-29")
    return p


def x265_csv(p, qps):
    d = tempfile.mkdtemp(dir=C.TMP)
    qf, out, csv = f"{d}/qp.txt", f"{d}/o.hevc", f"{d}/f.csv"
    codec._qpfile(qf, qps)
    codec._run(codec._cmd("x265", p, len(qps), out, [*codec.FORCED_ARGS["x265"], "--qp", str(qps[0]), "--qpfile", qf,
                                                     "--csv", csv, "--csv-log-level", "1"]))
    lines = open(csv).read().strip().splitlines()
    hdr = [h.strip() for h in lines[0].split(",")]
    rows = [dict(zip(hdr, [v.strip() for v in ln.split(",")])) for ln in lines[1:]]
    rows = [r for r in rows if r.get("POC", "").isdigit()]   # drop x265's trailing summary lines
    rows.sort(key=lambda r: int(r["POC"]))
    return [float(r["QP"]) for r in rows], np.array([int(r["Bits"]) for r in rows]), out


def x264_verbose_qps(p, qps):
    d = tempfile.mkdtemp(dir=C.TMP)
    qf, out = f"{d}/qp.txt", f"{d}/o.264"
    codec._qpfile(qf, qps)
    cmd = codec._cmd("x264", p, len(qps), out, [*codec.FORCED_ARGS["x264"], *codec._carrier("x264", qps[0]),
                                                "--qpfile", qf, "--verbose"])
    cmd.remove("--quiet")
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    txt = r.stdout.decode(errors="replace")
    return [float(m) for m in re.findall(r"frame=\s*\d+\s+QP=([\d.]+)", txt)]


def main():
    print("versions:", codec.versions())
    p = gop_file()
    rng = np.random.default_rng(0)
    for cd in ("x265", "x264"):
        print(f"[{cd}]")
        qps = [int(30 + o + a) for o, a in zip(C.static_offsets(), rng.integers(-3, 4, C.GOP))]
        full = codec.encode(p, qps, codec=cd)
        # 1 (+2 for x265)
        if cd == "x265":
            got, csv_bits, _ = x265_csv(p, qps)
            check("forced QPs obeyed", got == [float(q) for q in qps], f"{got[:6]}... vs {qps[:6]}...")
            rel = np.abs(csv_bits - full["bits"]) / full["bits"]
            check("bitstream bits == CSV bits (P frames); I frame + parameter sets only",
                  np.array_equal(csv_bits[1:], full["bits"][1:]) and 0 <= full["bits"][0] - csv_bits[0] < 1200,
                  f"I-frame extra {full['bits'][0] - csv_bits[0]} bits (VPS/SPS/PPS)")
        else:
            got = x264_verbose_qps(p, qps)
            check("forced QPs obeyed", got == [float(q) for q in qps], f"{got[:6]}... vs {qps[:6]}...")
        # 3
        for n in (1, 7, 18):
            pre = codec.encode(p, qps[:n], codec=cd)
            check(f"prefix property n={n}", np.array_equal(pre["bits"], full["bits"][:n])
                  and np.allclose(pre["psnr"], full["psnr"][:n]))
        # 4
        again = codec.encode(p, qps, codec=cd)
        check("deterministic", np.array_equal(again["bits"], full["bits"]) and np.allclose(again["psnr"], full["psnr"]))
        # 5
        d = tempfile.mkdtemp(dir=C.TMP)
        bs = f"{d}/o.bin"
        codec._qpfile(f"{d}/q.txt", qps)
        codec._run(codec._cmd(cd, p, C.GOP, bs, [*codec.FORCED_ARGS[cd], *codec._carrier(cd, qps[0]),
                                                "--qpfile", f"{d}/q.txt"]))
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", bs, "-f", "rawvideo", "-pix_fmt", "yuv420p",
                        "-s", f"{C.W}x{C.H}", "-i", p, "-lavfi", f"[0:v]setpts=N/(30*TB)[a];[1:v]setpts=N/(30*TB)[b];[a][b]psnr=stats_file={d}/ps.txt", "-f", "null",
                        "-"], check=True)
        ff = [float(m) for m in re.findall(r"psnr_y:([\d.]+)", open(f"{d}/ps.txt").read())]
        ours = full["psnr_yuv"][:, 0]
        check("Y-PSNR matches ffmpeg", len(ff) == C.GOP and np.abs(np.array(ff) - ours).max() < 0.01,
              f"max diff {np.abs(np.array(ff) - ours).max() if len(ff) == C.GOP else 'n/a'}")
        # 6
        curve = [codec.encode_cqp(p, q, codec=cd, measure=False)["total_bits"] for q in range(18, 51, 4)]
        check("CQP bits monotone in QP", all(a > b for a, b in zip(curve, curve[1:])), f"{curve}")
        # 7
        cq = codec.encode_cqp(p, 30, codec=cd)
        check("own CQP: IDR frame below P frames (ipratio)", cq["bits"][0] > cq["bits"][1:].max())
        target = cq["total_bits"]
        for mode in ("abr", "2pass", "abr_vbv"):
            for aq in (False, True):
                r = codec.encode_own_rc(p, target, mode, aq=aq, codec=cd)
                print(f"  info  own RC {mode:8s} aq={aq!s:5s}: {r['total_bits'] / target - 1:+.1%} of target, "
                      f"PSNR {r['mean_psnr']:.2f}")
    print("ALL PASS" if ok_all else "SOME CHECKS FAILED")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
