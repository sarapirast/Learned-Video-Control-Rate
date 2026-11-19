"""Experiment 10 (brief Part E item 9): the encoder's 1-pass ABR+VBV with a target margin, val, k in {0, 5}.

Same encode as results_v1/baselines_v1 abr_vbv (scripts/baselines_v1.py: P1 settings, --bitrate = --vbv-maxrate =
m x B x fps / 30, --vbv-bufsize = m x B, --rc-lookahead k), at margins m in {0.95, 0.97, 0.99}; m = 1.00 is the
existing abr_vbv row set (not re-encoded). The budget B used for scoring is always the real budget. Rates are whole
kbit/s and kbit as in baselines_v1 (the encoders need integers), so the effective margin is quantised at low levels:
the realised rate / (m x B rate) is stored as 'rate_q'.
Scored later on the dB metric (exp_next/exp10/abr_margin_report.py); rows keep the old-score columns of baselines_v1.

  python exp_next/exp10/abr_margin.py --encoder x264 --nshards 4      (shard = array task id)
Out: results_v1/next/exp10/rows_<enc>_val_<shard>of<n>.parquet
"""
import argparse
import importlib.util
import os
import shutil
import tempfile
import time
from multiprocessing import Pool

import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/next/exp10"
MARGINS = (0.95, 0.97, 0.99)
KS = (0, 5)
spec = importlib.util.spec_from_file_location("baselines_v1", f"{ROOT}/scripts/baselines_v1.py")
BL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BL)


def one_gop(args):
    enc, g, budgets, curve, tmp, margins, ks = args
    src = BL.RN.read_frames(g["y4m"], g["start_frame"], BL.GOP, 320, 180)
    d = tempfile.mkdtemp(dir=tmp)
    rows = []
    try:
        yuv = os.path.join(d, "in.yuv")
        src.tofile(yuv)
        out = os.path.join(d, "o.bin")
        fps = g["fps"]
        for level, B in budgets.items():
            for m in margins:
                kbps = m * B * eval(fps) / BL.GOP / 1000.0
                rate, buf = str(max(1, round(kbps))), str(max(1, round(m * B / 1000)))
                for k in ks:
                    BL.run(BL.common(enc, yuv, fps, out, ["--bitrate", rate, "--vbv-maxrate", rate,
                                                          "--vbv-bufsize", buf, "--rc-lookahead", str(k)]))
                    b, h = BL.bits_of(enc, out)
                    r = BL.row("abr_vbv_margin", enc, g, level, k, B, b, h, *BL.measure(enc, out, src), curve, True,
                               param=f"{m:.2f}")
                    r["margin"] = m
                    r["rate_q"] = float(rate) / kbps
                    rows.append(r)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", choices=("x264", "x265"), required=True)
    ap.add_argument("--split", default="val", choices=("val", "test", "test2", "parity"))   # test: approved final pass only
    # test2 / parity (exp_next/test2/PLAN.md): run with P2_DATA=data/t2/320x180; rows go to results_v1/test2/abr
    ap.add_argument("--margins", default=",".join(map(str, MARGINS)))
    ap.add_argument("--ks", default=",".join(map(str, KS)))
    ap.add_argument("--tag", default="", help="output name suffix (e.g. ext for the 0.90 / 0.93 extension)")
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", 2)))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    man = {r.clip_id: r for r in pd.read_csv(f"{BL.D}/manifest.csv").itertuples()}
    gops = pd.read_csv(f"{BL.D}/gops.csv").query("split == @a.split")
    bud = pd.read_csv(f"{BL.D}/budgets.csv").query("encoder == @a.encoder")
    _, cur = BL.curves_for(a.encoder)
    glist = list(gops.itertuples())[a.shard::a.nshards]
    if a.limit:
        glist = glist[:a.limit]
    items = []
    for g in glist:
        m = man[g.clip_id]
        bb = bud[(bud.clip_id == g.clip_id) & (bud.gop == g.gop)].set_index("level_q0")
        items.append((a.encoder, {"split": g.split, "clip_id": g.clip_id, "gop": g.gop, "label": g.label,
                                  "start_frame": g.start_frame, "fps": m.fps, "y4m": os.path.join(BL.D, m.path)},
                      {lv: float(bb.budget_bits[lv]) for lv in bb.index}, cur[(g.clip_id, g.gop)],
                      os.environ.get("RC_TMP") or os.environ.get("TMPDIR", "/tmp"),
                      [float(x) for x in a.margins.split(",")], [int(x) for x in a.ks.split(",")]))
    t0 = time.time()
    with Pool(a.workers) as p:
        rows = [r for part in p.imap_unordered(one_gop, items) for r in part]
    out = f"{ROOT}/results_v1/test2/abr" if a.split in ("test2", "parity") else OUT
    if a.split in ("test2", "parity"):
        assert "data/t2" in BL.D, "test2 / parity rows need P2_DATA=data/t2/320x180"
    os.makedirs(out, exist_ok=True)
    tag = (f"_{a.tag}" if a.tag else "") + ("_limit" if a.limit else "")
    dest = f"{out}/rows_{a.encoder}_{a.split}_{a.shard}of{a.nshards}{tag}.parquet"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    pd.DataFrame(rows).to_parquet(dest, index=False)
    print(f"{a.encoder} {a.split} shard {a.shard}/{a.nshards}: {len(glist)} GOPs, {len(rows)} rows, "
          f"{time.time() - t0:.0f}s -> {dest}")


if __name__ == "__main__":
    main()
