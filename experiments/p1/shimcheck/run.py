"""CLI vs shim backend for rclib's env: final4 or R3 (x264 k5, seed 3, 180k) on a few val GOPs.

Episode loop = rclib/policies.py _episode (same env construction), but keeps per-frame bits / PSNR. Single process.
  RC_BACKEND=cli|shim ... python -I run.py --method final4|r3 --out rows.pkl [--pixels]
"""
import argparse
import json
import os
import pickle
import sys
import time

sys.path.insert(0, "/scratch1/ahhanagu/tmp/mainpp/pavneet_pipeline")      # main's rclib + the RC_BACKEND hook
sys.path.insert(0, "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate")  # p1: x264env
import numpy as np  # noqa: E402
from rclib import codec, config as C, data, env as E, policies as P  # noqa: E402

IPATH = "/scratch1/aayushso/rcwork_v1/x264_resh/results_infos/infos_slim.pkl"
RUN = ("/scratch1/aayushso/rcwork_v1/x264_resh/results_rl/"
       "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s3")
SM = "/scratch1/aayushso/ee599/results_v1/next/exp5/shifts_smooth.json"
CLIPS = "/scratch1/aayushso/ee599/data/v1/320x180/clips"


def pick(infos, n_each=5):
    """5 stable + 5 cut val GOPs, one per clip, in sorted id order."""
    out, seen = {"stable": [], "cut": []}, set()
    for g in sorted(g for g, x in infos.items() if x["gop"]["split"] == "val"):
        lab, clip = infos[g]["gop"]["label"], infos[g]["gop"]["clip"]
        if lab in out and len(out[lab]) < n_each and (lab, clip) not in seen:
            out[lab].append(g)
            seen.add((lab, clip))
    return out["stable"] + out["cut"]


def pixels(infos, gids):
    """rclib's GOP .yuv vs the clip y4m read with P1's reader (frames start..start+29)."""
    from x264env import read_y4m
    bad = []
    for g in gids:
        x = infos[g]["gop"]
        yuv = codec._read_frames(data.gop_path(g), C.GOP)
        _, _, _, _, it = read_y4m(os.path.join(CLIPS, x["clip"] + ".y4m"))
        fr = [f for i, f in zip(range(x["start"] + C.GOP), it) if i >= x["start"]]
        ref = np.stack([np.frombuffer(f, np.uint8) for f in fr])
        if ref.shape != yuv.shape or not np.array_equal(ref, yuv):
            bad.append(g)
    return bad


def episode(pol, infos, gid, b, envkw):
    env = E.make_env({gid: infos[gid]}, **envkw)
    env.force(gid, b)
    obs, _ = env.reset()
    done = False
    while not done:
        obs, r, done, _, res = env.step(pol(env, obs))
    return {"gid": gid, "budget": b, "qps": list(env.qps), "bits": list(env.bits), "score": res["score"],
            "total_bits": int(sum(env.bits)), "mean_psnr": res.get("mean_psnr"), "res": res}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=("final4", "r3"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pixels", action="store_true")
    a = ap.parse_args()
    assert C.CODEC == "x264" and C.RES and max(C.ACTIONS) == 6
    assert os.environ.get("RC_CTRL_SETTING") == "1.0:6:1.0:2:3:4:1:1:1:0:3"
    infos = pickle.load(open(IPATH, "rb"))
    gids = pick(infos)
    if a.pixels:
        bad = pixels(infos, gids)
        print(f"pixels: {len(gids) - len(bad)}/{len(gids)} GOPs identical" + (f"; MISMATCH {bad}" if bad else ""))
    if a.method == "final4":
        assert C.RES_RECAP == "", "final4 alone: RC_RES_RECAP=0"
        spec, envkw = {"kind": "static"}, {"k": 5}                      # offset 0 = final4 (tools/res_parity.py)
    else:
        assert C.RES_RECAP == "bit"
        ev = pickle.load(open(f"{RUN}/eval.pkl", "rb"))["args"]
        assert ev["k"] == 5 and ev["drop"] == "level" and ev["res_mean"] == "pooled" and ev["extra"] == "f4"
        spec = {"kind": "sb3", "path": f"{RUN}/model_180993.zip", "algo": "ppo"}
        envkw = {"k": 5, "mode": "fixed", "drop": ("level",), "prior": False, "extra": "f4",
                 "res_mean": json.load(open(SM))["x264|5|pooled"], "k_sampler": None}   # = exp_next/final/eval_r3.py
    pol = P.make(spec)
    episode(pol, infos, gids[0], C.BUDGET_QPS[0], envkw)     # warm-up (model load, first imports), not timed
    t0 = time.perf_counter()
    rows = [episode(pol, infos, g, b, envkw) for g in gids for b in C.BUDGET_QPS]
    dt = time.perf_counter() - t0
    print(f"{a.method} backend={codec.BACKEND}: {len(rows)} episodes in {dt:.1f} s = {len(rows) / dt:.2f} episodes/s")
    pickle.dump({"gids": gids, "labels": [infos[g]["gop"]["label"] for g in gids], "rows": rows, "secs": dt,
                 "backend": codec.BACKEND, "method": a.method}, open(a.out, "wb"))


if __name__ == "__main__":
    main()
