"""Exp 0 items 2, 4, 7 (no encodes).
 4: final4 per-episode rows on TRAIN (results_v1/controller_real/final4_<enc>_train_*.parquet): every (GOP, level, k)?
 2: the resh infos' stored controller rows (info["ctrl"][(level, k)]) on train: present for every non-flat episode?
 7: level-24 hole: episodes whose budget exceeds the constant-QP curve's largest point (QP 18), so PSNR_CQP(B) is
    linearly extrapolated (rclib/metrics.py psnr_at_bits); counts per split, encoder and level.
  python -I exp_next/exp0/coverage_checks.py
"""
import glob
import pickle

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
flat = pd.read_csv(f"{ROOT}/data/v1/320x180/rd/flat_gops.csv")
gops = flat[["clip_id", "gop", "gid", "split", "flat"]]
LV, KS = (24, 30, 36, 42), (0, 2, 5, 10, 29)
for enc in ("x264", "x265"):
    f = pd.concat(pd.read_parquet(p, columns=["clip_id", "gop", "level_q0", "k"])
                  for p in glob.glob(f"{ROOT}/results_v1/controller_real/final4_{enc}_train_*.parquet"))
    tr = gops[gops.split == "train"]
    want = {(c, g, l, k) for c, g in zip(tr.clip_id, tr.gop) for l in LV for k in KS}
    want_nf = {(c, g, l, k) for c, g, fl in zip(tr.clip_id, tr.gop, tr.flat) if not fl for l in LV for k in KS}
    have = set(zip(f.clip_id, f.gop, f.level_q0, f.k))
    print(f"[4] {enc} final4 train rows {len(f)} (unique {len(have)}); expected {len(want)} "
          f"(non-flat {len(want_nf)}); missing non-flat {len(want_nf - have)}; extra {len(have - want)}")
    inf = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
    nf = set(gops.loc[~gops.flat, "gid"])
    cnt = {}
    for split in ("train", "val", "test"):
        gl = [g for g, x in inf.items() if x["gop"]["split"] == split and g in nf]
        miss = sum((l, k) not in inf[g].get("ctrl", {}) for g in gl for l in LV for k in KS)
        cnt[split] = (len(gl), miss)
    print(f"[2] {enc} resh infos: non-flat GOPs / missing ctrl rows by split: {cnt}")
    # level-24 hole
    rows = []
    for g, x in inf.items():
        if g not in nf:
            continue
        mx = max(x["curve"]["bits"])
        for l in LV:
            B = x["budget"].get(l)
            if B is None:
                continue
            rows.append((x["gop"]["split"], l, B > mx, B / mx))
    r = pd.DataFrame(rows, columns=["split", "level", "beyond", "ratio"])
    t = r.groupby(["split", "level"]).beyond.agg(["sum", "count"])
    print(f"[7] {enc} episodes with B above the QP-18 point (extrapolated reference), per split x level:")
    print(t.unstack(0).to_string())
    print(f"    ratio B / bits(QP18) among those: median {r[r.beyond].ratio.median():.2f}, max {r.ratio.max():.2f}")
