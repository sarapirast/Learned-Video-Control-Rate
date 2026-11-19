"""D54: VMAF of the encoder rate-control rows (the rows D52 could not rescore: their decoded output was not stored).

Re-encodes exactly the encodes behind the paper's encoder rows, checks that every GOP's bits equal the stored run, and
scores the decoded frames with VMAF (vmaf_v0.6.1) at native 320x180 and upscaled to 1080p (as D49):
  stream  on-demand stream level (D50 luma run, rcwork_v1/<codec>/results_own_rc_stream_v1_luma/run.pkl):
          abr_vbv (ABR + VBV) and 2pass (non-causal two-pass), every stored test case
  live    live channel, fixed-ladder budget (D47 E2, results_buffer{,_trace}_ladder/real): the encoder's whole-stream
          ABR + VBV at f x the channel mean, f tuned on val exactly as tools/live_vs_encoder.py; test and test16
Nothing is retrained or retuned. The paired comparisons are made by tools/encoder_vmaf_report.py.

  RC_V1=1 RC_PRESET=medium RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 \
      python experiments/encoder_vmaf.py --shard i --nshards N [--limit K]
Output: $RC_WORK/results_enc_vmaf/<i>of<N>.pkl (--limit -> results_enc_vmaf_debug)
  {"rows": {item: {"gop_bits", "bits_match", "vmaf_native" [frames], "vmaf_1080" [frames]}}, "mismatch": int}
  item = ("stream", cfg, stream, q0, s) | ("live", tag, split, stream, q0, s)
"""
import argparse
import glob
import os
import pickle
import shutil
import sys
import tempfile
import time

import numpy as np

