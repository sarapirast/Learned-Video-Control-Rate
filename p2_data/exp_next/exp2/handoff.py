"""Experiment 2: handoff -- the stored CQL->PPO@prev 540k learner chooses frames 0..29-m, final4 chooses the last m.

Evaluation only (no training), real encodes, deterministic learner (SB3 predict(deterministic=True)).
- Learner side: Pavneet's env in the lfqp arm (RC_ARM=lfq, RC_ACT_RANGE=10, dPSNR_B metric, previous-GOP base),
  infos rcwork_v1/<enc>_lfqp/results_infos/infos_learn.pkl (slimmed like rl.py), models
  rcwork_v1/<enc>_lfqp/results_rl/cql_ppo_k<k>_fixed_st540k_s<seed>/model.zip.
- final4 side: rclib/controller.decide with final4's setting 1.0:6:1.0:2:3:4:1:1:1:0:3, its train-fitted rate model
  (data/v1/320x180/rd/controller_model.json), the history inputs final4 used on this GOP (ctrl_qhat, rate-prior
  scale ctrl_r from rcwork_v1/<enc>_resh infos, i.e. the stored final4 chain), and the P1 first pass of the resh
  infos. decide() is stateless given (bits, QPs) of the frames already coded, so final4's state is "shadow-updated"
  with the learner's real frames by construction. Its QP is forced through env.q_override.
- m = 0 must reproduce the learner's stored val episodes; m = 30 must reproduce final4's stored rows (--check).

  RC_CODEC=<enc> python -I exp_next/exp2/handoff.py --ms 3,5,10,15,20 --ks 0,5 --seeds 0,1,2 --split val \
      [--shard i --nshards n] [--workers w]
  RC_CODEC=<enc> python -I exp_next/exp2/handoff.py --check [--n 8]
Out: results_v1/next/exp2/rows_<enc>_<split>_<shard>of<n>.pkl (list of per-episode dicts; pickle, because the
     torch env envs/rc has no parquet engine -- the first submission 14200366/7 failed at the write)
"""
import argparse
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

os.environ.update({"RC_ARM": "lfq", "RC_ACT_RANGE": "10", "RC_METRIC": "dpsnr"})
ENC = os.environ["RC_CODEC"]
os.environ["RC_WORK"] = f"/scratch1/aayushso/rcwork_v1/{ENC}_lfqp"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, controller as CTRL, env as E, offrl, policies as P  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
OUT = f"{ROOT}/results_v1/next/exp2"
SETTING = (1.0, 6.0, 1.0, 2.0, 3.0, 4.0, 1.0, 1.0, 1.0, 0.0, 3.0)
TMPL = f"{RC}/{ENC}_lfqp/results_rl/cql_ppo_k{{k}}_fixed_st540k_s{{s}}"
_G = {}


def _init():
    _G["infos"] = pickle.load(open(_G["ipath"], "rb"))
    _G["ctrl"] = pickle.load(open(_G["cpath"], "rb"))
    _G["M"] = CTRL.load_model(ENC, f"{ROOT}/data/v1/320x180/rd/controller_model.json")
    _G["pol"] = {}


def episode(item):
    gid, b, k, s, m = item
    if (k, s) not in _G["pol"]:
        _G["pol"][(k, s)] = P.SB3(os.path.join(TMPL.format(k=k, s=s), "model.zip"))
    pol, info, ci = _G["pol"][(k, s)], _G["infos"][gid], _G["ctrl"][gid]
    r = ci["ctrl_r"].get((b, k), 1.0)
    M = _G["M"] if r == 1.0 else dict(_G["M"], c_i=_G["M"]["c_i"] * r, c_p=_G["M"]["c_p"] * r)
    qhat = ci["ctrl_qhat"].get((b, k))
    fp = np.maximum(np.asarray(ci["fp_bits"], float), 8)
    env = E.make_env({gid: info}, k=k)
    env.force(gid, b)
    obs, _ = env.reset()
    zero = C.ACTIONS.index(0)
    who = []
    for t in range(C.GOP):
        if t < C.GOP - m:
            a = pol(env, obs)
            who.append("L")
        else:
            env.q_override = CTRL.decide(t, env.bits, env.qps, fp, env.budget, k, M, *SETTING, qhat=qhat)
            a = zero
            who.append("F")
        obs, _, done, _, res = env.step(a)
    assert done
    return {"gid": gid, "clip": info["gop"]["clip"], "level": b, "k": k, "seed": s, "m": m, "budget": env.budget,
            "bits": res["bits"], "psnr": res["psnr"], "score": res["score"], "dpsnr_b": res["dpsnr_b"],
            "use": res["use"], "over_pct": res["over_pct"], "qps": list(res["qps"]), "frame_bits": res["frame_bits"],
            "who": "".join(who)}


