"""Exp 5b BC-only rung: final4 + mean[t] + BC (argmax over R2's 13 offsets), bit cap only, real encodes.
Pre-registration: exp_next/exp5/PREREG_BC.md (REVISION 2).

Env: R2's residual env (RC_ARM=res RC_RES_RANGE=6, final4 setting, rcwork_v1/<enc>_resh infos), extra f4, drop
"level" + "history" (o[2], o[5..8] = 0, as in the BC data), res_float = mean[t] = shifts_smooth.json
"<enc>|<k>|pooled", RC_RES_RECAP=bit. Frame t: q = round(final4's real-valued QP + mean[t]) + BC offset, then the bit
cap. Deterministic (argmax). Models: results_v1/next/exp5/bc/bc_<enc>_k<k>_s<s>.pt (bc_train.py).

  RC_CODEC=<enc> ... python exp_next/exp5/bc_eval.py --split fold [--ks 0,5] [--seeds 0,1,2]
  RC_CODEC=<enc> ... python exp_next/exp5/bc_eval.py --check [--n 4]   BC replaced by "always offset 0" and mean 0:
                                                                        must reproduce final4's stored rows
Out: results_v1/next/exp5/bc_rows_<enc>_<split>.pkl (one row per (GOP, level, k, seed))
"""
import argparse
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import torch

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, env as E, offrl, policies as P  # noqa: E402

assert C.RES and max(C.ACTIONS) == 6, "run with RC_ARM=res RC_RES_RANGE=6"
ROOT = "/scratch1/aayushso/ee599"
RC = os.environ.get("P2_RCWORK") or "/scratch1/aayushso/rcwork_v1"   # test2 (exp_next/test2/PLAN.md): rcwork_t2; default unchanged
ENC = C.CODEC
EXP5 = f"{ROOT}/results_v1/next/exp5"
DROP = ("level", "history")
_G = {}


def _init():
    torch.set_num_threads(1)
    _G["infos"] = pickle.load(open(_G["ipath"], "rb"))
    _G["nets"] = {}


def net_for(k, s):
    key = (k, s)
    if key not in _G["nets"]:
        ck = torch.load(f"{_G['bcdir']}/bc_{ENC}_k{k}_s{s}.pt", weights_only=False)
        net = offrl.mlp(ck["obs_dim"], len(C.ACTIONS))
        net.load_state_dict(ck["state_dict"])
        net.eval()
        _G["nets"][key] = net
    return _G["nets"][key]


def episode(item):
    gid, lv, k, s, mean, zero = item
    C.RES_RECAP = "bit"
    env = E.make_env({gid: _G["infos"][gid]}, k=k, extra="f4", drop=DROP)
    env.force(gid, lv, k)
    obs, _ = env.reset()
    env.res_float = np.asarray(mean, float)
    net = None if zero else net_for(k, s)
    acts = []
    for t in range(C.GOP):
        if zero:
            a = C.ACTIONS.index(0)
        else:
            with torch.no_grad():
                a = int(net(torch.from_numpy(np.asarray(obs, np.float32))[None]).argmax(1)[0])
        acts.append(C.ACTIONS[a])
        obs, _, done, _, res = env.step(a)
    assert done
    return {"gid": gid, "clip": _G["infos"][gid]["gop"]["clip"], "level": lv, "k": k, "seed": s,
            "budget": env.budget, "bits": res["bits"], "psnr": res["psnr"], "score": res["score"],
            "static_score": res["static_score"], "use": res["use"], "over_pct": res["over_pct"],
            "qps": list(res["qps"]), "ctrl_qps": list(res["ctrl_qps"]), "acts": acts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="fold", choices=("fold", "val", "test2", "parity"))   # test2/parity: --out results_v1/test2
    ap.add_argument("--ks", default="0,5")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--workers", type=int, default=max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", 2)) - 1))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="smoke: first N items")
    ap.add_argument("--bcdir", default=f"{EXP5}/bc")
    ap.add_argument("--out", default=None)
    ap.add_argument("--tag", default="", help="final week: output name suffix (e.g. k2_s345)")
    a = ap.parse_args()
    out = a.out or EXP5
    _G["bcdir"] = a.bcdir
    full = pickle.load(open(f"{RC}/{ENC}_resh/results_infos/infos.pkl", "rb"))
    fold = set(json.load(open(f"{ROOT}/exp_next/folds.json"))["train_select_clips"])
    if a.split in ("val", "test2", "parity"):
        gids = sorted(g for g, x in full.items() if x["gop"]["split"] == a.split)
    else:
        gids = sorted(g for g, x in full.items() if x["gop"]["split"] == "train" and x["gop"]["clip"] in fold)
    infos = {g: offrl.slim(full[g]) for g in gids}
    tmp = os.environ.get("RC_TMP") or "/scratch1/aayushso/tmp"
    _G["ipath"] = P.save_infos_for_workers(infos, f"{tmp}/exp5b_{ENC}_infos_{os.getpid()}.pkl")
    sm = json.load(open(f"{EXP5}/shifts_smooth.json"))
    ks, seeds = [int(x) for x in a.ks.split(",")], [int(x) for x in a.seeds.split(",")]
    if a.check:                                   # offset 0, mean 0, bit cap, masked obs: final4 exactly
        _init()
        rng = np.random.default_rng(0)
        ok = tot = 0
        for gid in rng.choice(gids, a.n, replace=False):
            for lv in C.BUDGET_QPS:
                k = int(rng.choice(ks))
                r = episode((gid, lv, k, 0, [0.0] * C.GOP, True))
                c = full[gid]["ctrl"][(lv, k)]
                same = r["qps"] == list(c["qps"]) and int(r["bits"]) == int(c["bits"]) and abs(r["score"] - c["score"]) < 1e-9
                ok += same
                tot += 1
        print(f"check {ENC}: offset 0 + mean 0 + bit cap + masked obs reproduces final4's stored row {ok}/{tot}")
        return
    items = [(g, lv, k, s, sm[f"{ENC}|{k}|pooled"], False) for g in gids for lv in C.BUDGET_QPS for k in ks
             for s in seeds]
    if a.limit:
        items = items[:a.limit]
    print(f"{ENC} {a.split}: {len(gids)} GOPs, {len(items)} episodes", flush=True)
    t0 = time.time()
    with Pool(a.workers, initializer=_init) as p:
        rows = list(p.imap_unordered(episode, items, chunksize=2))
    os.makedirs(out, exist_ok=True)
    dest = f"{out}/bc_rows_{ENC}_{a.split}{'_' + a.tag if a.tag else ''}{'_limit' if a.limit else ''}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    with open(dest + ".part", "wb") as f:
        pickle.dump(rows, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(dest + ".part", dest)
    print(f"{ENC} {a.split}: {len(rows)} episodes, {time.time() - t0:.0f}s -> {dest}")


if __name__ == "__main__":
    main()
