"""P2 week-2 baseline table (docs/p2-plan.md, "Week 2: baselines at scale") on data v1.

Every baseline uses P1's frozen encoder settings (scripts/rd_native.py flags, preset medium) and the leak-free
clip-level budgets (data/v1/320x180/budgets.csv, 4 levels), for x264 and x265. One row per (method, k, GOP, level)
in a results-row format. Score = % bits saved at equal PSNR vs the GOP's own constant-QP curve (linear extrapolation
beyond its ends, = Pavneet's metric), minus 2 x % over budget. Bits are slice bits; PSNR = mean over frames of YUV
6:1:1 PSNR.

Methods (causal = uses only what a single-pass encoder could know at lookahead k):
  cqp_best        best constant QP in hindsight: the lowest QP whose own constant-QP encode fits B. From the stored
                  curves (no encodes), all splits; saving 0 by construction. Also P3's search starting point.
  cqp_est         constant QP = round(base_qp_est_k) from budgets.csv (causal estimator, no feedback). Stored curves.
  abr_vbv         the encoder's own 1-pass ABR at the GOP's bitrate with VBV sized to one GOP
                  (--bitrate = --vbv-maxrate = B x fps / 30, --vbv-bufsize = B), --rc-lookahead k. Causal at k.
                  The k sweep is the non-learned lookahead curve.
  two_pass        2-pass ABR at the GOP's bitrate (first pass sees the whole GOP): non-causal reference.
  crf_best        the CRF (bisection, 7 encodes) that spends closest to B without exceeding it: hindsight reference.
  fixed_best      a fixed pattern (I at q-6, P frames ramping linearly from q-3 to q+3) with the lowest base q that
                  fits B (bisection on real encodes). NOT the pilot's STATIC (a step: P 1-9 at q-3, P 10-29 at q+3):
                  the ramp came from a wrong description. Reported as ramp_best; the STATIC versions are static_best /
                  static_causal from scripts/static_rd.py (rows_static_all.parquet, all splits).
  fixed_causal    the same ramp with q = round(base_qp_est_k) (causal estimator at k, no feedback); reported as
                  ramp_causal.
Forced per-frame QPs use P1's method (x264 --qp 31 --ipratio 10 --pbratio 10 --qpfile; x265 --qp 31 --qpfile).

  python scripts/baselines_v1.py --encoder x264 --split test --nshards 8     one shard (= array task id)
  python scripts/baselines_v1.py --encoder x264 --split val --limit 2 --tag smoke
  python scripts/baselines_v1.py --gather    -> results_v1/baselines_v1.parquet + results_v1/baselines_v1_table.md
"""
import argparse
import glob
import importlib.util
import os
import shutil
import subprocess
import tempfile
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
D = f"{ROOT}/data/v1/320x180"
OUT = f"{ROOT}/results_v1/baselines_v1"
KS = (0, 2, 5, 10, 29)
GOP = 30


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RN = _load("rd_native", f"{ROOT}/scripts/rd_native.py")
CR = _load("controller_real", f"{ROOT}/scripts/controller_real.py")
PATTERN = np.array([-6.0] + list(np.linspace(-3, 3, GOP - 1)))


def common(enc, yuv, fps, out, extra, preset="medium"):
    if enc == "x264":
        return ["x264", *RN.X264, "--input-res", "320x180", "--fps", fps, "--preset", preset, *extra,
                "--frames", str(GOP), "-o", out, yuv]
    return ["x265", "--input", yuv, "--input-res", "320x180", "--fps", fps, *RN.X265, "--preset", preset, *extra,
            "--frames", str(GOP), "-o", out]


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def bits_of(enc, out):
    sl, hd = RN.frame_bits(open(out, "rb").read(), enc)
    assert len(sl) == GOP, (enc, out, len(sl))
    return int(sl.sum()), int(hd.sum())


def measure(enc, out, src):
    my, mu, mv = RN.plane_mse(src, RN.decode(out, GOP, 320, 180), 320, 180)
    ps = (6 * RN.psnr(my) + RN.psnr(mu) + RN.psnr(mv)) / 8
    return float(ps.mean()), float(RN.psnr(my).mean())


