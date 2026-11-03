"""Parity test: env encodes vs the x264 CLI (CARC module x264/20250608).

For each clip/GOP and QP sequence:
  1. run an episode through RateControlEnv and keep its bitstream and recon;
  2. encode the same 30 frames with the x264 CLI (frozen flags + qp=31
     ipratio=10 pbratio=10 force-cfr, --qpfile with the same per-frame QPs:
     frame 0 as I, the rest as P), reading the original y4m with --seek;
  3. compare the full bitstream NAL by NAL, the per-frame slice sizes, and
     the ffmpeg-decoded frames (and the env's own recon) byte for byte.

Cases: constant 26, constant 11, constant 51, random across 11..51, and a
shield case (dqp=-1 actions from base QP 31 with the constant-QP-31 spend as
budget, so the shield fires part-way; the QPs the env actually used, forced
ones included, are given to the CLI).

    source env.sh && make
    python3 tests/test_parity.py --clip /path/a.y4m:GOP [--clip ...] [--workdir DIR] [--keep]

Work files go to --workdir (default /scratch1/$USER/tmp/ee599_parity), never
the repo, and are deleted unless --keep or a case fails.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from x264env.env import GOP_LEN, QP_MAX, QP_MIN, RateControlEnv  # noqa: E402

# Frozen settings as x264 CLI flags (keep in sync with encoder_shim.c / ENCODER_SETTINGS.md).
X264_FLAGS = ["--preset", "medium", "--bframes", "0", "--keyint", "30", "--min-keyint", "30",
              "--scenecut", "0", "--aq-mode", "0", "--no-mbtree", "--no-psy", "--threads", "1",
              "--qp", "31", "--ipratio", "10", "--pbratio", "10", "--force-cfr"]
NAL_NAMES = {1: "slice", 5: "IDR slice", 6: "SEI", 7: "SPS", 8: "PPS", 9: "AUD"}


def split_nals(data: bytes) -> list[tuple[int, bytes]]:
    """Annex-B -> [(nal_type, bytes incl. start code)]. A 4-byte start code's
    leading zero is counted with the NAL that follows, as x264 does."""
    starts, i = [], 0
    while (j := data.find(b"\x00\x00\x01", i)) >= 0:
        starts.append(j - 1 if j > 0 and data[j - 1] == 0 else j)
        i = j + 3
    nals = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(data)
        hdr = data.index(b"\x00\x00\x01", s) + 3
        nals.append((data[hdr] & 0x1F, data[s:e]))
    return nals


def sei_text(nal: bytes) -> str:
    """Printable part of x264's user-data SEI (version + options string)."""
    txt = "".join(chr(b) if 32 <= b < 127 else " " for b in nal)
    k = txt.find("x264 - core")
    return txt[k:].split("  ")[0] if k >= 0 else txt


def decode(path: Path, out: Path) -> bytes:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
                    "-f", "rawvideo", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out.read_bytes()


SHIELD_ACTION = 3   # dqp = -1 every frame: QP walks down until the shield steps in


def run_env(clip: str, gop: int, qps=None, shield_budget=None):
    """Episode via the env. qps: explicit per-frame QPs (step_qp). shield_budget:
    instead use dqp=-1 actions (step) with the shield on and this budget."""
    if shield_budget is None:
        env = RateControlEnv(clip=clip, gop=gop, budget=10**9, shield=False)
        env.reset()
        infos = [env.step_qp(q)[4] for q in qps]
    else:
        env = RateControlEnv(clip=clip, gop=gop, budget=shield_budget, base_qp=31, dqp_mode="prev")
        env.reset()
        infos = [env.step(SHIELD_ACTION)[4] for _ in range(GOP_LEN)]
    bs, recon = bytes(env.episode_bitstream), bytes(env.episode_recon)
    env.close()
    return infos, bs, recon


def run_cli(clip: str, gop: int, qps: list[int], work: Path, tag: str) -> Path:
    # The CLI numbers qpfile lines by ABSOLUTE input frame (it adds --seek), so
    # GOP g's frames are g*30 .. g*30+29. Lines that don't match are ignored
    # silently and x264 falls back to its default CQP QPs.
    first = gop * GOP_LEN
    qpfile = work / f"{tag}.qpfile"
    qpfile.write_text("".join(f"{first + i} {'I' if i == 0 else 'P'} {q}\n"
                              for i, q in enumerate(qps)))
    out = work / f"{tag}_cli.264"
    cmd = ["x264", *X264_FLAGS, "--qpfile", str(qpfile), "--seek", str(gop * GOP_LEN),
           "--frames", str(GOP_LEN), "--quiet", "-o", str(out), clip]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out


