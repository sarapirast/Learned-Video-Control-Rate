"""test2: evaluation-only passes of the frozen RL models (exp_next/test2/PLAN.md section 2). Deterministic.

Models (checkpoints read from the v1 work dirs through the test2 work dir's results_rl symlink; nothing trained):
  r3k5    R3 of the 11-16 test pass: res_k5_..._st360k_..._s{3,4,5}/model_180993.zip (the 180k primary)
  r3k2    final-week R3 at k2: res_k2_..._st180k_..._s{3,4,5}/model.zip
  cqlppo  CQL->PPO 540k @prev (lfqp): cql_ppo_k{k}_fixed_st540k_s{0,1,2}/model.zip, --ks 0,5
Env (rc env, gymnasium), set by the job:
  r3*     RC_ARM=res RC_RES_RANGE=6 RC_RES_RECAP=bit RC_METRIC=dpsnr RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3
          RC_WORK=/scratch1/aayushso/rcwork_t2/<enc>_resh
  cqlppo  RC_ARM=lfq RC_ACT_RANGE=10 RC_WORK=/scratch1/aayushso/rcwork_t2/<enc>_lfqp
R3 env settings are checked against each run's stored eval.pkl args (k, drop level, res_mean pooled, extra f4), as in
exp_next/final/eval_r3.py; R3 here uses final4's stored GOP n-1 history (the pre-registered definition).

  python exp_next/test2/eval_t2.py --model r3k5 --split parity     must equal the stored v1 TEST rows exactly
  python exp_next/test2/eval_t2.py --model r3k5 --split test2
Out: results_v1/test2/<model>_<split>_<enc>.pkl = {(seed, k): rows}; parity also prints equal/total.
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
SM = f"{ROOT}/results_v1/next/exp5/shifts_smooth.json"
F4 = "1.0:6:1.0:2:3:4:1:1:1:0:3"
R3 = {"r3k5": (5, "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s{s}", "model_180993.zip"),
      "r3k2": (2, "res_k2_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s{s}", "model.zip")}


def slim_path(name):
    st = runner.Stages("infos")
    p = os.path.join(st.dir, f"{name}_slim.pkl")
    if not os.path.exists(p):
        P.save_infos_for_workers({g: offrl.slim(x) for g, x in st.load(name).items()}, p)
    return p


def stored(model, s, k):
    """The stored v1 TEST rows of the same model (parity reference), or None."""
    if model == "r3k5":
        return pickle.load(open(f"{ROOT}/results_v1/final/r3_test_{C.CODEC}.pkl", "rb"))[(s, "180k")]
    if model == "cqlppo":
        d = os.path.join(C.results_dir("rl"), f"cql_ppo_k{k}_fixed_st540k_s{s}")
        return pickle.load(open(f"{d}/eval.pkl", "rb"))["res"][("fixed", k, "test")]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=("r3k5", "r3k2", "cqlppo"), required=True)
    ap.add_argument("--split", choices=("test2", "parity"), required=True)
    ap.add_argument("--ks", default="0,5", help="cqlppo only")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    assert "rcwork_t2" in C.WORK, f"RC_WORK must be a test2 work dir, got {C.WORK}"
    jobs = []
    if a.model in R3:
        assert C.RES and max(C.ACTIONS) == 6 and C.RES_RECAP == "bit"
        assert os.environ.get("RC_CTRL_SETTING") == F4 and os.environ.get("RC_METRIC") == "dpsnr"
        k, run, mfile = R3[a.model]
        mean = json.load(open(SM))[f"{C.CODEC}|{k}|pooled"]
        ipath = slim_path("infos")
        for s in [int(x) for x in (a.seeds or "3,4,5").split(",")]:
            d = os.path.join(C.results_dir("rl"), run.format(s=s))
            ra = pickle.load(open(f"{d}/eval.pkl", "rb"))["args"]
            assert ra["k"] == k and ra["drop"] == "level" and ra["res_mean"] == "pooled" and ra["extra"] == "f4", ra
            envkw = {"k": k, "mode": "fixed", "drop": ("level",), "prior": False, "extra": "f4", "res_mean": mean,
                     "k_sampler": None}
            jobs.append((s, k, {"kind": "sb3", "path": f"{d}/{mfile}", "algo": "ppo"}, envkw))
    else:
        assert C.ARM == "lfq" and C.LFQ_LEARN and max(C.ACTIONS) == 10, "run with RC_ARM=lfq RC_ACT_RANGE=10"
        assert C.WORK.endswith("_lfqp"), C.WORK
        ipath = slim_path("infos_learn")
        for k in [int(x) for x in a.ks.split(",")]:
            for s in [int(x) for x in (a.seeds or "0,1,2").split(",")]:
                d = os.path.join(C.results_dir("rl"), f"cql_ppo_k{k}_fixed_st540k_s{s}")
                ra = pickle.load(open(f"{d}/eval.pkl", "rb"))["args"]
                assert (ra["method"], ra["k"], ra["mode"], ra["drop"], ra["prior"], ra["extra"], ra["ppo_steps"]) == \
                    ("cql_ppo", k, "fixed", "", False, "", 540000), ra
                envkw = {"k": k, "mode": "fixed", "drop": (), "prior": False, "extra": "", "k_sampler": None}
                jobs.append((s, k, {"kind": "sb3", "path": f"{d}/model.zip", "algo": "ppo"}, envkw))
    infos = pickle.load(open(ipath, "rb"))
    ids = sorted(g for g, x in infos.items() if x["gop"]["split"] == a.split)
    assert ids, f"no {a.split} GOPs in {ipath}"
    res, ok, tot = {}, 0, 0
    for s, k, spec, envkw in jobs:
        rows = P.evaluate(spec, ipath, ids, workers=a.workers, desc=f"{a.model} {a.split} k{k} s{s}", **envkw)
        res[(s, k)] = rows
        if a.split == "parity":
            ref = stored(a.model, s, k)
            if ref is not None:
                st = {(r["gid"], r["budget"]): r for r in ref}
                same = [(r["gid"], r["budget"]) in st and abs(r["score"] - st[(r["gid"], r["budget"])]["score"]) < 1e-9
                        and list(r["qps"]) == list(st[(r["gid"], r["budget"])]["qps"]) for r in rows]
                ok, tot = ok + sum(same), tot + len(same)
    if a.split == "parity":
        print(f"PARITY {a.model} {C.CODEC}: rows equal to the stored v1 test rows {ok}/{tot}"
              + ("" if tot else " (no stored test rows for this model)"))
    os.makedirs(OUT, exist_ok=True)
    dest = f"{OUT}/{a.model}_{a.split}_{C.CODEC}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    pickle.dump(res, open(dest, "wb"))
    print(f"-> {dest} ({len(ids)} GOPs, {sum(len(r) for r in res.values())} rows)")


if __name__ == "__main__":
    main()