def forced(enc, yuv, fps, out, qps, d):
    qf = os.path.join(d, "qp.txt")
    with open(qf, "w") as f:
        for i, q in enumerate(qps):
            f.write(f"{i} {'I' if i == 0 else 'P'} {int(q)}\n")
    extra = ["--qp", "31", "--ipratio", "10", "--pbratio", "10", "--qpfile", qf] if enc == "x264" else \
        ["--qp", "31", "--qpfile", qf]
    run(common(enc, yuv, fps, out, extra))


def pattern_qps(q):
    return [int(np.clip(round(q + o), 11, 51)) for o in PATTERN]


def bisect_fit(encode_at, lo, hi, B, iters, integer):
    """Smallest x in [lo, hi] (more bits at smaller x) whose encode fits B; returns (x, bits, hdr) of the best
    fitting candidate seen, or the highest x tried if none fits."""
    best, last = None, None
    for _ in range(iters):
        x = int(round((lo + hi) / 2)) if integer else (lo + hi) / 2
        b, h = encode_at(x)
        last = (x, b, h)
        if b <= B:
            best = (x, b, h) if best is None or x < best[0] else best
            hi = x - (1 if integer else 0)
        else:
            lo = x + (1 if integer else 0)
        if integer and lo > hi:
            break
    return best or last


def row(method, enc, g, level, k, B, bits, hdr, psnr, psnr_y, curve, causal, param=""):
    sav = CR.saving(bits, psnr, curve)
    over = 100 * max(0.0, bits / B - 1)
    return {"method": method, "encoder": enc, "split": g["split"], "clip_id": g["clip_id"], "gop": g["gop"],
            "label": g["label"], "level_q0": level, "k": k, "causal": causal, "param": str(param),
            "budget_bits": B, "bits": bits, "header_bits": hdr, "psnr_yuv": psnr, "psnr_y": psnr_y,
            "saving": sav, "over_pct": over, "over": bits > B, "score": sav - 2 * over}


def one_gop(args):
    enc, g, budgets, curve, tmp = args
    src = RN.read_frames(g["y4m"], g["start_frame"], GOP, 320, 180)
    d = tempfile.mkdtemp(dir=tmp)
    rows = []
    try:
        yuv = os.path.join(d, "in.yuv")
        src.tofile(yuv)
        out, keep = os.path.join(d, "o.bin"), os.path.join(d, "keep.bin")
        fps = g["fps"]
        for level, bd in budgets.items():
            B = bd["B"]
            kbps = B * eval(fps) / GOP / 1000.0                 # fps is a rational string like "30/1"
            rate, buf = str(max(1, round(kbps))), str(max(1, round(B / 1000)))   # encoders take whole kbit(/s)
            # 1-pass ABR + VBV over the lookahead grid (causal at k)
            for k in KS:
                run(common(enc, yuv, fps, out, ["--bitrate", rate, "--vbv-maxrate", rate,
                                                "--vbv-bufsize", buf, "--rc-lookahead", str(k)]))
                b, h = bits_of(enc, out)
                rows.append(row("abr_vbv", enc, g, level, k, B, b, h, *measure(enc, out, src), curve, True))
            # 2-pass ABR (non-causal reference)
            st = os.path.join(d, "2p.stats")
            run(common(enc, yuv, fps, out, ["--bitrate", rate, "--pass", "1", "--stats", st]))
            run(common(enc, yuv, fps, out, ["--bitrate", rate, "--pass", "2", "--stats", st]))
            b, h = bits_of(enc, out)
            rows.append(row("two_pass", enc, g, level, 29, B, b, h, *measure(enc, out, src), curve, False))

            # CRF closest to B without exceeding it (hindsight reference)
            def at_crf(c):
                run(common(enc, yuv, fps, out, ["--crf", f"{c:.3f}"]))
                r = bits_of(enc, out)
                if r[0] <= B:
                    shutil.copyfile(out, keep)
                return r
            c, b, h = bisect_fit(at_crf, 0.0, 51.0, B, 7, integer=False)
            fin = keep if (os.path.exists(keep) and b <= B) else out
            rows.append(row("crf_best", enc, g, level, 29, B, b, h, *measure(enc, fin, src), curve, False, f"{c:.2f}"))
            if os.path.exists(keep):
                os.remove(keep)

            # fixed pattern, hindsight-shifted base (reference)
            def at_q(q):
                forced(enc, yuv, fps, out, pattern_qps(q), d)
                r = bits_of(enc, out)
                if r[0] <= B:
                    shutil.copyfile(out, keep)
                return r
            q, b, h = bisect_fit(at_q, 12, 51, B, 8, integer=True)
            fin = keep if (os.path.exists(keep) and b <= B) else out
            rows.append(row("fixed_best", enc, g, level, 29, B, b, h, *measure(enc, fin, src), curve, False, q))
            if os.path.exists(keep):
                os.remove(keep)
            # fixed pattern with the causal estimator's base QP at each k
            for k in KS:
                qk = int(round(bd[f"est{k}"]))
                forced(enc, yuv, fps, out, pattern_qps(qk), d)
                b, h = bits_of(enc, out)
                rows.append(row("fixed_causal", enc, g, level, k, B, b, h, *measure(enc, out, src), curve, True, qk))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return rows


