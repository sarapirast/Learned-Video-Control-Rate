"""Experiment 1, steps 1-5 and 7: score decomposition A / E / P, spend-error statistics, allocation headroom, local
R-D slope and the metric's optimal over-budget rate, level-24 hole. No encodes. See exp_next/exp1/PREREG.md.

Per episode (rclib/metrics.py interpolation; lfq infos_learn.pkl curves and budgets, flat GOPs excluded):
  rho = bits / B;  A = PSNR - PSNR_cq(bits);  E = PSNR_cq(bits) - PSNR_cq(B);  P = 0.17 x max(0, 100 (rho - 1))
  check: score = A + E - P (1e-6).
Sources: final4 / final3 per-episode rows (results_v1/controller_real/<tag>_<enc>_<split>_*.parquet); learners
(results_v1/lfq_compare_<enc>_final4.csv: bits = use x B, PSNR = dPSNR_B + PSNR_cq(B)); search best plan
(rcwork_v1/<enc>_lfq/results_search/search_<split>.pkl); ABR+VBV (results_v1/baselines_v1.parquet, abr_vbv rows).
Splits: val (primary) and train (final4 / final3 / search only). Test is not read.

  python -I exp_next/exp1/decompose.py
Out: results_v1/next/exp1/decomposition_<enc>.md, episodes_<enc>.parquet, headroom.md
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import metrics  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
OUT = f"{ROOT}/results_v1/next/exp1"
PEN = metrics.OVER_PENALTY_DB
LEARNERS = ("cql_ppo@prev", "cql_ppo_st180k@prev", "cql_ppo_st540k@prev", "bc@prev", "res@hist",
            "res_st180k@hist", "res_lv36-42@hist")
SPLITS = ("train", "val")
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    lo, hi = np.percentile(ms, 2.5), np.percentile(ms, 97.5)
    return f"{d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]" + (" *" if lo > 0 or hi < 0 else "")


def pcq(curve, bits):
    return float(metrics.psnr_at_bits(curve, bits))


def decomp(rows, infos):
    """rows: DataFrame with gid, level, bits, psnr (+ any other columns). Adds rho, A, E, P, score."""
    A, E, P, S, R = [], [], [], [], []
    for g, lv, b, p in zip(rows.gid, rows.level, rows.bits, rows.psnr):
        cv, B = infos[g]["curve"], infos[g]["budget"][int(lv)]
        a = p - pcq(cv, b)
        e = pcq(cv, b) - pcq(cv, B)
        pe = PEN * max(0.0, 100.0 * (b / B - 1.0))
        A.append(a), E.append(e), P.append(pe), R.append(b / B)
        S.append(float(metrics.score(b, p, cv, B)))
    rows = rows.copy()
    rows["rho"], rows["A"], rows["E"], rows["P"], rows["score_re"] = R, A, E, P, S
    err = np.abs(rows.score_re - (rows.A + rows.E - rows.P)).max()
    assert err < 1e-6, f"decomposition check failed: {err}"
    return rows


def load(enc, infos, gops):
    out = []
    for tag in ("final4", "final3"):
        for split in SPLITS:
            fs = glob.glob(f"{ROOT}/results_v1/controller_real/{tag}_{enc}_{split}_*.parquet")
            c = pd.concat(pd.read_parquet(f, columns=["clip_id", "gop", "level_q0", "k", "bits", "psnr_yuv", "score",
                                                     "budget_bits", "qps"]) for f in fs)
            c["gid"] = [f"{a}@{gops[(a, b)]}" for a, b in zip(c.clip_id, c.gop)]
            c = c[c.gid.isin(infos)]
            bi = np.array([infos[g]["budget"][int(l)] for g, l in zip(c.gid, c.level_q0)])
            assert np.allclose(bi, c.budget_bits.to_numpy(), rtol=1e-6), f"budget mismatch {tag} {split}"
            out.append(pd.DataFrame({"method": tag, "split": split, "gid": c.gid, "clip": c.clip_id,
                                     "level": c.level_q0.astype(int), "k": c.k.astype(int), "seed": 0,
                                     "bits": c.bits.astype(float), "psnr": c.psnr_yuv, "score_src": np.nan}))
            # (controller_real rows store the OLD %-saving score, so they are not used for the stored-score check)
    d = pd.read_csv(f"{ROOT}/results_v1/lfq_compare_{enc}_final4.csv",
                    usecols=["method", "k", "seed", "split", "gid", "clip", "budget", "score", "dpsnr_b", "use"])
    d = d[(d.split == "val") & d.method.isin(LEARNERS) & d.gid.isin(infos)]
    B = np.array([infos[g]["budget"][int(l)] for g, l in zip(d.gid, d.budget)])
    psnr = d.dpsnr_b.to_numpy() + np.array([pcq(infos[g]["curve"], b) for g, b in zip(d.gid, B)])
    out.append(pd.DataFrame({"method": d.method, "split": "val", "gid": d.gid, "clip": d["clip"], "level": d.budget,
                             "k": d.k, "seed": d.seed, "bits": d.use.to_numpy() * B, "psnr": psnr,
                             "score_src": d.score}))
    for split in SPLITS:
        s = pickle.load(open(f"{RC}/{enc}_lfq/results_search/search_{split}.pkl", "rb"))
        r = [(g, lv, e["total_bits"], e["psnr"]) for g, x in s.items() if g in infos for lv, e in x.items()]
        r = pd.DataFrame(r, columns=["gid", "level", "bits", "psnr"])
        r["clip"] = [infos[g]["gop"]["clip"] for g in r.gid]
        for k in (0, 2, 5, 10, 29):   # k-independent: replicated so it pairs with every k
            out.append(r.assign(method="search", split=split, k=k, seed=0, score_src=np.nan))
    b = pd.read_parquet(f"{ROOT}/results_v1/baselines_v1.parquet")
    b = b[(b.encoder == enc) & (b.split == "val") & (b.method == "abr_vbv")].copy()
    b["gid"] = [f"{a}@{gops[(a, g)]}" for a, g in zip(b.clip_id, b.gop)]
    b = b[b.gid.isin(infos)]
    out.append(pd.DataFrame({"method": "abr_vbv", "split": "val", "gid": b.gid, "clip": b.clip_id,
                             "level": b.level_q0.astype(int), "k": b.k.astype(int), "seed": 0,
                             "bits": b.bits.astype(float), "psnr": b.psnr_yuv, "score_src": np.nan}))
    x = pd.concat(out, ignore_index=True)
    lab = pd.read_csv(f"{ROOT}/data/v1/320x180/rd/flat_gops.csv").set_index("gid").label
    x["cls"] = x.gid.map(lab)
    assert x.cls.notna().all()
    return x


def summ(x, by):
    g = x.assign(abs_err=100 * (x.rho - 1).abs(), sgn=100 * (x.rho - 1), over=100 * (x.rho > 1),
                 EP=x.E - x.P).groupby(by)
    t = g.agg(n=("A", "size"), score=("score_re", "mean"), A=("A", "mean"), E_minus_P=("EP", "mean"),
              mean_abs_err_pct=("abs_err", "mean"), signed_err_pct=("sgn", "mean"), over_pct=("over", "mean"))
    t["p90_abs_err_pct"] = g.abs_err.quantile(0.9)
    return t.round(3)


def main():
    os.makedirs(OUT, exist_ok=True)
    gops = pd.read_csv(f"{ROOT}/data/v1/320x180/gops.csv").set_index(["clip_id", "gop"]).start_frame
    H = ["# Exp 1: allocation headroom and local slope (exp_next/exp1/decompose.py)", "",
         "Val, flat GOPs excluded. A = quality for the bits (dB). 95% bootstrap over clips ('*' = CI excludes 0).", ""]
    pooled = []
    for enc in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{enc}_lfq/results_infos/infos_learn.pkl", "rb"))
        x = decomp(load(enc, infos, gops), infos)
        # stored scores must match the recomputed ones where a stored score exists
        m = x.score_src.notna()
        d = np.abs(x.score_src[m] - x.score_re[m])
        x.to_parquet(f"{OUT}/episodes_{enc}.parquet")
        L = [f"# Exp 1: score decomposition, {enc} (exp_next/exp1/decompose.py)", "",
             "score = A + E - P per episode (checked to 1e-6). A = PSNR - PSNR_cq(bits) (quality for the bits); "
             "E = PSNR_cq(bits) - PSNR_cq(B) (spend effect); P = 0.17 x % over. Spend error = 100 (bits/B - 1). "
             "Flat GOPs excluded. Learners: seeds pooled.", "",
             f"Stored vs recomputed score: max |diff| {d.max():.2e} over {int(m.sum())} episodes "
             f"(episodes with |diff| > 1e-6: {int((d > 1e-6).sum())}).", ""]
        for split in SPLITS:
            y = x[x.split == split]
            L += [f"## {split}: by method x k", "", summ(y, ["method", "k"]).to_markdown(), ""]
        v = x[x.split == "val"]
        L += ["## val: by method x level (k pooled)", "", summ(v, ["method", "level"]).to_markdown(), "",
              "## val: by method x GOP class (k pooled)", "", summ(v, ["method", "cls"]).to_markdown(), ""]
        # level-24 hole: B beyond the QP-18 point
        v = v.assign(hole=[infos[g]["budget"][int(l)] > max(infos[g]["curve"]["bits"]) for g, l in zip(v.gid, v.level)])
        t = v.groupby(["method", "hole"]).score_re.mean().unstack()
        t["all"] = v.groupby("method").score_re.mean()
        t["without hole"] = v[~v.hole].groupby("method").score_re.mean()
        L += ["## val: level-24 hole (budget above the QP-18 curve point, reference extrapolated)", "",
              f"Episodes in the hole: {int(v[v.method == 'final4'].hole.sum())} of "
              f"{int((v.method == 'final4').sum())} final4 val episodes.", "",
              t.round(3).to_markdown(), ""]
        open(f"{OUT}/decomposition_{enc}.md", "w").write("\n".join(L) + "\n")
        # headroom: search A - final4 A, paired on (gid, level, k), val
        key = ["gid", "level", "k"]
        f4 = v[v.method == "final4"].set_index(key)
        se = v[v.method == "search"].set_index(key)
        j = f4[["A", "clip", "score_re"]].join(se[["A", "score_re"]], rsuffix="_s", how="inner").reset_index()
        j["enc"] = enc
        pooled.append(j)
        H += [f"## {enc}", "", "| k | n | search A - final4 A | search score - final4 score |", "|---|---|---|---|"]
        for k in (0, 2, 5, 10, 29):
            z = j[j.k == k]
            H.append(f"| {k} | {len(z)} | {boot(z.A_s - z.A, z['clip'])} | {boot(z.score_re_s - z.score_re, z['clip'])} |")
        # local slope at B per level (dB per 1% of bits) and the metric's optimal over rate
        rows = []
        for lv in (24, 30, 36, 42):
            sl = [(pcq(infos[g]["curve"], infos[g]["budget"][lv] * 1.01)
                   - pcq(infos[g]["curve"], infos[g]["budget"][lv] / 1.01)) / 2
                  for g in infos if infos[g]["gop"]["split"] == "val"]
            fo = f4.reset_index()
            fo = fo[fo.level == lv]
            rows.append({"level": lv, "slope dB per 1%": np.mean(sl), "optimal over rate (slope/0.17)":
                         np.mean(sl) / PEN, "final4 over rate":
                         (v[(v.method == "final4") & (v.level == lv)].rho > 1).mean()})
        H += ["", pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
    j = pd.concat(pooled)
    z = j[j.k.isin([0, 5])]
    H += ["## PRIMARY: allocation headroom H, both encoders, k in {0, 5}, val", "",
          f"search A - final4 A = {boot(z.A_s - z.A, z['clip'])} (n {len(z)}; "
          "bootstrap over clips, each clip carrying both encoders)", "",
          "Stop rule 1 (PREREG): H < 0.05 dB -> frame-level RL has little left; shrink Experiments 4 and 5.", ""]
    open(f"{OUT}/headroom.md", "w").write("\n".join(H) + "\n")
    print("\n".join(H))


if __name__ == "__main__":
    main()
