"""Build the leak-free arm's infos.pkl ("lf", data-v1 branch, P2 2026-11-09) from P2's v1 data products. No encodes.

Per GOP, starting from the orig arm's info (gop record, features, scene analysis kept for later stages):
  curve   P2's constant-QP curve on P1's frozen settings (data/v1/320x180/rd/rd_native.parquet): QP 18-50, slice bits,
          psnr = mean over frames of the 6:1:1 YUV PSNR (same curve as scripts/baselines_v1.py), frame_bits per QP
  budget  {24, 30, 36, 42}: P2's clip-level budgets (data/v1/320x180/budgets.csv, slice bits; never the GOP's own spend)
  budget_meta  per level: q_fit (hindsight QP spending exactly B), budget / own spend, causal estimates base_qp_est_k*
  static  removed (the lf search starts from the ramp at a hindsight base, rclib/search.py lf_start)
  fp_bits / an  still the orig harness's (Pavneet's settings); recompute before any learner uses them on this arm

Run with P2's project env (needs pyarrow):
  /scratch1/aayushso/envs/ee599/bin/python -I tools/lf_infos.py <x264|x265> <orig RC_WORK> <lf RC_WORK>
Links clips/, gops/ and manifest.json from the orig work dir.
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

D = "/scratch1/aayushso/ee599/data/v1/320x180"
LEVELS = (24, 30, 36, 42)
QPS = list(range(18, 51))


def main(enc, src, dst):
    os.makedirs(os.path.join(dst, "results_infos"), exist_ok=True)
    for name in ("clips", "gops", "manifest.json"):
        if not os.path.lexists(os.path.join(dst, name)):
            os.symlink(os.path.join(src, name), os.path.join(dst, name))
    out = os.path.join(dst, "results_infos", "infos.pkl")
    if os.path.exists(out):
        sys.exit(f"{out} exists; delete it to rebuild")
    with open(os.path.join(src, "results_infos", "infos.pkl"), "rb") as f:
        infos = pickle.load(f)

    rd = pd.read_parquet(f"{D}/rd/rd_native.parquet").query("encoder == @enc")
    rd = {k: v.sort_values("qp") for k, v in rd.groupby(["clip_id", "gop"])}
    fr = pd.read_parquet(f"{D}/rd/rd_frames.parquet", columns=["encoder", "kind", "qp", "clip_id", "gop", "frame",
                                                               "slice_bits"]).query("encoder == @enc and kind == 'cqp'")
    fr = {k: v for k, v in fr.groupby(["clip_id", "gop"])}
    bud = pd.read_csv(f"{D}/budgets.csv").query("encoder == @enc")
    bud = {k: v.set_index("level_q0") for k, v in bud.groupby(["clip_id", "gop"])}

    for gid, x in infos.items():
        key = (x["gop"]["clip"], int(x["gop"]["v1_gop"]))
        c = rd[key]
        assert c.qp.tolist() == QPS, (gid, c.qp.tolist())
        fb = fr[key].pivot(index="qp", columns="frame", values="slice_bits").loc[QPS].to_numpy(np.int64)
        assert fb.shape == (len(QPS), 30) and (fb.sum(1) == c.slice_bits.to_numpy()).all(), gid
        x["curve"] = {"qps": QPS, "bits": c.slice_bits.to_numpy(np.int64), "psnr": c.psnr_yuv_mean_frames.to_numpy(float),
                      "frame_bits": fb.astype(np.int32), "source": "P2 rd_native.parquet (P1 settings, slice bits)"}
        b = bud[key]
        assert sorted(b.index) == list(LEVELS), gid
        x["budget"] = {lv: float(b.loc[lv, "budget_bits"]) for lv in LEVELS}   # float, as in baselines_v1.py
        x["budget_meta"] = {lv: {c2: b.loc[lv, c2] for c2 in ("q_fit", "q_fit_flag", "budget_over_own_cqp", "cls",
                                                              "base_qp_est_k0", "base_qp_est_k2", "base_qp_est_k5",
                                                              "base_qp_est_k10", "base_qp_est_k29")}
                            for lv in LEVELS}
        x.pop("static", None)
        x["arm"] = "lf"
    with open(out, "wb") as f:
        pickle.dump(infos, f)
    r = [v for x in infos.values() for v in x["budget"].values()]
    print(f"{out}: {len(infos)} GOPs x {len(LEVELS)} levels, budget bits min {min(r):.0f} median {np.median(r):.0f} "
          f"max {max(r):.0f}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
