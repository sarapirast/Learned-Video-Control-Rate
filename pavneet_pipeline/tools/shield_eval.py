"""Evaluate finished RL runs with a budget shield (rclib/policies.Shield). No training; never touches eval.pkl.

  python tools/shield_eval.py --run cql_ppo_k0_fixed_s0 --split val --grid 1.0:max:0.2:3,1.0:max:0.1:3
  grid item = margin:future:tol:w0 (tol and w0 optional, default 0 and 3)
  python tools/shield_eval.py --list runs_shield.txt          # line $SLURM_ARRAY_TASK_ID: "<run> <split> <grid>"

Writes $RC_WORK/results_rl/<run>/shield_<split>.pkl = {(margin, future, tol, w0): rows}; configs already there are
skipped. The bit model (slopes, calibration priors, I/P first-pass ratio) is fitted on TRAIN only and cached in
results_infos/shield_model.pkl.
Aayush, v1-data branch, 2026-11-04.
"""
import argparse
import os
import pickle
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, env as E, policies as P, runner  # noqa: E402
from rclib.runner import log  # noqa: E402


def fit_model(infos, srch, n_per=6, seed=0):
    """Bit model fitted on TRAIN only: slopes of log2(bits / fp) vs QP (I and P frames, from the search logs, which
    vary the QP), then calibration priors (median per-GOP ratio of real to predicted bits) and the I/P first-pass
    ratio."""
    rng = np.random.default_rng(seed)
    A = np.array(C.ACTIONS)
    xi, yi, xp, yp, ci, cp, ip = [], [], [], [], [], [], []
    for g, r in srch.items():
        x = infos.get(g)
        if x is None or x["gop"]["split"] != "train":
            continue
        fp = np.maximum(np.asarray(x["fp_bits"], float), 8)
        ip.append(fp[0] / fp[1:].mean())
        for b, e in r.items():
            logs = [l for lg in e["logs"] for l in lg] if "logs" in e else []
            for l in [logs[i] for i in rng.choice(len(logs), min(n_per, len(logs)), replace=False)] if logs else []:
                q = b + E.STATIC_OFF + A[l["acts"].astype(int)]
                lb = np.log2(np.maximum(np.asarray(l["bits"], float), 8) / fp)
                xi.append(q[0] - 30); yi.append(lb[0])
                xp.extend(q[1:] - 30); yp.extend(lb[1:])
    s_i = -1 / np.polyfit(xi, yi, 1)[0]
    s_p = -1 / np.polyfit(xp, yp, 1)[0]
    for x in infos.values():
        if x["gop"]["split"] != "train":
            continue
        fp = np.maximum(np.asarray(x["fp_bits"], float), 8)
        for b, st in x["static"].items():
            bits = np.asarray(st["bits"], float)
            q = b + E.STATIC_OFF
            ci.append(bits[0] / (fp[0] * 2 ** (-(q[0] - 30) / s_i)))
            cp.append(bits[1:].sum() / (fp[1:] * 2 ** (-(q[1:] - 30) / s_p)).sum())
    return {"slopes": (float(s_i), float(s_p)), "prior": (float(np.median(ci)), float(np.median(cp))),
            "ip_ratio": float(np.median(ip))}


def run_one(run, split, grid, limit=0):
    rdir = os.path.join(C.results_dir("rl"), run)
    with open(os.path.join(rdir, "eval.pkl"), "rb") as f:
        ev = pickle.load(f)
    a, base = ev["args"], ev["spec"]
    ipath = os.path.join(runner.Stages("infos").dir, "infos_slim.pkl")
    with open(ipath, "rb") as f:
        infos = pickle.load(f)
    mfile = os.path.join(runner.Stages("infos").dir, "shield_model.pkl")
    if os.path.exists(mfile):
        model = pickle.load(open(mfile, "rb"))
    else:
        model = fit_model(infos, runner.Stages("search").load("search_train"))
        pickle.dump(model, open(mfile, "wb"))
    log(f"shield model (train only): {model}")
    ids = sorted(g for g, x in infos.items() if x["gop"]["split"] == split)
    if limit:
        ids = ids[:limit]
    envkw = {"k": a["k"], "mode": a["mode"], "drop": tuple(x for x in a["drop"].split(",") if x),
             "prior": a["prior"], "extra": a.get("extra") or "", "k_sampler": None}
    out = os.path.join(rdir, f"shield_{split}{'_lim%d' % limit if limit else ''}.pkl")
    res = pickle.load(open(out, "rb")) if os.path.exists(out) else {}
    for g in grid:
        parts = g.split(":")
        m, fut, tol, w0 = parts + ["1.0", "max", "0", "3"][len(parts):]
        key = (float(m), fut, float(tol), float(w0))
        if key in res:
            log(f"{run} {split} {key}: done")
            continue
        spec = {"kind": "shield", "base": base, "margin": key[0], "future": fut, "tol": key[2], "w0": key[3], **model}
        t0 = time.time()
        rows = P.evaluate(spec, ipath, ids, desc=f"{run} {split} shield {g}", **envkw)
        res[key] = rows
        sc = np.mean([r["score"] for r in rows])
        log(f"{run} {split} shield {g}: score {sc:.2f} saving {np.mean([r['saving'] for r in rows]):.2f} "
            f"over {100 * np.mean([r['over'] for r in rows]):.1f}% mean over% {np.mean([r['over_pct'] for r in rows]):.2f} "
            f"fires/GOP {np.mean([r['shield_fires'] for r in rows]):.2f} ({time.time() - t0:.0f}s)")
        tmp = out + ".tmp"
        pickle.dump(res, open(tmp, "wb"))
        os.replace(tmp, out)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--split", default="val")
    ap.add_argument("--grid", default="1.0:max")
    ap.add_argument("--limit", type=int, default=0, help="first N GOPs only (smoke tests)")
    ap.add_argument("--list", help="file with lines '<run> <split> <grid>'; picks line $SLURM_ARRAY_TASK_ID")
    a = ap.parse_args()
    if a.list:
        line = open(a.list).read().splitlines()[int(os.environ["SLURM_ARRAY_TASK_ID"])].split()
        a.run, a.split, a.grid = line[0], line[1], line[2]
    run_one(a.run, a.split, a.grid.split(","), a.limit)


if __name__ == "__main__":
    main()
