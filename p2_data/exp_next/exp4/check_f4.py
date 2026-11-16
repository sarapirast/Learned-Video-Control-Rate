"""R2 check: the f4 observation features and the cap counters on one val episode with forced offsets.
Run in the res job env with RC_RES_RANGE=6:  python -I exp_next/exp4/check_f4.py
"""
import pickle
import sys

import numpy as np

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, env as E, offrl  # noqa: E402

infos = pickle.load(open(f"{C.WORK}/results_infos/infos.pkl", "rb"))
gid = sorted(g for g, x in infos.items() if x["gop"]["split"] == "val")[3]
env = E.make_env({gid: offrl.slim(infos[gid])}, k=5, extra="f4")
env.force(gid, 30)
obs, _ = env.reset()
plan = {2: 6, 3: 6, 4: 6, 10: -6, 11: -6, 20: 6}
print("ACTIONS", C.ACTIONS, "obs dim", obs.shape)
print(" t  q_ctrl  f4[planned, level, log2 plan/rem, log2 cP/prior, left]  -> offset")
for t in range(C.GOP):
    f = obs[E.OBS_DIM:]
    off = plan.get(t, 0)
    if t in (0, 1, 2, 5, 10, 12, 20, 29):
        print(f"{t:2d}  {env.q_ctrl:5d}   {np.round(f, 3)}  -> {off:+d}")
    obs, _, done, _, res = env.step(C.ACTIONS.index(off))
print("counters: beyond dmax", res["n_beyond_dmax"], "beyond fcap", res["n_beyond_fcap"], "range clip",
      res["n_clip_range"], "| score", round(res["score"], 3), "use", round(res["use"], 3))
print("qps     ", res["qps"])
print("ctrl_qps", res["ctrl_qps"])