os.environ.setdefault("RC_V1", "1")
os.environ.setdefault("RC_OWN_LUMA", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import own_rc_stream as O, own_rc_stream_v1 as O1, stream_rl as S, vmaf_curves as VC  # noqa: E402
from rclib import bufenv as BE, codec, config as C, data  # noqa: E402

W = C.WORK
STREAM_CFGS = ("abr_vbv", "2pass")
LIVE = ("results_buffer_ladder", "results_buffer_trace_ladder")
E2_F = (0.6, 0.7, 0.8, 0.9, 1.0, 0.2, 0.3, 0.4, 0.5)


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def _real_rows(d, split):
    R = {}
    for p in sorted(glob.glob(os.path.join(d, "real", f"{split}_*of*.pkl"))):
        if "_il_ppo_rr" in p:
            continue
        for name, rows in pickle.load(open(p, "rb"))["rows"].items():
            R.setdefault(name, []).extend(rows)
    return R


def best_f(d):
    """E2's target fraction picked on val (same rule as tools/live_vs_encoder.py)."""
    V = _real_rows(d, "val")
    vm = {f: np.mean([r["score"] for r in V[f"enc_vbv_f{f:g}"]]) for f in E2_F if V.get(f"enc_vbv_f{f:g}")}
    return max(vm, key=vm.get)


def items():
    """Every encode to redo, with what is needed to redo it and the stored per-GOP bits to check against."""
    out = []
    run = pickle.load(open(os.path.join(W, "results_own_rc_stream_v1_luma", "run.pkl"), "rb"))
    for (st, q0, s), v in sorted(run.items()):
        for cfg in STREAM_CFGS:
            if not v[cfg].get("failed"):
                out.append((("stream", cfg, tuple(st), int(q0), float(s)),
                            {"B": float(v["B"]), "gop_bits": list(v[cfg]["gop_bits"])}))
    for tag in LIVE:
        d = os.path.join(W, tag)
        if not os.path.isdir(os.path.join(d, "real")):
            continue
        f = best_f(d)
        for split in ("test", "test16"):
            for r in _real_rows(d, split).get(f"enc_vbv_f{f:g}", []):
                out.append((("live", tag, split, tuple(r["stream"]), int(r["q0"]), float(r["s"])),
                            {"B": float(r["budget"]), "f": f, "gop_bits": list(r["gop_bits"])}))
    return out


def _args_live(B, f, n):
    """As experiments/buffer_real.stream_abr_vbv (E2)."""
    k = max(1, round(f * B / n * 30 / 1000))
    rc = ["--bitrate", str(k), "--fps", f"{k * 1000 * n}/{max(1, int(round(f * B)))}"]
    kb = max(1, round(k * BE.D_CAP / f))
    return [*codec.FORCED_ARGS[C.CODEC], *rc, "--vbv-maxrate", str(k), "--vbv-bufsize", str(kb), "--rc-lookahead", "30"]


def one(item, meta, infos, d):
    if item[0] == "stream":
        _, cfg, st, q0, s = item
        mode, tk, extra = O1.CONFIGS[cfg]
        args, two = O1._args(meta["B"], tk, extra), mode == "2pass"
    else:
        _, tag, split, st, q0, s = item
        args, two = _args_live(meta["B"], meta["f"], len(st) * C.GOP), False
    sub = {g: infos[g] for g in st}
    n = len(st) * C.GOP
    p, _ = O._stream(sub, st, d)
    out = os.path.join(d, "out." + ("hevc" if C.CODEC == "x265" else "264"))
    base = [*args, *(["--repeat-headers"] if C.CODEC == "x265" else [])]
    if two:
        stats = os.path.join(d, "stats.log")
        for k in (1, 2):
            codec._run(codec._cmd(C.CODEC, p, n, out, [*base, "--pass", str(k), "--stats", stats]))
    else:
        codec._run(codec._cmd(C.CODEC, p, n, out, base))
    with open(out, "rb") as fh:
        bits = codec.frame_bits(fh.read(), C.CODEC)
    assert len(bits) == n, (len(bits), n)
    gb = bits.reshape(-1, C.GOP).sum(1)
    match = bool(np.array_equal(np.round(gb), np.round(np.asarray(meta["gop_bits"], float))))
    dec = os.path.join(d, "dec.yuv")
    codec.decode(out, n).tofile(dec)
    r = {"gop_bits": gb.tolist(), "bits_match": match, "vmaf_native": VC.vmaf(p, dec, C.W, C.H, d)}
    ru, du = os.path.join(d, "ref_up.yuv"), os.path.join(d, "dec_up.yuv")
    VC.upscale(p, ru)
    VC.upscale(dec, du)
    r["vmaf_1080"] = VC.vmaf(ru, du, *VC.UP, d)
    for x in (ru, du, dec, p):
        os.remove(x)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=int(os.environ.get("RC_NSHARDS", 1)))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    assert C.V1 and os.access(VC.VMAF, os.X_OK)
    od = os.path.join(W, "results_enc_vmaf" + ("_debug" if a.limit else ""))
    os.makedirs(od, exist_ok=True)
    p = os.path.join(od, f"{a.shard}of{a.nshards}.pkl")
    if os.path.exists(p):
        log(f"{p}: done")
        return
    infos = S.load_infos()
    its = data.shard(items(), a.nshards, a.shard)
    if a.limit:   # debug: a few of each kind
        its = [x for x in its if x[0][0] == "stream"][:a.limit] + [x for x in its if x[0][0] == "live"][:a.limit]
    t0, R, bad = time.time(), {}, 0
    d = tempfile.mkdtemp(dir=codec._tmpdir())
    try:
        for j, (it, meta) in enumerate(its):
            R[it] = one(it, meta, infos, d)
            bad += int(not R[it]["bits_match"])
            if j % 10 == 0 or a.limit:
                log(f"shard {a.shard}: {j + 1}/{len(its)}, {(time.time() - t0) / 60:.1f} min; {it[:2]} "
                    f"VMAF {R[it]['vmaf_native'].mean():.1f} / {R[it]['vmaf_1080'].mean():.1f}; bits mismatch {bad}")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    pickle.dump({"rows": R, "mismatch": bad, "seconds": time.time() - t0}, open(p, "wb"))
    log(f"{p}: {len(R)} encodes, bits mismatch {bad}, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
