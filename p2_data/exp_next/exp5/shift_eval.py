"""Experiment 5a: final4 + a fixed per-frame offset schedule, real encodes. Pre-registration:
exp_next/exp5/PREREG_SHIFT.md (REVISION 2: smooth real-valued shifts_smooth.json, added to final4's real-valued QP
before its rounding via env.res_float; arms pooled|perlevel x none|bit, + pooled:full as a reference).

R2's residual env (arm res, RC_RES_RANGE=6, final4 setting 1.0:6:1.0:2:3:4:1:1:1:0:3, rcwork_v1/<enc>_resh infos):
frame t gets round(final4's real-valued QP + shift_t), then the cap rule ("" none = resh behaviour, "bit" = budget
limits only, "full" = also final4's shape limits; RC_RES_RECAP semantics, set per episode). No learner.

  RC_CODEC=<enc> ... python exp_next/exp5/shift_eval.py --split fold [--shard i --nshards n] [--workers w]
  RC_CODEC=<enc> ... python exp_next/exp5/shift_eval.py --split val --variants pooled:bit      (selected only)
  RC_CODEC=<enc> ... python exp_next/exp5/shift_eval.py --check [--n 8]   offset 0 must reproduce final4 (all caps)
REVISION 3: arm perqbin:<cap> picks the vector shifts_qbin.json["enc|k|Q<bin>"] by the bin of final4's own frame-0
planning QP (decide() diag "level" at t = 0, causal; bins < 27 / 27-33 / 33-39 / >= 39 -> 24 / 30 / 36 / 42), read
after reset() in the worker. --tag names the output file (e.g. --tag qbin -> shift_rows_<enc>_<split>_qbin_0of1.pkl).
Out: results_v1/next/exp5/shift_rows_<enc>_<split>_<shard>of<n>.pkl (one row per encoded (episode, vector, recap),
     with the list of variants it stands for)
"""
import argparse
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, env as E, offrl, policies as P  # noqa: E402

assert C.RES and max(C.ACTIONS) == 6, "run with RC_ARM=res RC_RES_RANGE=6"
ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
ENC = C.CODEC
OUT = f"{ROOT}/results_v1/next/exp5"
KS = (0, 5)
QBIN_EDGES, QBIN_LEVELS = (27, 33, 39), (24, 30, 36, 42)
_G = {}


def _init():
    _G["infos"] = pickle.load(open(_G["ipath"], "rb"))
    qp = f"{OUT}/shifts_qbin.json"
    _G["qshifts"] = json.load(open(qp)) if os.path.exists(qp) else None


def episode(item):
    gid, lv, k, vec, recap, variants = item
    C.RES_RECAP = recap
    env = E.make_env({gid: _G["infos"][gid]}, k=k)
    env.force(gid, lv, k)
    env.reset()
    lv0 = float(env.ctrl_diag["level"])             # final4's frame-0 planning QP (causal)
    qb = None
    if isinstance(vec, str):
        assert vec == "qbin"
        qb = QBIN_LEVELS[int(np.searchsorted(QBIN_EDGES, lv0, side="right"))]
        vec = _G["qshifts"][f"{ENC}|{k}|Q{qb}"]
    env.res_float = np.asarray(vec, float)
    zero = C.ACTIONS.index(0)
    for t in range(C.GOP):
        _, _, done, _, res = env.step(zero)
    assert done
    return {"gid": gid, "clip": _G["infos"][gid]["gop"]["clip"], "level": lv, "k": k, "vec": list(vec),
            "recap": recap, "variants": variants, "f4_level0": lv0, "qbin": qb, "budget": env.budget, "bits": res["bits"], "psnr": res["psnr"],
            "score": res["score"], "static_score": res["static_score"], "use": res["use"],
            "over_pct": res["over_pct"], "qps": list(res["qps"]), "ctrl_qps": list(res["ctrl_qps"])}