def setup(split_ids):
    st = f"{RC}/{ENC}_lfqp/results_infos"
    infos = {g: offrl.slim(x) for g, x in pickle.load(open(f"{st}/infos_learn.pkl", "rb")).items()}
    full = pickle.load(open(f"{RC}/{ENC}_resh/results_infos/infos.pkl", "rb"))
    ctrl = {g: {"ctrl_r": full[g]["ctrl_r"], "ctrl_qhat": full[g]["ctrl_qhat"], "fp_bits": full[g]["fp_bits"],
                "ctrl": full[g]["ctrl"]} for g in infos if g in full}
    os.makedirs(OUT, exist_ok=True)
    tmp = os.environ.get("RC_TMP") or "/scratch1/aayushso/tmp"
    _G["ipath"] = P.save_infos_for_workers(infos, f"{tmp}/exp2_{ENC}_infos_{os.getpid()}.pkl")
    _G["cpath"] = P.save_infos_for_workers(ctrl, f"{tmp}/exp2_{ENC}_ctrl_{os.getpid()}.pkl")
    return infos, ctrl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", default="3,5,10,15,20")
    ap.add_argument("--ks", default="0,5")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--split", default="val", choices=("val", "train_select"))
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", 2)) - 1))
    ap.add_argument("--check", action="store_true", help="m=0 vs the learner's stored val rows, m=30 vs final4's")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="smoke: only the first N items of this shard")
    a = ap.parse_args()
    infos, ctrl = setup(None)
    if a.split == "val":
        gids = sorted(g for g, x in infos.items() if x["gop"]["split"] == "val" and g in ctrl)
    else:
        fold = set(json.load(open(f"{ROOT}/exp_next/folds.json"))["train_select_clips"])
        gids = sorted(g for g, x in infos.items() if x["gop"]["split"] == "train" and x["gop"]["clip"] in fold)
    ks, seeds = [int(x) for x in a.ks.split(",")], [int(x) for x in a.seeds.split(",")]
    if a.check:
        ev = {(k, s): pickle.load(open(os.path.join(TMPL.format(k=k, s=s), "eval.pkl"), "rb"))["res"]
              for k in ks for s in seeds[:1]}
        items, ref = [], {}
        for k in ks:
            rows = [r for r in ev[(k, seeds[0])][("fixed", k, "val")] if r["gid"] in ctrl][:a.n]
            for r in rows:
                items.append((r["gid"], r["budget"], k, seeds[0], 0))
                ref[(r["gid"], r["budget"], k, 0)] = (r["qps"], r["bits"], r["score"])
                items.append((r["gid"], r["budget"], k, seeds[0], 30))
                c = ctrl[r["gid"]]["ctrl"][(r["budget"], k)]
                ref[(r["gid"], r["budget"], k, 30)] = (list(c["qps"]), c["bits"], c["score"])
        _init()
        ok = {0: 0, 30: 0}
        for it in items:
            x = episode(it)
            q, bt, sc = ref[(x["gid"], x["level"], x["k"], x["m"])]
            same = list(x["qps"]) == list(q) and int(x["bits"]) == int(bt) and abs(x["score"] - sc) < 1e-9
            ok[x["m"]] += same
            if not same:
                print("MISMATCH", x["gid"], x["level"], x["k"], "m", x["m"], f"score {sc:.4f} -> {x['score']:.4f}")
        n = len(items) // 2
        print(f"check {ENC}: m=0 reproduces the learner {ok[0]}/{n}; m=30 reproduces final4 {ok[30]}/{n}")
        return
    items = [(g, b, k, s, m) for g in gids for b in C.BUDGET_QPS for k in ks for s in seeds
             for m in (int(x) for x in a.ms.split(","))]
    items = items[a.shard::a.nshards]
    if a.limit:
        items = items[:a.limit]
    t0 = time.time()
    with Pool(a.workers, initializer=_init) as p:
        rows = list(p.imap_unordered(episode, items, chunksize=4))
    dest = f"{OUT}/rows_{ENC}_{a.split}_{a.shard}of{a.nshards}{'_limit' if a.limit else ''}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    with open(dest + ".part", "wb") as f:
        pickle.dump(rows, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(dest + ".part", dest)
    print(f"{ENC} {a.split} shard {a.shard}/{a.nshards}: {len(rows)} episodes, {time.time() - t0:.0f}s -> {dest}")


if __name__ == "__main__":
    main()
