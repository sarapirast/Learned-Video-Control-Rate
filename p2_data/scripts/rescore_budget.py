"""Rescore every stored result with a budget-aware score (P2, 2026-11-09). No encodes.

Why: the project score (repo-pavneet rclib/metrics.py: % bits saved at equal PSNR vs the GOP's constant-QP curve,
minus 2 per 1% over budget) does not penalise UNUSED budget. The residual RL learned to spend ~2/3 of the budget at
lower PSNR and scored higher (results_v1/res_offsets_x264.md). The task is the best quality within the budget, so:

  saving_B = 100 x (1 - max(bits, B) / bits_CQP(PSNR))      unused budget counts as spent (wasted)
  score_B  = saving_B - 2 x %over                           (same over penalty as the project score)
  dPSNR@B  = PSNR - PSNR_CQP(B)                             quality vs the constant QP that spends exactly B (dB)
  use      = bits / B
bits_CQP and PSNR_CQP use the GOP's constant-QP curve with the project metric's own interpolation and linear
extrapolation (metrics.py is imported from repo-pavneet, so the old score is reproduced exactly; checked per source).

Sources (per codec):
  lf (leak-free budgets, P1 settings; curves/budgets from rcwork_v1/<codec>_lf infos):
    search          rcwork_v1/<codec>_lf/results_search/search_{val,test}.pkl (best plan)
    P2 baselines    results_v1/baselines_v1.parquet (incl. online_controller_v1 = controller final v1)
    controller v2   results_v1/controller_real/final2_<codec>_*.parquet (the residual's base)
    residual RL     rcwork_v1/<codec>_res/results_rl/res_k*_s*/eval.pkl
  orig / dec (Pavneet's budgets and settings; curves/budgets from that arm's infos):
    search          rcwork_v1/<codec>_<arm>/results_search/search_{val,test}.pkl
    learned         rcwork_v1/<codec>_<arm>/results_rl/<method>_k<k>_fixed[_variant]_s<seed>/eval.pkl
Flat (grayscale) GOPs are excluded everywhere (data/v1/320x180/rd/flat_gops.csv). Seeds pooled.

  /scratch1/aayushso/envs/ee599/bin/python -I scripts/rescore_budget.py [x264 x265]
Out: results_v1/rescore_budget/rescore_<codec>.md, summary_<codec>.csv, episodes_<codec>.parquet
"""
import glob
import importlib.util
import os
import pickle
import re
import sys

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
OUT = f"{ROOT}/results_v1/rescore_budget"
CTRL2 = "0.97:3.0:0.3:2.0:3.0:4.0:0.0:1.0:0.0:0.0"

