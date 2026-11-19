"""test2 parity gate (exp_next/test2/PLAN.md section 5). The 3 parity clips (v1 TEST clips ed_s05, NewsClip_360P-1b1c,
park_joy) went through the whole test2 path; every product must equal v1's stored one. Stages not run yet are reported
as "not yet" (the gate passes only when every stage is OK).

  /scratch1/aayushso/envs/ee599/bin/python -I exp_next/test2/parity.py [--stage name ...]
Stages: decode, cuts, rd, fp, fpstats, flat, budgets, prev, ctrl, infos, abr, shift (episode-level R3 / CQL->PPO parity
is printed by eval_t2.py --split parity). Out: prints, and appends a dated summary to results_v1/test2/parity.md.
"""
import argparse
import glob
import os
import pickle
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
V1 = f"{ROOT}/data/v1/320x180"
T2 = f"{ROOT}/data/t2/320x180"
CTRL = f"{ROOT}/results_v1/controller_real"
OUT = f"{ROOT}/results_v1/test2"
PY = "/scratch1/aayushso/envs/ee599/bin/python"
PARITY = ("ed_s05", "NewsClip_360P-1b1c", "park_joy")
ENCS = ("x264", "x265")


def same(a, b, path=""):
    """Deep equality for nested dict / list / numpy / scalars; returns the first differing path or None."""
    if isinstance(a, dict):
        if not isinstance(b, dict) or set(a) != set(b):
            return f"{path}: keys {sorted(map(str, set(a) ^ set(b)))[:5]}"
        for k in a:
            d = same(a[k], b[k], f"{path}/{k}")
            if d:
                return d
        return None
    if isinstance(a, (list, tuple, np.ndarray)) or isinstance(b, (list, tuple, np.ndarray)):
        x, y = np.asarray(a), np.asarray(b)
        if x.shape != y.shape:
            return f"{path}: shape {x.shape} vs {y.shape}"
        if x.dtype.kind in "fc" or y.dtype.kind in "fc":
            return None if np.allclose(x, y, rtol=0, atol=1e-9, equal_nan=True) else f"{path}: values"
        if x.dtype == object:
            for i, (p, q) in enumerate(zip(x.ravel(), y.ravel())):
                d = same(p, q, f"{path}[{i}]")
                if d:
                    return d
            return None
        return None if np.array_equal(x, y) else f"{path}: values"
    if isinstance(a, float) or isinstance(b, float):
        try:
            return None if (np.isnan(a) and np.isnan(b)) or abs(a - b) <= 1e-9 else f"{path}: {a} vs {b}"
        except TypeError:
            return f"{path}: {a!r} vs {b!r}"
    return None if a == b else f"{path}: {a!r} vs {b!r}"


def frame_cmp(t, v, key, skip=("split",)):
    t = t[t.clip_id.isin(PARITY)]
    v = v[v.clip_id.isin(PARITY)]
    if not len(t):
        return None
    cols = [c for c in v.columns if c not in skip]
    if len(t) != len(v):
        return f"rows {len(t)} vs {len(v)}"
    t = t.sort_values(key).reset_index(drop=True)[cols]
    v = v.sort_values(key).reset_index(drop=True)[cols]
    for c in cols:
        d = same(t[c].tolist(), v[c].tolist(), c)
        if d:
            return d
    return f"OK ({len(t)} rows)"


def stage(name):
    f = globals()[f"st_{name}"]
    try:
        r = f()
    except FileNotFoundError as e:
        r = f"not yet ({os.path.basename(str(e.filename or e))})"
    return r or "not yet"


def st_decode():
    t, v = pd.read_csv(f"{T2}/manifest.csv"), pd.read_csv(f"{V1}/manifest.csv")
    t, v = t[t.clip_id.isin(PARITY)], v[v.clip_id.isin(PARITY)]
    if len(t) < len(PARITY):
        return None
    m = t.merge(v, on="clip_id", suffixes=("", "_v1"))
    bad = [c for c in ("md5", "fps", "n_frames", "width", "height", "crop", "filter_chain") if
           (m[c].astype(str) != m[f"{c}_v1"].astype(str)).any()]
    return f"MISMATCH {bad}" if bad else f"OK (y4m md5 identical, {len(m)} clips)"


def st_cuts():
    return frame_cmp(pd.read_csv(f"{T2}/gops.csv"), pd.read_csv(f"{V1}/gops.csv"), ["clip_id", "gop"])


def st_rd():
    t = pd.read_parquet(f"{T2}/rd/rd_native.parquet")
    v = pd.read_parquet(f"{V1}/rd/rd_native.parquet")
    r1 = frame_cmp(t, v, ["encoder", "clip_id", "gop", "qp"])
    t = pd.read_parquet(f"{T2}/rd/rd_frames.parquet", filters=[("clip_id", "in", list(PARITY))])
    v = pd.read_parquet(f"{V1}/rd/rd_frames.parquet", filters=[("clip_id", "in", list(PARITY))])
    r2 = frame_cmp(t, v, ["encoder", "kind", "qp", "clip_id", "gop", "frame"])
    return f"rd_native {r1}; rd_frames {r2}"


def st_fp():
    return frame_cmp(pd.read_parquet(f"{T2}/features/fp_bits.parquet"),
                     pd.read_parquet(f"{V1}/features/fp_bits.parquet"), ["encoder", "fp_qp", "clip_id", "gop", "frame"])


