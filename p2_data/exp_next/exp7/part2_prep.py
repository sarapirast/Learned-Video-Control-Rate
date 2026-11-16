"""Exp 7 Part 2 inputs (analysis env: reads parquet). For every val GOP of the encoder: what scripts/controller_real.py's
run_episode needs (y4m, start frame, fps, first pass at QP 32, causal cut flags), the 4 level budgets with the causal
base-QP estimate base_qp_est_k5, the constant-QP curve; plus final4's rate model, the previous-GOP history model (k5)
and stored final4 val rows (k5) for a parity check.

  python -I exp_next/exp7/part2_prep.py x264
Out: results_v1/next/exp7/part2_inputs_<enc>.pkl (keys use Pavneet's GOP ids: "<clip>@<start frame>")
"""
import glob
import importlib.util
import json
import pickle
import sys

import pandas as pd

ENC = sys.argv[1]
SPLIT = sys.argv[2] if len(sys.argv) > 2 else "val"   # test: approved final pass only
ROOT = "/scratch1/aayushso/ee599"
spec = importlib.util.spec_from_file_location("controller_real", f"{ROOT}/scripts/controller_real.py")
CR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CR)
D = CR.D
SETTING = "1.0:6:1.0:2:3:4:1:1:1:0:3"

man = {r.clip_id: r for r in pd.read_csv(f"{D}/manifest.csv").itertuples()}
gops = pd.read_csv(f"{D}/gops.csv").query("split == @SPLIT")
bud = pd.read_csv(f"{D}/budgets.csv").query("encoder == @ENC")
rd = pd.read_parquet(f"{D}/rd/rd_native.parquet").query("encoder == @ENC")
fp = pd.read_parquet(f"{D}/features/fp_bits.parquet").query("encoder == @ENC and fp_qp == @CR.FPQ")
fpd = {k: v.sort_values("frame").fp_slice_bits.to_numpy() for k, v in fp.groupby(["clip_id", "gop"])}
cutd, thr = CR.cut_flags(ENC)
curves = {k: {"bits": v.sort_values("qp").slice_bits.to_numpy(float), "psnr": v.sort_values("qp").psnr_yuv_mean_frames.to_numpy(float)}
          for k, v in rd.groupby(["clip_id", "gop"])}
out = {"gops": {}, "M": json.load(open(CR.MODEL_FILE))[ENC], "pm": json.load(open(f"{D}/base_prev_model.json"))[ENC]["k"]["5"],
       "setting": tuple(float(x) for x in SETTING.split(":")), "cut_threshold": thr}
for g in gops.itertuples():
    m = man[g.clip_id]
    bb = bud[(bud.clip_id == g.clip_id) & (bud.gop == g.gop)].set_index("level_q0")
    out["gops"][f"{g.clip_id}@{g.start_frame}"] = {
        "gd": {"clip_id": g.clip_id, "gop": g.gop, "start_frame": g.start_frame, "fps": m.fps,
               "y4m": f"{D}/{m.path}", "fp": fpd[(g.clip_id, g.gop)], "cut": cutd[(g.clip_id, g.gop)]},
        "levels": {int(lv): {"B": float(r.budget_bits), "qest": float(r.base_qp_est_k5)} for lv, r in bb.iterrows()},
        "curve": curves[(g.clip_id, g.gop)]}
f4 = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{ROOT}/results_v1/controller_real/final4_{ENC}_val_*.parquet"))
f4 = f4[(f4.k == 5) & (f4.gop == 0)]
out["final4_rows"] = f4[["clip_id", "gop", "level_q0", "budget_bits", "bits", "psnr_yuv", "qps"]].head(8).to_dict("records")
pickle.dump(out, open(f"{ROOT}/results_v1/next/exp7/part2_inputs_{ENC}{'' if SPLIT == 'val' else '_' + SPLIT}.pkl", "wb"))
print(ENC, len(out["gops"]), "val GOPs; cut threshold", thr, "; parity rows", len(out["final4_rows"]))