def curves_for(enc):
    rd = pd.read_parquet(f"{D}/rd/rd_native.parquet").query("encoder == @enc")
    return rd, {k: {"bits": v.slice_bits.to_numpy(float), "psnr": v.psnr_yuv_mean_frames.to_numpy(float)}
                for k, v in rd.groupby(["clip_id", "gop"])}


def offline_rows(enc):
    """cqp_best (all splits) and cqp_est (val/test) from the stored constant-QP curves: no encodes."""
    rd, cur = curves_for(enc)
    rdi = rd.set_index(["clip_id", "gop", "qp"])
    bud = pd.read_csv(f"{D}/budgets.csv").query("encoder == @enc")
    out = []
    for r in bud.itertuples():
        g = {"split": r.split, "clip_id": r.clip_id, "gop": r.gop, "label": r.label}
        c = rd[(rd.clip_id == r.clip_id) & (rd.gop == r.gop)].sort_values("qp") if False else None
        qs = np.arange(18, 51)
        bits = np.array([rdi.loc[(r.clip_id, r.gop, q), "slice_bits"] for q in qs])
        ok = np.flatnonzero(bits <= r.budget_bits)
        q = int(qs[ok[0]]) if len(ok) else 50
        x = rdi.loc[(r.clip_id, r.gop, q)]
        out.append(row("cqp_best", enc, g, r.level_q0, 29, r.budget_bits, int(x.slice_bits), int(x.header_bits),
                       float(x.psnr_yuv_mean_frames), float(x.psnr_y_mean_frames), cur[(r.clip_id, r.gop)], False, q))
        if r.split in ("val", "test"):
            for k in KS:
                qk = int(np.clip(round(getattr(r, f"base_qp_est_k{k}")), 18, 50))
                x = rdi.loc[(r.clip_id, r.gop, qk)]
                out.append(row("cqp_est", enc, g, r.level_q0, k, r.budget_bits, int(x.slice_bits),
                               int(x.header_bits), float(x.psnr_yuv_mean_frames), float(x.psnr_y_mean_frames),
                               cur[(r.clip_id, r.gop)], True, qk))
    return out