_spec = importlib.util.spec_from_file_location("pv_metrics", f"{ROOT}/repo-pavneet/rclib/metrics.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def psnr_at_bits(curve, B):
    """Constant-QP PSNR at exactly B bits: inverse of metrics._interp_logbits (piecewise linear, linear extrapolation)."""
    p = np.asarray(curve["psnr"], float)
    lb = np.log(np.asarray(curve["bits"], float))
    o = np.argsort(lb)                     # sorted by bits (a few curves have tiny non-monotonic steps)
    p, lb = p[o], lb[o]
    x = np.log(B)
    if x < lb[0]:
        return p[0] + (x - lb[0]) * (p[1] - p[0]) / max(lb[1] - lb[0], 1e-9)
    if x > lb[-1]:
        return p[-1] + (x - lb[-1]) * (p[-1] - p[-2]) / max(lb[-1] - lb[-2], 1e-9)
    return float(np.interp(x, lb, p))


def row(source, arm, method, k, seed, split, gid, info, level, bits, psnr, stored):
    curve, B = info["curve"], info["budget"][level]
    need = float(np.exp(M._interp_logbits(curve, psnr)))
    over = float(M.overshoot(bits, B))
    return {"source": source, "arm": arm, "method": method, "k": k, "seed": seed, "split": split, "gid": gid,
            "clip": info["gop"]["clip"], "cls": info["gop"]["label"], "level": level,
            "score": float(M.score(bits, psnr, curve, B)), "stored_score": stored,
            "score_B": 100 * (1 - max(bits, B) / need) - M.OVER_PENALTY * over,
            "dpsnr_B": psnr - psnr_at_bits(curve, B), "use": bits / B, "over": over > 0}


def rl_runs(work, source, arm, infos, flat):
    rows = []
    for p in sorted(glob.glob(f"{work}/results_rl/*/eval.pkl")):
        m = re.match(r"(.+)_k(\d+)_fixed(?:_(.+))?_s(\d+)$", os.path.basename(os.path.dirname(p)))
        if not m:
            continue
        method = m.group(1) + (f"_{m.group(3)}" if m.group(3) else "")
        d = pickle.load(open(p, "rb"))
        for key, eps in d["res"].items():
            _, k, split = key
            for e in eps:
                if e["gid"] in flat or e["gid"] not in infos:
                    continue
                rows.append(row(source, arm, method, k, int(m.group(4)), split, e["gid"], infos[e["gid"]],
                                e["budget"], e["bits"], e["psnr"], e["score"]))
    return rows


def search(work, arm, infos, flat):
    rows = []
    for split in ("val", "test"):
        p = f"{work}/results_search/search_{split}.pkl"
        if not os.path.exists(p):
            continue
        for gid, v in pickle.load(open(p, "rb")).items():
            if gid in flat or gid not in infos:
                continue
            for lv, r in v.items():
                rows.append(row("search", arm, "search", 29, 0, split, gid, infos[gid], lv, r["total_bits"],
                                r["psnr"], r["best_score"]))
    return rows


def parquet_rows(df, source, method_col, infos, key, flat):
    rows = []
    for r in df.itertuples(index=False):
        gid = key.get((r.clip_id, int(r.gop)))
        if gid is None or gid in flat:
            continue
        rows.append(row(source, "lf", getattr(r, method_col) if method_col else source, int(r.k), 0, r.split, gid,
                        infos[gid], int(r.level_q0), float(r.bits), float(r.psnr_yuv), float(r.score)))
    return rows


def summarize(d):
    g = d.groupby(["arm", "source", "method", "k", "split"])
    s = g.agg(n=("score", "size"), score=("score", "mean"), score_B=("score_B", "mean"),
              dPSNR_B=("dpsnr_B", "mean"), use=("use", "mean"), use_p10=("use", lambda x: x.quantile(.1)),
              pct_over=("over", lambda x: 100 * x.mean()),
              max_dscore=("dscore", lambda x: x.abs().max())).reset_index()
    return s


def md(df):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        L.append("| " + " | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(L)


def main(codecs):
    os.makedirs(OUT, exist_ok=True)
    flatdf = pd.read_csv(f"{ROOT}/data/v1/320x180/rd/flat_gops.csv")
    flat = set(flatdf.gid[flatdf.flat])
    for codec in codecs:
        rows = []
        lf = pickle.load(open(f"{RC}/{codec}_lf/results_infos/infos.pkl", "rb"))
        key = {(x["gop"]["clip"], int(x["gop"]["v1_gop"])): g for g, x in lf.items()}
        rows += search(f"{RC}/{codec}_lf", "lf", lf, flat)
        b = pd.read_parquet(f"{ROOT}/results_v1/baselines_v1.parquet").query("encoder == @codec")
        rows += parquet_rows(b, "baseline", "method", lf, key, flat)
        c2 = pd.concat([pd.read_parquet(p) for p in glob.glob(f"{ROOT}/results_v1/controller_real/final2_{codec}_*.parquet")])
        c2 = c2[c2.setting == CTRL2]
        c2 = c2.assign(split=c2.clip_id.map({x["gop"]["clip"]: x["gop"]["split"] for x in lf.values()}))
        rows += parquet_rows(c2, "controller_v2", None, lf, key, flat)
        if os.path.isdir(f"{RC}/{codec}_res"):
            rows += rl_runs(f"{RC}/{codec}_res", "residual_rl", "lf", lf, flat)
        for arm in ("orig", "dec"):
            work = f"{RC}/{codec}_{arm}"
            if not os.path.isdir(work):
                continue
            inf = pickle.load(open(f"{work}/results_infos/infos.pkl", "rb"))
            rows += search(work, arm, inf, flat)
            rows += rl_runs(work, "learned", arm, inf, flat)
        d = pd.DataFrame(rows)
        d["dscore"] = d.score - d.stored_score
        d.to_parquet(f"{OUT}/episodes_{codec}.parquet", index=False)
        s = summarize(d)
        s.to_csv(f"{OUT}/summary_{codec}.csv", index=False)

        L = [f"# Budget-aware rescoring of all stored results ({codec})", "",
             "Generated by `scripts/rescore_budget.py` (definitions in its docstring). score = the project score "
             "(recomputed; max_dscore = max |recomputed - stored|, should be ~0); score_B = same but unused budget "
             "counts as spent; dPSNR_B = PSNR minus the constant-QP PSNR at exactly the budget (dB); use = bits / "
             "budget (mean, and 10th percentile). Flat GOPs excluded; seeds pooled. Arms: lf = leak-free budgets "
             "(4 levels, P1 settings); orig = Pavneet's budget (the GOP's own constant-QP spend; leaky); dec = orig "
             "x U(0.8, 1.25). Scores are only comparable within an arm.", ""]
        for arm in ("lf", "orig", "dec"):
            x = s[(s.arm == arm) & (s.split == "test")].drop(columns=["arm", "split"])
            if x.empty:
                continue
            x = x.sort_values(["source", "method", "k"])
            L += [f"## {arm}, test", "", md(x), ""]
            best = x.sort_values("score_B", ascending=False).head(8)[["source", "method", "k", "score", "score_B",
                                                                       "dPSNR_B", "use", "pct_over"]]
            L += [f"Top 8 by score_B ({arm}, test):", "", md(best), ""]
        open(f"{OUT}/rescore_{codec}.md", "w").write("\n".join(L) + "\n")
        print(f"{codec}: {len(d)} rows; max |recomputed - stored score| by source:")
        print(d.groupby(["arm", "source"]).dscore.apply(lambda x: x.abs().max()).to_string())


if __name__ == "__main__":
    main(sys.argv[1:] or ["x264", "x265"])