def vectors(shifts, k, lv, variants):
    """{(vector tuple, cap rule): [variant names]} for one episode."""
    out = {}
    for v in variants:
        kind, cap = v.split(":")
        rc = {"none": "", "bit": "bit", "full": "full"}[cap]
        if kind == "perqbin":                       # vector chosen in the worker from final4's frame-0 level
            out.setdefault(("qbin", rc), []).append(v)
            continue
        assert kind in ("pooled", "perlevel"), v
        key = f"{ENC}|{k}|" + ("pooled" if kind == "pooled" else f"L{lv}")
        out.setdefault((tuple(shifts[key]), rc), []).append(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="fold", choices=("fold", "val", "test"))   # test: approved final pass only
    ap.add_argument("--variants", default="pooled:none,pooled:bit,perlevel:none,perlevel:bit,pooled:full")
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", 2)) - 1))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="smoke: only the first N items of this shard")
    ap.add_argument("--out", default=None, help="smoke: output directory")
    ap.add_argument("--tag", default="", help="output file tag (REVISION 3: qbin)")
    ap.add_argument("--ks", default="0,5", help="lookaheads to run (REVISION 4: 5)")
    a = ap.parse_args()
    out = a.out or OUT
    full = pickle.load(open(f"{RC}/{ENC}_resh/results_infos/infos.pkl", "rb"))
    fold = set(json.load(open(f"{ROOT}/exp_next/folds.json"))["train_select_clips"])
    if a.split in ("val", "test"):
        gids = sorted(g for g, x in full.items() if x["gop"]["split"] == a.split)
    else:
        gids = sorted(g for g, x in full.items() if x["gop"]["split"] == "train" and x["gop"]["clip"] in fold)
    infos = {g: offrl.slim(full[g]) for g in gids}
    tmp = os.environ.get("RC_TMP") or "/scratch1/aayushso/tmp"
    _G["ipath"] = P.save_infos_for_workers(infos, f"{tmp}/exp5a_{ENC}_infos_{os.getpid()}.pkl")
    if a.check:
        _init()
        rng = np.random.default_rng(0)
        ok = tot = 0
        for gid in rng.choice(gids, a.n, replace=False):
            for recap in ("", "bit", "full"):
                lv, k = int(rng.choice(C.BUDGET_QPS)), int(rng.choice(KS))
                r = episode((gid, lv, k, [0] * C.GOP, recap, ["zero"]))
                c = full[gid]["ctrl"][(lv, k)]
                same = list(r["qps"]) == list(c["qps"]) and int(r["bits"]) == int(c["bits"]) and \
                    abs(r["score"] - c["score"]) < 1e-9
                ok += same
                tot += 1
                print(gid, lv, f"k{k}", f"recap {recap}", "OK" if same else
                      f"MISMATCH score {c['score']:.4f} -> {r['score']:.4f}", flush=True)
        print(f"check {ENC}: offset 0 reproduces final4's stored row {ok}/{tot}")
        return
    shifts = json.load(open(f"{OUT}/shifts_smooth.json"))
    variants = a.variants.split(",")
    items = [(g, lv, k, vec if isinstance(vec, str) else list(vec), recap, vs) for g in gids for lv in C.BUDGET_QPS
             for k in [int(x) for x in a.ks.split(",")]
             for (vec, recap), vs in vectors(shifts, k, lv, variants).items()]
    items = items[a.shard::a.nshards]
    if a.limit:
        items = items[:a.limit]
    print(f"{ENC} {a.split}: {len(gids)} GOPs, {len(items)} encoded episodes in this shard", flush=True)
    t0 = time.time()
    with Pool(a.workers, initializer=_init) as p:
        rows = list(p.imap_unordered(episode, items, chunksize=2))
    os.makedirs(out, exist_ok=True)
    tag = f"{a.tag}_" if a.tag else ""
    dest = f"{out}/shift_rows_{ENC}_{a.split}_{tag}{a.shard}of{a.nshards}{'_limit' if a.limit else ''}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    with open(dest + ".part", "wb") as f:
        pickle.dump(rows, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(dest + ".part", dest)
    print(f"{ENC} {a.split} shard {a.shard}/{a.nshards}: {len(rows)} episodes, {time.time() - t0:.0f}s -> {dest}")


if __name__ == "__main__":
    main()