def compare(name: str, clip: str, gop: int, infos, env_bs: bytes, env_recon: bytes,
            work: Path, tag: str) -> bool:
    qps = [i["qp"] for i in infos]
    cli_path = run_cli(clip, gop, qps, work, tag)
    cli_bs = cli_path.read_bytes()
    env_path = work / f"{tag}_env.264"
    env_path.write_bytes(env_bs)
    problems, notes = [], []

    # 1. full bitstream, NAL by NAL
    en, cn = split_nals(env_bs), split_nals(cli_bs)
    if env_bs == cli_bs:
        notes.append(f"bitstream identical ({len(env_bs)} bytes)")
    elif [t for t, _ in en] != [t for t, _ in cn]:
        problems.append(f"NAL sequence differs: env {[t for t, _ in en][:8]}... "
                        f"cli {[t for t, _ in cn][:8]}...")
    else:
        diff = [(k, t) for k, ((t, a), (_, b)) in enumerate(zip(en, cn)) if a != b]
        kinds = sorted({NAL_NAMES.get(t, str(t)) for _, t in diff})
        if kinds == ["SEI"]:
            k = diff[0][0]
            ea, ca = sei_text(en[k][1]).split(), sei_text(cn[k][1]).split()
            only_env = [w for w in ea if w not in ca]
            only_cli = [w for w in ca if w not in ea]
            notes.append(f"bitstream differs ONLY in the x264 options SEI: env {only_env} "
                         f"vs cli {only_cli}")
        else:
            problems.append(f"bitstream differs in {kinds} NALs ({len(diff)} NALs)")

    # 2. per-frame slice sizes
    cli_slices = [len(b) * 8 for t, b in cn if t in (1, 5)]
    env_slices = [i["slice_bits"] for i in infos]
    if cli_slices != env_slices:
        bad = [k for k, (a, b) in enumerate(zip(env_slices, cli_slices)) if a != b]
        problems.append(f"slice bits differ on {len(bad)} frames (first: frame {bad[:1]}); "
                        f"counts env {len(env_slices)} cli {len(cli_slices)}")
    else:
        notes.append(f"slice bits identical on all {len(env_slices)} frames "
                     f"(total {sum(env_slices)})")

    # 3. decoded frames
    dec_env = decode(env_path, work / f"{tag}_env.yuv")
    dec_cli = decode(cli_path, work / f"{tag}_cli.yuv")
    if dec_env != dec_cli:
        problems.append("decoded frames differ")
    elif dec_env != env_recon:
        problems.append("decoded frames match each other but not the env recon")
    else:
        notes.append(f"decoded frames identical to each other and to env recon "
                     f"({len(dec_env) * GOP_LEN // len(env_recon)} frames)")

    ok = not problems
    qdesc = f"QPs {min(qps)}..{max(qps)}" if len(set(qps)) > 1 else f"QP {qps[0]}"
    print(f"[{'PASS' if ok else 'FAIL'}] {Path(clip).stem} gop {gop} | {name} ({qdesc})")
    for n in notes:
        print(f"       - {n}")
    for p in problems:
        print(f"       ! {p}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", action="append", required=True, metavar="PATH:GOP",
                    help="y4m clip and GOP index; repeat for more clips")
    ap.add_argument("--workdir", default=f"/scratch1/{os.environ.get('USER', 'user')}/tmp/ee599_parity")
    ap.add_argument("--keep", action="store_true", help="keep work files")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    results = []
    for spec in args.clip:
        clip, _, g = spec.rpartition(":")
        clip, gop = (clip, int(g)) if clip else (spec, 0)
        tag0 = f"{Path(clip).stem}_g{gop}"

        cases = [("constant 26", [26] * GOP_LEN), ("constant 11", [QP_MIN] * GOP_LEN),
                 ("constant 51", [QP_MAX] * GOP_LEN),
                 (f"random 11..51 (seed {args.seed})",
                  rng.integers(QP_MIN, QP_MAX + 1, GOP_LEN).tolist())]
        for name, qps in cases:
            infos, bs, recon = run_env(clip, gop, qps=qps)
            results.append(compare(name, clip, gop, infos, bs, recon, work,
                                   f"{tag0}_{name.split()[0]}{name.split()[1]}"))

        # shield case: budget = what constant QP 31 spends on this GOP; with
        # dqp=-1 every frame the spend outgrows it and the shield must fire
        base_infos, _, _ = run_env(clip, gop, qps=[31] * GOP_LEN)
        budget = sum(i["slice_bits"] for i in base_infos)
        infos, bs, recon = run_env(clip, gop, shield_budget=budget)
        fired = sum(i["shield_fired"] for i in infos)
        ok = compare(f"shield, budget {budget} (fired on {fired} frames)", clip, gop,
                     infos, bs, recon, work, f"{tag0}_shield")
        if fired == 0:
            print("       ! shield never fired: case did not test what it should")
            ok = False
        results.append(ok)

    n_ok = sum(results)
    print(f"\n{n_ok}/{len(results)} cases passed")
    if n_ok == len(results) and not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    else:
        print(f"work files kept in {work}")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
