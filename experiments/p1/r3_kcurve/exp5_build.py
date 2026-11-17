"""P1 COPY of p2_data/exp_next/exp5/build.py (origin/main 046d1f9), patched only where marked "P1 copy".
"""
"""Experiment 5, step 1: replay final4 (R2 residual env) along kept search plans at budget S and build the BC dataset.
See exp_next/exp5/PREREG.md. Run in the res job env with RC_RES_RANGE=6 (R2's action range):
  RC_ARM=res RC_RES_RANGE=6 RC_CODEC=<enc> RC_WORK=.../<enc>_resh ... python exp_next/exp5/build.py [--workers n]
  ... python exp_next/exp5/build.py --check [--n 20]       round-trip check (a): real encodes of final4 + labels
Out: results_v1/next/exp5/data_<enc>_k<k>.npz (obs float16, label int8, delta float32, plan index), plans_<enc>.pkl
     (one row per kept plan: gid, level, S, delta, mean P QP), labels_<enc>.md (check (b) and clipping)
--v2 (Exp 5b, PREREG_BC.md REVISION 2): observation built with env drop groups "level" + "history" (o[2], o[5..8]
     zeroed, verified on the saved array), plus q_real (final4's real-valued QP) and the BC class target
     label2 = clip(plan QP - round(q_real + mean[t]), -6, 6) with mean = shifts_smooth.json "<enc>|<k>|pooled" (Python
     round, as env.step with res_float) -> data_v2_<enc>_k<k>.npz, plans_v2_<enc>.pkl, labels_v2_<enc>.md
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

sys.path.insert(0, "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/pavneet_pipeline")   # P1 copy: p1-fast-backend rclib
from rclib import config as C, env as E, offrl  # noqa: E402

assert C.RES and max(C.ACTIONS) == 6, "run with RC_ARM=res RC_RES_RANGE=6"
ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
ENC = C.CODEC
OUT = f"{ROOT}/results_v1/next/exp5"
RAMP = np.array([-6.0] + list(np.linspace(-3, 3, 29)))        # lfq search start pattern (rclib/config.py RAMP)
SACT = np.arange(-5, 6)                                       # search actions (lfq search keeps +-5)
KS, KEEP, TOL = tuple(int(x) for x in os.environ["EXP5_KS"].split(",")), 50, 0.15   # P1 copy: k list from EXP5_KS
V2_DROP = ("level", "history")          # o[2] and o[5..8]
V2_ZERO = [2, 5, 6, 7, 8]
_G = {"v2": False}


def plan_qps(base, acts):
    return np.clip(np.round(base + RAMP + SACT[np.asarray(acts, int)]), 11, 51).astype(int)


def select(gid, info, entries):
    """Kept plans of one GOP: list of (level, qps, bits, S, psnr, delta)."""
    pts_b, pts_p, plans = [], [], []
    for lv, e in entries.items():
        seen = set()
        for run in e["logs"]:
            for r in run:
                key = bytes(np.asarray(r["acts"], np.int8))
                if key in seen:
                    continue
                seen.add(key)
                plans.append((lv, plan_qps(e["base_q"], r["acts"]), np.asarray(r["bits"], int), int(r["total_bits"]),
                              float(r["psnr"])))
                pts_b.append(r["total_bits"])
                pts_p.append(r["psnr"])
    pts_b += list(info["curve"]["bits"])
    pts_p += list(info["curve"]["psnr"])
    o = np.argsort(pts_b)
    xb, yp = np.asarray(pts_b, float)[o], np.maximum.accumulate(np.asarray(pts_p, float)[o])
    out = []
    for lv in entries:
        B = info["budget"][lv]
        cand = []
        for (l, q, b, S, p) in plans:
            if l != lv or abs(S / B - 1) > TOL:
                continue
            env_p = yp[np.searchsorted(xb, S, side="right") - 1]
            cand.append((l, q, b, S, p, p - env_p))
        cand.sort(key=lambda x: -x[5])
        out += cand[:KEEP]
    return out


def replay(info, gid, lv, qps, bits, S, k):
    v2 = _G["v2"]
    env = E.make_env({gid: info}, k=k, extra="f4", drop=V2_DROP if v2 else ())
    mean = _G["mean"][k] if v2 else None
    env.force(gid, lv, k)
    env.reset()
    env.budget = float(S)
    obs, lab, lev = [], [], []
    zero = C.ACTIONS.index(0)
    for t in range(C.GOP):
        env.t = t
        env.qps = [int(x) for x in qps[:t]]
        env.bits = [int(x) for x in bits[:t]]
        env.acts = list(env.acts[:t])
        o = env._obs()
        raw = int(qps[t]) - int(env.q_ctrl)
        a = int(np.clip(raw, -6, 6))
        obs.append(o.astype(np.float16))
        if v2:
            qr = float(env.ctrl_diag["q_real"])
            raw2 = int(qps[t]) - round(qr + float(mean[t]))
            lab.append((raw, a, raw2, int(np.clip(raw2, -6, 6)), qr))
        else:
            lab.append((raw, a))
        lev.append(env.ctrl_diag.get("level", np.nan))
        env.acts.append(C.ACTIONS.index(a) if a in C.ACTIONS else zero)
    return np.stack(obs), lab, lev


def work(gid):
    info, entries = _G["infos"][gid], _G["search"][gid]
    res = {k: [] for k in KS}
    meta = []
    for (lv, q, b, S, p, d) in select(gid, info, entries):
        pid = len(meta)
        meta.append({"gid": gid, "level": lv, "S": S, "use": S / info["budget"][lv], "psnr": p, "delta": d,
                     "meanP": float(q[1:].mean()), "pid": pid})
        for k in KS:
            o, lab, lev = replay(info, gid, lv, q, b, S, k)
            res[k].append((pid, o, lab, lev))
    return gid, meta, res


def load():
    full = pickle.load(open(f"{RC}/{ENC}_resh/results_infos/infos.pkl", "rb"))
    fold = set(json.load(open(f"{ROOT}/exp_next/folds.json"))["train_select_clips"])
    flat = pd.read_csv(f"{ROOT}/data/v1/320x180/rd/flat_gops.csv")
    flat = set(flat.loc[flat.flat, "gid"])
    s = pickle.load(open(f"{RC}/{ENC}_lfq/results_search/search_train.pkl", "rb"))
    gids = sorted(g for g in s if g in full and full[g]["gop"]["split"] == "train" and g not in flat
                  and full[g]["gop"]["clip"] not in fold)
    _G["infos"] = {g: offrl.slim(full[g]) for g in gids}
    _G["search"] = {g: s[g] for g in gids}
    return gids


def check(n):
    """(a) Round trip: execute final4 + clipped labels with real encodes; logged QPs reproduced on >= 95% of frames."""
    gids = load()
    rng = np.random.default_rng(0)
    tot = same = clipped_mismatch = bits_ok = 0
    for gid in rng.choice(gids, n, replace=False):
        info = _G["infos"][gid]
        kept = select(gid, info, _G["search"][gid])
        lv, q, b, S, p, d = kept[rng.integers(len(kept))]
        k = KS[rng.integers(len(KS))]
        _, lab, _ = replay(info, gid, lv, q, b, S, k)
        env = E.make_env({gid: info}, k=k, extra="f4")
        env.force(gid, lv, k)
        env.reset()
        env.budget = float(S)
        for t in range(C.GOP):
            env._obs()                                    # refresh q_ctrl at the real state
            env.step(C.ACTIONS.index(lab[t][1]))
        got = np.array(env.qps)
        m = got == q
        tot += C.GOP
        same += int(m.sum())
        clipped_mismatch += int(sum((not mm) and lab[t][0] != lab[t][1] for t, mm in enumerate(m)))
        bits_ok += int(list(env.bits) == [int(x) for x in b])
        print(gid, lv, f"k{k}", f"QPs reproduced {int(m.sum())}/30", "bits identical" if list(env.bits) == list(b)
              else "bits differ")
        if not m.all():
            t0 = int(np.argmin(m))
            print(f"    first mismatch at frame {t0}: logged QP {q[t0]}, executed {got[t0]}, raw label {lab[t0][0]} "
                  f"(clipped to {lab[t0][1]}); raw labels frames 0-5 {[l[0] for l in lab[:6]]}")
    print(f"check (a) {ENC}: {same}/{tot} frames reproduced ({100 * same / tot:.1f}%; need >= 95%); mismatches from "
          f"label clipping {clipped_mismatch}; plans with identical bits {bits_ok}/{n}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", 2)) - 1))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0, help="smoke: only the first N GOPs")
    ap.add_argument("--out", default=None, help="smoke: output directory instead of results_v1/next/exp5")
    ap.add_argument("--v2", action="store_true", help="Exp 5b BC dataset (masked obs, q_real, class target)")
    a = ap.parse_args()
    global OUT
    OUT = a.out or OUT
    tag = "_v2" if a.v2 else ""
    if a.v2:
        sm = json.load(open(os.environ["RC_SHIFTS"]))   # P1 copy
        _G["v2"], _G["mean"] = True, {k: np.asarray(sm[f"{ENC}|{k}|pooled"], float) for k in KS}
        for f in (f"{OUT}/plans_v2_{ENC}.pkl", *[f"{OUT}/data_v2_{ENC}_k{k}.npz" for k in KS]):
            assert not os.path.exists(f), f"{f} exists; never overwrite"
    os.makedirs(OUT, exist_ok=True)
    if a.check:
        return check(a.n)
    gids = load()
    if a.limit:
        gids = gids[:a.limit]
    t0 = time.time()
    metas, data = [], {k: [] for k in KS}
    with Pool(a.workers, initializer=None) as p:          # fork: workers inherit _G (incl. v2 / mean)
        for i, (gid, meta, res) in enumerate(p.imap(work, gids, chunksize=2)):   # P1 copy: deterministic row order (was imap_unordered)
            off = sum(len(m) for m in metas)
            for m in meta:
                m["pid"] += off
            metas.append(meta)
            for k in KS:
                data[k] += [(pid + off, o, lab, lev) for pid, o, lab, lev in res[k]]
            if i % 50 == 0:
                print(f"{i}/{len(gids)} GOPs, {time.time() - t0:.0f}s", flush=True)
    plans = pd.DataFrame([m for ms in metas for m in ms])
    plans.to_pickle(f"{OUT}/plans{tag}_{ENC}.pkl")                  # the job env (envs/rc) has no parquet engine
    L = [f"# Exp 5 dataset{' v2 (Exp 5b)' if a.v2 else ''}, {ENC} (exp_next/exp5/build.py{' --v2' if a.v2 else ''})", "",
         f"GOPs {len(gids)}; kept plans {len(plans)} (max {KEEP} per (GOP, level), |S/B - 1| <= {TOL}); "
         f"plans per (GOP, level): median {plans.groupby(['gid', 'level']).size().median():.0f}.", ""]
    for k in KS:
        rows = sorted(data[k], key=lambda x: x[0])
        obs = np.concatenate([r[1] for r in rows])
        raw = np.array([l[0] for r in rows for l in r[2]], int)
        lab = np.array([l[1] for r in rows for l in r[2]], np.int8)
        pid = np.repeat([r[0] for r in rows], C.GOP).astype(np.int32)
        lev = np.array([v for r in rows for v in r[3]], np.float32)
        delta = plans.set_index("pid").delta.reindex(pid).to_numpy(np.float32)
        extra = {}
        if a.v2:
            raw2 = np.array([l[2] for r in rows for l in r[2]], int)
            extra = {"label2": np.array([l[3] for r in rows for l in r[2]], np.int8), "raw2": raw2.astype(np.int16),
                     "q_real": np.array([l[4] for r in rows for l in r[2]], np.float32)}
            nz = {c: int(np.count_nonzero(obs[:, c])) for c in V2_ZERO}
            assert not any(nz.values()), nz
            L += [f"## k = {k}: v2 checks (measured on the saved array)", "",
                  f"Nonzero entries in obs columns {V2_ZERO}: {nz} (of {len(obs)} rows) -> o[2] and o[5..8] zeroed.",
                  f"label2 (class target vs round(q_real + mean[t])): clipped (|raw2| > 6) "
                  f"{100 * np.mean(np.abs(raw2) > 6):.2f}%; = 0 {100 * np.mean(extra['label2'] == 0):.1f}%; "
                  f"label2 differs from label (expected: mean[t] != 0, rounding of q_real) on {100 * np.mean(extra['label2'] != lab):.1f}% of rows.", "",
                  "mean label2 by frame index: " + " ".join(
                      f"{v:+.2f}" for v in pd.Series(extra["label2"]).groupby(np.tile(np.arange(C.GOP), len(rows))).mean()),
                  ""]
        np.savez(f"{OUT}/data{tag}_{ENC}_k{k}.npz", obs=obs, label=lab, raw=raw.astype(np.int16), pid=pid, delta=delta,
                 level=lev, t=np.tile(np.arange(C.GOP), len(rows)).astype(np.int8), **extra)
        t = np.tile(np.arange(C.GOP), len(rows))
        by = pd.DataFrame({"t": t, "raw": raw}).groupby("t").raw.agg(["mean", "std"])
        L += [f"## k = {k}", "", f"rows {len(lab)}; clipped labels (|raw| > 6): {100 * np.mean(np.abs(raw) > 6):.2f}%; "
              f"label = 0: {100 * np.mean(lab == 0):.1f}%", "",
              "Check (b): label (raw, before clipping) by frame index:", "", by.round(3).T.to_markdown(), "",
              f"max |mean| over frame indices: {by['mean'].abs().max():.3f} QP (report before training if > 0.5)", ""]
    open(f"{OUT}/labels{tag}_{ENC}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
