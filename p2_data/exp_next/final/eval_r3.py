"""F: evaluation-only pass of the stored R3-recipe models (fresh seeds 3-5; exp_next/final/PREREG.md, branch A).

Models per (encoder, seed): model_180993.zip = the primary 180k model, model.zip = the 360k secondary. Each run's own
stored settings (eval.pkl args: res arm, -6..+6, f4, drop level, res_mean pooled, k5, fixed) with RC_RES_RECAP=bit.
Deterministic. --split val must reproduce the stored val rows exactly (check before test).

  RC_ARM=res RC_RES_RANGE=6 RC_RES_RECAP=bit RC_CODEC=<enc> RC_CTRL_SETTING=<final4> RC_WORK=rcwork_v1/<enc>_resh ... \
      python exp_next/final/eval_r3.py --split val --check 3      (parity on the first 3 val GOPs)
      python exp_next/final/eval_r3.py --split test               (only in the approved test pass)
Out: results_v1/final/r3_<split>_<enc>.pkl = {(seed, "180k" | "360k"): rows}
"""
import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, policies as P, runner  # noqa: E402

OUT = "/scratch1/aayushso/ee599/results_v1/final"
RUN = "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s{s}"
SM = "/scratch1/aayushso/ee599/results_v1/next/exp5/shifts_smooth.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("val", "test"), required=True)
    ap.add_argument("--check", type=int, default=0)
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    assert C.RES and max(C.ACTIONS) == 6 and C.RES_RECAP == "bit"
    assert os.environ.get("RC_CTRL_SETTING") == "1.0:6:1.0:2:3:4:1:1:1:0:3"
    ipath = os.path.join(runner.Stages("infos").dir, "infos_slim.pkl")
    infos = pickle.load(open(ipath, "rb"))
    ids = sorted(g for g, x in infos.items() if x["gop"]["split"] == a.split)
    if a.check:
        ids = ids[:a.check]
    mean = json.load(open(SM))[f"{C.CODEC}|5|pooled"]
    res, ok, tot = {}, 0, 0
    for s in (3, 4, 5):
        d = os.path.join(C.results_dir("rl"), RUN.format(s=s))
        ev = pickle.load(open(f"{d}/eval.pkl", "rb"))
        ra = ev["args"]
        assert ra["k"] == 5 and ra["drop"] == "level" and ra["res_mean"] == "pooled" and ra["extra"] == "f4"
        envkw = {"k": 5, "mode": "fixed", "drop": ("level",), "prior": False, "extra": "f4", "res_mean": mean,
                 "k_sampler": None}
        ck = pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"]
        for lab, path, stored in (("180k", f"{d}/model_180993.zip", ck.get((180993, "fixed", 5, "val"))),
                                  ("360k", f"{d}/model.zip", ev["res"][("fixed", 5, "val")])):
            rows = P.evaluate({"kind": "sb3", "path": path, "algo": "ppo"}, ipath, ids, workers=a.workers,
                              desc=f"{a.split} s{s} {lab}", **envkw)
            res[(s, lab)] = rows
            if a.split == "val":
                st = {(r["gid"], r["budget"]): r for r in stored}
                same = [abs(r["score"] - st[(r["gid"], r["budget"])]["score"]) < 1e-9 and
                        list(r["qps"]) == list(st[(r["gid"], r["budget"])]["qps"]) for r in rows]
                ok, tot = ok + sum(same), tot + len(same)
    if a.split == "val":
        print(f"val parity {C.CODEC}: re-evaluated rows equal the stored val rows {ok}/{tot}")
    if a.check:
        return
    os.makedirs(OUT, exist_ok=True)
    dest = f"{OUT}/r3_{a.split}_{C.CODEC}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    pickle.dump(res, open(dest, "wb"))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
