"""Re-run final4 (k 0/2/5/10/29) and R3 (k5, seeds 3-5, 180k) on the full x264 val set through rclib + the shim.

rclib = p1-fast-backend's pavneet_pipeline (RC_BACKEND=shim hook). Episode set = every val GOP in the resh infos
(flat GOPs already dropped) x the 4 budget levels, as exp_next/final/eval_r3.py. Episode loop = rclib policies._episode,
keeping per-frame bits.
  final4: RC_RES_RECAP=0, offset 0 every frame (tools/res_parity.py), k as given
  R3:     RC_RES_RECAP=bit, env arguments of exp_next/final/eval_r3.py, model_180993.zip
Out: <out>/rows_final4_k<k>.pkl, <out>/rows_r3_s<seed>.pkl
"""
import argparse
import json
import os
import pickle
import sys
import time

REPO = "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate"
sys.path.insert(0, f"{REPO}/pavneet_pipeline")
sys.path.insert(0, REPO)
from rclib import codec, config as C, env as E, policies as P  # noqa: E402

IPATH = "/scratch1/aayushso/rcwork_v1/x264_resh/results_infos/infos_slim.pkl"
RUN = ("/scratch1/aayushso/rcwork_v1/x264_resh/results_rl/"
       "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s{s}")
SM = "/scratch1/aayushso/ee599/results_v1/next/exp5/shifts_smooth.json"
OUT = "/scratch1/ahhanagu/ee599/results/baselines_val"


def episode(pol, infos, gid, b, envkw):
    env = E.make_env({gid: infos[gid]}, **envkw)
    env.force(gid, b)
    obs, _ = env.reset()
    done = False
    while not done:
        obs, r, done, _, res = env.step(pol(env, obs))
    return {"gid": gid, "budget": b, "k": envkw["k"], "qps": list(env.qps), "frame_bits": list(env.bits),
            "bits": int(sum(env.bits)), "psnr": res["psnr"], "score": res["score"]}


def run(tag, pol, infos, gids, envkw):
    t0 = time.perf_counter()
    rows = [episode(pol, infos, g, b, envkw) for g in gids for b in C.BUDGET_QPS]
    dt = time.perf_counter() - t0
    dest = f"{OUT}/rows_{tag}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; not overwriting"
    pickle.dump({"rows": rows, "secs": dt, "envkw": {k: v for k, v in envkw.items() if k != "res_mean"},
                 "backend": codec.BACKEND}, open(dest, "wb"))
    print(f"{tag}: {len(rows)} episodes in {dt:.0f} s ({len(rows) / dt:.2f}/s) -> {dest}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=("final4", "r3"), required=True)
    ap.add_argument("--ks", default="0,2,5,10,29")
    ap.add_argument("--seeds", default="3,4,5")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    assert C.CODEC == "x264" and C.RES and max(C.ACTIONS) == 6 and codec.BACKEND == "shim"
    assert os.environ.get("RC_METRIC") == "dpsnr" and os.environ.get("RC_CTRL_SETTING") == "1.0:6:1.0:2:3:4:1:1:1:0:3"
    infos = pickle.load(open(IPATH, "rb"))
    gids = sorted(g for g, x in infos.items() if x["gop"]["split"] == "val")
    if a.limit:
        gids = gids[:a.limit]
    print(f"{len(gids)} val GOPs x {len(C.BUDGET_QPS)} levels", flush=True)
    if a.method == "final4":
        assert C.RES_RECAP == ""
        pol = P.make({"kind": "static"})
        for k in (int(x) for x in a.ks.split(",")):
            run(f"final4_k{k}" + ("_limit" if a.limit else ""), pol, infos, gids, {"k": k})
    else:
        assert C.RES_RECAP == "bit"
        mean = json.load(open(SM))["x264|5|pooled"]
        for s in (int(x) for x in a.seeds.split(",")):
            ev = pickle.load(open(f"{RUN.format(s=s)}/eval.pkl", "rb"))["args"]
            assert ev["k"] == 5 and ev["drop"] == "level" and ev["res_mean"] == "pooled" and ev["extra"] == "f4"
            pol = P.make({"kind": "sb3", "path": f"{RUN.format(s=s)}/model_180993.zip", "algo": "ppo"})
            envkw = {"k": 5, "mode": "fixed", "drop": ("level",), "prior": False, "extra": "f4", "res_mean": mean,
                     "k_sampler": None}
            run(f"r3_s{s}" + ("_limit" if a.limit else ""), pol, infos, gids, envkw)


if __name__ == "__main__":
    main()