def gather():
    parts = [pd.read_parquet(p) for p in sorted(glob.glob(f"{OUT}/rows_*.parquet"))]
    off = [pd.DataFrame(offline_rows(e)) for e in ("x264", "x265")]
    df = pd.concat(parts + off, ignore_index=True)
    df["method"] = df.method.replace({"fixed_best": "ramp_best", "fixed_causal": "ramp_causal"})
    # the P2 online controller (v1, scripts/controller_real.py, tag final) in the same format
    ctl = glob.glob(f"{ROOT}/results_v1/controller_real/final_*.parquet")
    if ctl:
        c = pd.concat([pd.read_parquet(p) for p in ctl]).merge(
            pd.read_csv(f"{D}/gops.csv")[["clip_id", "gop", "split", "label"]], on=["clip_id", "gop"])
        c = c.assign(method="online_controller_v1", causal=True, param=c.setting, header_bits=np.nan, psnr_y=np.nan)
        df = pd.concat([df, c[[x for x in df.columns if x in c.columns]]], ignore_index=True)
    df.to_parquet(f"{ROOT}/results_v1/baselines_v1.parquet", index=False)
    df["cls"] = np.where(df.label.isin(["cut", "gradual"]), "cut/gradual", "stable")
    order = ["cqp_best", "crf_best", "two_pass", "static_best", "ramp_best", "abr_vbv", "static_causal",
             "ramp_causal", "cqp_est", "online_controller_v1"]
    L = ["# Week-2 baseline table (data v1, leak-free budgets, P1's encoder settings)", "",
         "Generated by `scripts/baselines_v1.py --gather` from `results_v1/baselines_v1.parquet` (one row per method, "
         "k, GOP, budget level). Score = % bits saved at equal PSNR vs the GOP's own constant-QP curve - 2 x % over "
         "budget (0 = best constant QP in hindsight). Methods are defined in the script's docstring; non-causal "
         "methods are references (k shown as 29 = whole GOP).", ""]
    for sp in ("test", "val"):
        t = df[df.split == sp]
        a = t.groupby(["method", "causal", "k", "encoder"]).agg(score=("score", "mean"), saving=("saving", "mean"),
                                                             pct_over=("over", lambda s: 100 * s.mean()),
                                                             mean_over=("over_pct", "mean")).reset_index()
        a["method"] = pd.Categorical(a.method, order + sorted(set(a.method) - set(order)))
        piv = a.pivot_table(index=["method", "causal", "k"], columns="encoder",
                            values=["score", "pct_over"], observed=True).round(2)
        piv.columns = [f"{x} {y}" for x, y in piv.columns]
        L += [f"## {sp}: score and % of GOPs over budget", "", piv.reset_index().to_markdown(index=False), ""]
    t = df[(df.split == "test") & df.method.isin(["abr_vbv", "static_causal", "ramp_causal", "cqp_est", "online_controller_v1"])]
    k = t.pivot_table(index=["method", "encoder"], columns="k", values="score").round(2)
    k.columns = [f"k={c}" for c in k.columns]
    L += ["## Test: causal lookahead curves (score by k)", "", k.reset_index().to_markdown(index=False), ""]
    s = df[df.split == "test"].groupby(["method", "encoder", "cls"]).score.mean().unstack("cls").round(2)
    L += ["## Test: stable vs cut/gradual GOPs (all k pooled)", "", s.reset_index().to_markdown(index=False), ""]
    open(f"{ROOT}/results_v1/baselines_v1_table.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L[:40]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", choices=("x264", "x265"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", 2)))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--gather", action="store_true")
    a = ap.parse_args()
    if a.gather:
        return gather()
    man = {r.clip_id: r for r in pd.read_csv(f"{D}/manifest.csv").itertuples()}
    gops = pd.read_csv(f"{D}/gops.csv").query("split == @a.split")
    bud = pd.read_csv(f"{D}/budgets.csv").query("encoder == @a.encoder")
    _, cur = curves_for(a.encoder)
    glist = list(gops.itertuples())[a.shard::a.nshards]
    if a.limit:
        glist = glist[:a.limit]
    items = []
    for g in glist:
        m = man[g.clip_id]
        bb = bud[(bud.clip_id == g.clip_id) & (bud.gop == g.gop)].set_index("level_q0")
        budgets = {lv: {"B": float(bb.budget_bits[lv]), **{f"est{k}": float(bb[f"base_qp_est_k{k}"][lv]) for k in KS}}
                   for lv in bb.index}
        gd = {"split": g.split, "clip_id": g.clip_id, "gop": g.gop, "label": g.label, "start_frame": g.start_frame,
              "fps": m.fps, "y4m": os.path.join(D, m.path)}
        items.append((a.encoder, gd, budgets, cur[(g.clip_id, g.gop)],
                      os.environ.get("RC_TMP") or os.environ.get("TMPDIR", "/tmp")))
    t0 = time.time()
    with Pool(a.workers) as p:
        rows = [r for part in p.imap_unordered(one_gop, items) for r in part]
    os.makedirs(OUT if not a.tag else f"{OUT}_{a.tag}", exist_ok=True)
    dest = f"{OUT if not a.tag else OUT + '_' + a.tag}/rows_{a.encoder}_{a.split}_{a.shard}of{a.nshards}.parquet"
    if os.path.exists(dest):
        dest = dest.replace(".parquet", f"_{os.environ.get('SLURM_JOB_ID') or time.strftime('%H%M%S')}.parquet")
    pd.DataFrame(rows).to_parquet(dest, index=False)
    print(f"{a.encoder} {a.split} shard {a.shard}/{a.nshards}: {len(glist)} GOPs, {len(rows)} rows, "
          f"{time.time() - t0:.0f}s -> {dest}")


if __name__ == "__main__":
    main()
