"""test2 PREREG secondary 10: Ahhana's R3 at k0 / k29 (x264, seeds 3-5, 180k), evaluation only. Deterministic.

Models (read in place from Ahhana's dir, nothing copied or trained; received 11-18, before the Thu 11-19 12:00 freeze):
  r3k0a / r3k29a   /scratch1/ahhanagu/ee599/results/r3_kcurve/work/results_rl/
                   res_k{0,29}_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s{3,4,5}/model.zip
  mean[t]          her shifts_smooth.json, key x264|K|pooled (identical to ours on every shared key; asserted for k0)
Env (rc env), as for r3k5 in eval_t2.py:
  RC_CODEC=x264 RC_ARM=res RC_RES_RANGE=6 RC_RES_RECAP=bit RC_METRIC=dpsnr RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3
  --split val     RC_WORK=/scratch1/aayushso/rcwork_v1/x264_resh: PARITY, must equal her stored eval.pkl val rows
  --split test2   RC_WORK=/scratch1/aayushso/rcwork_t2/x264_resh (+ P2_DATA / P2_RCWORK of test2)
Gate (PREREG section 2): no test2 number of these models is read before the val parity line is all equal.
Out: results_v1/test2/<model>_<split>_x264.pkl = {(seed, k): rows}; never overwritten.
"""
import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, offrl, policies as P, runner  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/test2"
AH = "/scratch1/ahhanagu/ee599/results/r3_kcurve"
SM_AH = f"{AH}/exp5/shifts_smooth.json"
SM_OURS = f"{ROOT}/results_v1/next/exp5/shifts_smooth.json"
F4 = "1.0:6:1.0:2:3:4:1:1:1:0:3"
RUN = "res_k{k}_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s{s}"
MODELS = {"r3k0a": 0, "r3k29a": 29}
WORKS = {"val": "/scratch1/aayushso/rcwork_v1/x264_resh", "test2": "/scratch1/aayushso/rcwork_t2/x264_resh"}


def slim_path():
    st = runner.Stages("infos")
    p = os.path.join(st.dir, "infos_slim.pkl")
    if not os.path.exists(p):
        P.save_infos_for_workers({g: offrl.slim(x) for g, x in st.load("infos").items()}, p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=tuple(MODELS), required=True)
    ap.add_argument("--split", choices=tuple(WORKS), required=True)
    ap.add_argument("--seeds", default="3,4,5")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--dry", action="store_true", help="checks + job list only, no encodes")
    a = ap.parse_args()
    assert C.CODEC == "x264", "Ahhana's models are x264 only"
    assert os.path.realpath(C.WORK) == os.path.realpath(WORKS[a.split]), f"RC_WORK {C.WORK} != {WORKS[a.split]}"
    assert C.RES and max(C.ACTIONS) == 6 and C.RES_RECAP == "bit"
    assert os.environ.get("RC_CTRL_SETTING") == F4 and os.environ.get("RC_METRIC") == "dpsnr"
    k = MODELS[a.model]
    sm = json.load(open(SM_AH))
    if f"x264|{k}|pooled" in json.load(open(SM_OURS)):
        assert sm[f"x264|{k}|pooled"] == json.load(open(SM_OURS))[f"x264|{k}|pooled"], "shift files differ"
    mean = sm[f"x264|{k}|pooled"]
    ipath = slim_path()
    infos = pickle.load(open(ipath, "rb"))
    ids = sorted(g for g, x in infos.items() if x["gop"]["split"] == a.split)
    assert ids, f"no {a.split} GOPs in {ipath}"
    jobs = []
    for s in [int(x) for x in a.seeds.split(",")]:
        d = os.path.join(AH, "work", "results_rl", RUN.format(k=k, s=s))
        e = pickle.load(open(f"{d}/eval.pkl", "rb"))
        ra = e["args"]
        assert (ra["method"], ra["k"], ra["mode"], ra["drop"], ra["res_mean"], ra["extra"], ra["ppo_steps"], ra["lam"],
                ra["seed"], ra["prior"]) == ("res", k, "fixed", "level", "pooled", "f4", 180000, 0.17, s, False), ra
        envkw = {"k": k, "mode": "fixed", "drop": ("level",), "prior": False, "extra": "f4", "res_mean": mean,
                 "k_sampler": None}
        jobs.append((s, {"kind": "sb3", "path": f"{d}/model.zip", "algo": "ppo"}, envkw, e["res"].get(("fixed", k, "val"))))
    print(f"{a.model} {a.split}: k{k}, seeds {[j[0] for j in jobs]}, {len(ids)} GOPs, infos {ipath}")
    if a.dry:
        return
    res, ok, tot = {}, 0, 0
    for s, spec, envkw, ref in jobs:
        rows = P.evaluate(spec, ipath, ids, workers=a.workers, desc=f"{a.model} {a.split} k{k} s{s}", **envkw)
        res[(s, k)] = rows
        if a.split == "val":
            st = {(r["gid"], r["budget"]): r for r in ref}
            same = [(r["gid"], r["budget"]) in st and abs(r["score"] - st[(r["gid"], r["budget"])]["score"]) < 1e-9
                    and list(r["qps"]) == list(st[(r["gid"], r["budget"])]["qps"]) for r in rows]
            print(f"  s{s}: {sum(same)}/{len(same)} equal (stored {len(ref)} rows)")
            ok, tot = ok + sum(same), tot + len(same)
    if a.split == "val":
        print(f"PARITY {a.model} x264: rows equal to Ahhana's stored val rows {ok}/{tot}")
    os.makedirs(OUT, exist_ok=True)
    dest = f"{OUT}/{a.model}_{a.split}_x264.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    pickle.dump(res, open(dest, "wb"))
    print(f"-> {dest} ({len(ids)} GOPs, {sum(len(r) for r in res.values())} rows)")


if __name__ == "__main__":
    main()
