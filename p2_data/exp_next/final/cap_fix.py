"""PSNR-cap correction (Ahhana 11-16): one convention everywhere = each plane's per-frame PSNR capped at 100 dB (as
rclib, i.e. every learner's rows). The constant-QP curves (scripts/rd_native.py) and final4's rows
(scripts/controller_real.py) floored the MSE at 1e-10 instead (a zero-error plane = 148 dB).

1. Curves: recompute every GOP's curve PSNR from data/v1/320x180/rd/rd_frames.parquet with and without the cap; the
   uncapped recompute must equal rd_native.parquet's psnr_yuv_mean_frames; keep the capped curve where it differs.
2. final4: for every stored final4 row (val + test, all k, all levels) of a GOP whose capped curve differs, re-encode
   final4's stored per-frame QPs (controller_real.encode_prefix), require identical bits and uncapped PSNR equal to
   the stored psnr_yuv, and record the capped PSNR.

  (encoder env as jobs/p2_step.sbatch) python exp_next/final/cap_fix.py <enc>
Out: results_v1/final/cap_fix_<enc>.pkl = {"curves": {gid: capped psnr per QP 18..50}, "final4": {(gid, level, k):
     {"psnr": capped, "psnr_uncapped", "bits"}}}, plus a printed summary.
"""
import glob
import importlib.util
import os
import pickle
import sys
import tempfile

import numpy as np
import pandas as pd

ENC = sys.argv[1]
ROOT = "/scratch1/aayushso/ee599"
V1 = f"{ROOT}/data/v1/320x180"
D = os.environ.get("P2_DATA") or V1   # test2 (exp_next/test2/PREREG.md): P2_DATA=data/t2/320x180
T2 = os.path.realpath(D) != os.path.realpath(V1)
SPLITS, TAG = (("test2", "parity"), "t2final4") if T2 else (("val", "test"), "final4")
OUTD = f"{ROOT}/results_v1/test2" if T2 else f"{ROOT}/results_v1/final"
spec = importlib.util.spec_from_file_location("controller_real", f"{ROOT}/scripts/controller_real.py")
CR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CR)
RN = CR.RN


def plane_psnr(m, cap):
    p = 10 * np.log10(255.0 ** 2 / np.maximum(m, 1e-10))
    return np.minimum(p, 100.0) if cap else p


def yuv(my, mu, mv, cap):
    return (6 * plane_psnr(my, cap) + plane_psnr(mu, cap) + plane_psnr(mv, cap)) / 8


def main():
    f = pd.read_parquet(f"{D}/rd/rd_frames.parquet").query("encoder == @ENC")
    f["p_unc"] = yuv(f.mse_y.to_numpy(), f.mse_u.to_numpy(), f.mse_v.to_numpy(), False)
    f["p_cap"] = yuv(f.mse_y.to_numpy(), f.mse_u.to_numpy(), f.mse_v.to_numpy(), True)
    g = f.groupby(["clip_id", "gop", "qp"])[["p_unc", "p_cap"]].mean().reset_index()
    rd = pd.read_parquet(f"{D}/rd/rd_native.parquet").query("encoder == @ENC")[["clip_id", "gop", "qp", "psnr_yuv_mean_frames"]]
    m = g.merge(rd, on=["clip_id", "gop", "qp"])
    err = float((m.p_unc - m.psnr_yuv_mean_frames).abs().max())
    assert err < 1e-6, f"uncapped recompute does not match rd_native: {err}"
    gops = pd.read_csv(f"{D}/gops.csv")
    starts = {(r.clip_id, r.gop): r.start_frame for r in gops.itertuples()}
    curves = {}
    for (c, gp), x in m.groupby(["clip_id", "gop"]):
        x = x.sort_values("qp")
        if (x.p_cap - x.p_unc).abs().max() > 1e-9:
            curves[f"{c}@{starts[(c, gp)]}"] = x.p_cap.to_numpy()
    print(f"{ENC}: curves recomputed for {m.groupby(['clip_id', 'gop']).ngroups} GOPs (uncapped max diff {err:.1e}); "
          f"{len(curves)} GOPs change under the cap")
    man = {r.clip_id: r for r in pd.read_csv(f"{D}/manifest.csv").itertuples()}
    fixes = {}
    for split in SPLITS:
        d = pd.concat(pd.read_parquet(p) for p in glob.glob(f"{ROOT}/results_v1/controller_real/{TAG}_{ENC}_{split}_*.parquet"))
        d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
        d = d[d.gid.isin(curves)]
        for r in d.itertuples():
            mf = man[r.clip_id]
            src = RN.read_frames(os.path.join(D, mf.path), int(starts[(r.clip_id, r.gop)]), 30, 320, 180)
            with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR", "/scratch1/aayushso/tmp")) as td:
                yf = os.path.join(td, "in.yuv")
                src.tofile(yf)
                sl, out = CR.encode_prefix(ENC, yf, 30, list(r.qps), mf.fps, td)
                my, mu, mv = RN.plane_mse(src, RN.decode(out, 30, 320, 180), 320, 180)
            bits = int(sum(sl))
            unc, cap = float(yuv(my, mu, mv, False).mean()), float(yuv(my, mu, mv, True).mean())
            assert bits == int(r.bits), (r.gid, r.level_q0, r.k, bits, r.bits)
            assert abs(unc - float(r.psnr_yuv)) < 1e-6, (r.gid, r.level_q0, r.k, unc, r.psnr_yuv)
            fixes[(r.gid, int(r.level_q0), int(r.k))] = {"psnr": cap, "psnr_uncapped": unc, "bits": bits, "split": split}
    dl = [v["psnr_uncapped"] - v["psnr"] for v in fixes.values()]
    print(f"{ENC}: final4 rows re-measured {len(fixes)} (bits and uncapped PSNR identical to stored); PSNR drop under "
          f"the cap: mean {np.mean(dl):.3f}, max {np.max(dl):.3f} dB; GOPs: {sorted({k[0] for k in fixes})}")
    os.makedirs(OUTD, exist_ok=True)
    dest = f"{OUTD}/cap_fix_{ENC}.pkl"
    assert not (T2 and os.path.exists(dest)), f"{dest} exists; never overwrite"
    pickle.dump({"curves": curves, "final4": fixes}, open(dest, "wb"))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
