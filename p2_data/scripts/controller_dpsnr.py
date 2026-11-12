"""Controller settings scored on the quality-at-budget metric (tracker 30e; P2 2026-11-10). No encodes.

Reads results_v1/controller_real/<tag>_<codec>_<split>_*.parquet (scripts/controller_real.py episodes; each stores
bits, psnr_yuv and the budget) and rescores every episode as
  score = dPSNR_B - 0.17 dB x %over,  dPSNR_B = PSNR - the GOP's constant-QP PSNR at exactly the budget
(rclib/metrics.py METRIC=dpsnr, same interpolation/extrapolation), flat GOPs excluded (rd/flat_gops.csv).
Per setting: mean score (pooled over k and levels; selection criterion), per k, dPSNR_B, budget use, % over, old score.

  python -I scripts/controller_dpsnr.py <codec> <tag> [--split val]
Out: results_v1/controller_dpsnr/<tag>_<codec>_<split>.md (+ .csv per setting x k)
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import metrics  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
D = f"{ROOT}/data/v1/320x180"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codec", choices=("x264", "x265"))
    ap.add_argument("tag")
    ap.add_argument("--split", default="val")
    a = ap.parse_args()
    files = sorted(glob.glob(f"{ROOT}/results_v1/controller_real/{a.tag}_{a.codec}_{a.split}_*.parquet"))
    assert files, "no files"
    d = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    rd = pd.read_parquet(f"{D}/rd/rd_native.parquet").query("encoder == @a.codec")
    cur = {k: {"bits": v.sort_values("qp").slice_bits.to_numpy(float),
               "psnr": v.sort_values("qp").psnr_yuv_mean_frames.to_numpy(float)} for k, v in rd.groupby(["clip_id", "gop"])}
    flat = pd.read_csv(f"{D}/rd/flat_gops.csv")
    flat = set(flat.gid[flat.flat])
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    n0 = d.gid.nunique()
    d = d[~d.gid.isin(flat)].copy()
    d["dpsnr_b"] = [float(metrics.dpsnr_budget(r.psnr_yuv, cur[(r.clip_id, r.gop)], r.budget_bits)) for r in d.itertuples()]
    d["score_q"] = d.dpsnr_b - metrics.OVER_PENALTY_DB * d.over_pct
    d["use"] = d.bits / d.budget_bits
    dup = d.duplicated(["gid", "level_q0", "k", "setting"]).sum()
    assert dup == 0, f"{dup} duplicate episodes"
    agg = d.groupby("setting").agg(n=("score_q", "size"), score=("score_q", "mean"), dpsnr_b=("dpsnr_b", "mean"),
                                   use=("use", "mean"), over_pct_eps=("over", lambda s: 100 * s.mean()),
                                   mean_over=("over_pct", "mean"), score_old=("score", "mean")).reset_index()
    perk = d.pivot_table(index="setting", columns="k", values="score_q", aggfunc="mean")
    perk.columns = [f"k{c}" for c in perk.columns]
    agg = agg.merge(perk.reset_index(), on="setting").sort_values("score", ascending=False)
    out = f"{ROOT}/results_v1/controller_dpsnr/{a.tag}_{a.codec}_{a.split}"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    agg.to_csv(out + ".csv", index=False)
    txt = [f"# Controller settings on dPSNR_B ({a.codec}, {a.tag}, {a.split}; scripts/controller_dpsnr.py)", "",
           f"{d.gid.nunique()} GOPs ({n0 - d.gid.nunique()} flat excluded), levels {sorted(d.level_q0.unique())}, "
           f"k {sorted(d.k.unique())}. score = dPSNR_B - 0.17 x %over (dB), pooled over k and levels; "
           "setting = margin:dI:i_cap:w0:dmax:fcap:init:pmin:a:b.", "", agg.round(3).to_markdown(index=False)]
    open(out + ".md", "w").write("\n".join(txt))
    print("\n".join(txt[:3]))
    print(agg.round(3).head(12).to_string(index=False))


if __name__ == "__main__":
    main()