def st_fpstats():
    return frame_cmp(pd.read_parquet(f"{T2}/features/fp_stats.parquet"),
                     pd.read_parquet(f"{V1}/features/fp_stats.parquet"), ["encoder", "fp_qp", "clip_id", "gop", "frame"])


def st_flat():
    return frame_cmp(pd.read_csv(f"{T2}/rd/flat_gops.csv"), pd.read_csv(f"{V1}/rd/flat_gops.csv"), ["clip_id", "gop"])


def _run(args):
    p = subprocess.run([PY, "-I", *args], capture_output=True, text=True)
    return (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else f"exit {p.returncode}"


def st_budgets():
    if not os.path.exists(f"{T2}/budgets.csv"):
        return None
    return _run([f"{ROOT}/exp_next/test2/budgets_t2.py", "--check"])


def st_prev():
    if not all(os.path.exists(f"{T2}/budgets_prev_{e}.csv") for e in ENCS):
        return None
    return " | ".join(_run([f"{ROOT}/exp_next/test2/base_prev_t2.py", e, "--check"]) for e in ENCS)


def st_ctrl():
    out = []
    for tag in ("final4", "final3"):
        for e in ENCS:
            tf = glob.glob(f"{CTRL}/t2{tag}_{e}_parity_*.parquet")
            if not tf:
                out.append(f"{tag} {e} not yet")
                continue
            t = pd.concat(pd.read_parquet(p) for p in tf)
            v = pd.concat(pd.read_parquet(p) for p in glob.glob(f"{CTRL}/{tag}_{e}_test_*.parquet"))
            v = v[v.setting.isin(set(t.setting))]
            r = frame_cmp(t, v, ["clip_id", "gop", "level_q0", "k", "setting"], skip=("split", "secs", "seconds"))
            out.append(f"{tag} {e} {r}")
    return "; ".join(out)


def st_infos():
    out = []
    for e in ENCS:
        for arm, name in (("orig", "infos"), ("lf", "infos"), ("resh", "infos"), ("lfqp", "infos_learn")):
            tp = f"/scratch1/aayushso/rcwork_t2/{e}_{arm}/results_infos/{name}.pkl"
            vp = f"/scratch1/aayushso/rcwork_v1/{e}_{arm}/results_infos/{name}.pkl"
            if not os.path.exists(tp):
                out.append(f"{e}_{arm} not yet")
                continue
            t, v = pickle.load(open(tp, "rb")), pickle.load(open(vp, "rb"))
            gids = [g for g, x in t.items() if x["gop"]["split"] == "parity"]
            bad = None
            for g in gids:
                a = {k: x for k, x in t[g].items()}
                b = {k: x for k, x in v[g].items()}
                if arm == "lfqp":       # no search on test2: the search start (static) is absent by design
                    a.pop("static", None), b.pop("static", None)
                a["gop"] = {k: x for k, x in a["gop"].items() if k != "split"}
                b["gop"] = {k: x for k, x in b["gop"].items() if k != "split"}
                bad = same(a, b, g)
                if bad:
                    break
            out.append(f"{e}_{arm} {'MISMATCH ' + bad if bad else f'OK ({len(gids)} GOPs)'}")
    return "; ".join(out)


def st_abr():
    out = []
    for e in ENCS:
        tf = glob.glob(f"{OUT}/abr/rows_{e}_parity_*.parquet")
        if not tf:
            out.append(f"{e} not yet")
            continue
        t = pd.concat(pd.read_parquet(p) for p in tf)
        v = pd.read_parquet(f"{ROOT}/results_v1/next/exp10/rows_{e}_test_0of1.parquet")
        v = v[v.margin.isin(set(t.margin))]
        out.append(f"{e} " + str(frame_cmp(t, v, ["clip_id", "gop", "level_q0", "k", "margin"], skip=("split",))))
    return "; ".join(out)


def st_shift():
    tf = glob.glob(f"{OUT}/shift_rows_x265_parity_*.pkl")
    if not tf:
        return None
    t = [r for p in tf for r in pickle.load(open(p, "rb"))]
    v = pickle.load(open(f"{ROOT}/results_v1/next/exp5/shift_rows_x265_test_qbin_k5_0of1.pkl", "rb"))
    key = lambda r: (r["gid"], r["budget"], r.get("k"))
    vd = {key(r): r for r in v}
    ok = sum(1 for r in t if key(r) in vd and list(r["qps"]) == list(vd[key(r)]["qps"])
             and abs(r["score"] - vd[key(r)]["score"]) < 1e-9)
    return f"{'OK' if ok == len(t) else 'MISMATCH'} ({ok}/{len(t)} episodes equal)"


STAGES = ("decode", "cuts", "rd", "fp", "fpstats", "flat", "budgets", "prev", "ctrl", "infos", "abr", "shift")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", nargs="*", default=list(STAGES))
    a = ap.parse_args()
    lines = [f"## parity {time.strftime('%Y-%m-%d %H:%M')}", ""]
    for s in a.stage:
        r = stage(s)
        lines.append(f"- {s}: {r}")
        print(f"{s:8s} {r}", flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/parity.md", "a") as f:
        f.write("\n".join(lines) + "\n\n")


if __name__ == "__main__":
    main()
