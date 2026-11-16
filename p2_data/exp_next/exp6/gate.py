"""Experiment 6 gate (no encodes): leave-one-clip-out per-context choice among final4-family settings.
Pre-registration: exp_next/exp6/PREREG.md.

  python -I exp_next/exp6/gate.py
In: results_v1/controller_real/hist{1,2}_<enc>_val_*.parquet, data/v1/320x180/{budgets.csv, features/fp_bits.parquet
(first pass at QP 32), rd/rd_native.parquet, rd/flat_gops.csv}. Out: results_v1/next/exp6/gate.md
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp5")
from rclib import metrics  # noqa: E402
from shift_report import boot, fmt  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
D = f"{ROOT}/data/v1/320x180"
OUT = f"{ROOT}/results_v1/next/exp6"
FINAL4 = "1.0:6.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0"
CONTROL = "1.0:6.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:0.0"


def load(enc):
    files = [f for t in ("hist1", "hist2") for f in sorted(glob.glob(f"{ROOT}/results_v1/controller_real/{t}_{enc}_val_*.parquet"))]
    d = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    d = d[d.setting != CONTROL].copy()
    assert d.setting.nunique() == 12 and FINAL4 in set(d.setting)
    rd = pd.read_parquet(f"{D}/rd/rd_native.parquet").query("encoder == @enc")
    cur = {k: {"bits": v.sort_values("qp").slice_bits.to_numpy(float),
               "psnr": v.sort_values("qp").psnr_yuv_mean_frames.to_numpy(float)} for k, v in rd.groupby(["clip_id", "gop"])}
    flat = pd.read_csv(f"{D}/rd/flat_gops.csv")
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    d = d[~d.gid.isin(set(flat.gid[flat.flat]))].copy()
    d["hole"] = [r.budget_bits > max(cur[(r.clip_id, r.gop)]["bits"]) for r in d.itertuples()]
    d["score_q"] = [float(metrics.dpsnr_budget(r.psnr_yuv, cur[(r.clip_id, r.gop)], r.budget_bits)) for r in d.itertuples()]
    d["score_q"] -= metrics.OVER_PENALTY_DB * d.over_pct
    assert not d.duplicated(["gid", "level_q0", "k", "setting"]).any()
    # causal contexts
    b = pd.read_csv(f"{D}/budgets.csv").query("encoder == @enc")
    bq = b.melt(id_vars=["clip_id", "gop", "level_q0"], value_vars=[c for c in b.columns if c.startswith("base_qp_est_k")],
                var_name="kk", value_name="qest")
    bq["k"] = bq.kk.str.replace("base_qp_est_k", "").astype(int)
    d = d.merge(bq[["clip_id", "gop", "level_q0", "k", "qest"]], on=["clip_id", "gop", "level_q0", "k"], how="left")
    assert d.qest.notna().all()
    fp = pd.read_parquet(f"{D}/features/fp_bits.parquet").query("encoder == @enc and fp_qp == 32")
    fpw = fp.pivot_table(index=["clip_id", "gop"], columns="frame", values="fp_slice_bits")
    vis = np.array([fpw.loc[(r.clip_id, r.gop)].iloc[:r.k + 1].mean() for r in d.itertuples()])
    d["cx"] = np.log2(np.maximum(vis, 8) / (d.budget_bits / 30))
    d["q_bin"] = np.digitize(d.qest, [27, 33, 39])
    d["r_bin"] = np.where(d.r_prev.isna(), 0, 1 + np.digitize(d.r_prev.fillna(1.0), [0.9, 1.1]))
    med = d[d.setting == FINAL4].groupby("k").cx.median()
    d["c_bin"] = (d.cx > d.k.map(med)).astype(int)
    d["enc"] = enc
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    d = pd.concat([load(e) for e in ("x264", "x265")], ignore_index=True)
    d = d[~d.hole]
    ep = ["enc", "gid", "clip_id", "level_q0", "k"]
    cell = ["enc", "k", "q_bin", "r_bin", "c_bin"]
    f4 = d[d.setting == FINAL4].set_index(ep).score_q
    d["diff"] = d.score_q.to_numpy() - f4.reindex(pd.MultiIndex.from_frame(d[ep])).to_numpy()
    settings = sorted(d.setting.unique())
    picked = []
    for c in sorted(d.clip_id.unique()):
        tr, te = d[d.clip_id != c], d[(d.clip_id == c) & (d.setting == FINAL4)]
        # per (cell, setting): clip-clustered mean and SE of the paired difference on the other clips
        cm = tr.groupby(cell + ["setting", "clip_id"])["diff"].mean().reset_index()
        st = cm.groupby(cell + ["setting"])["diff"].agg(["mean", "std", "count"]).reset_index()
        st["lcb"] = st["mean"] - st["std"].fillna(np.inf) / np.sqrt(st["count"])
        best = st.sort_values("lcb", ascending=False).drop_duplicates(cell)
        best = best[best.lcb > 0].set_index(cell).setting
        for r in te.itertuples():
            key = (r.enc, r.k, r.q_bin, r.r_bin, r.c_bin)
            s = best.get(key, FINAL4)
            row = d[(d.enc == r.enc) & (d.gid == r.gid) & (d.level_q0 == r.level_q0) & (d.k == r.k) & (d.setting == s)]
            picked.append({"enc": r.enc, "gid": r.gid, "clip": c, "level": r.level_q0, "k": r.k, "setting": s,
                           "gain": float(row["diff"].iloc[0])})
    p = pd.DataFrame(picked)
    g = boot(p.gain, p["clip"])
    passed = g[0] >= 0.03 and g[1] > 0
    orc = d.groupby(cell + ["setting"])["diff"].mean().reset_index().sort_values("diff", ascending=False) \
        .drop_duplicates(cell)
    orc_gain = d.merge(orc[cell + ["setting"]], on=cell + ["setting"])["diff"].mean()
    single = d.groupby(["enc", "setting"])["diff"].mean().unstack("enc")
    L = ["# Exp 6 gate: per-context final4 setting, leave-one-clip-out (exp_next/exp6/gate.py)", "",
         "Pre-registration: exp_next/exp6/PREREG.md. 12 final4-family history settings (hist1 + hist2, no-history "
         "control excluded), val, flat GOPs and level-24 hole excluded, project metric. Contexts: k x base-QP-estimate "
         "bin x previous-GOP ratio bin x visible-complexity bin (budget level not used: clip-level hindsight). Pick = "
         "largest clip-clustered lower bound (mean - 1 SE) on the other 15 clips if > 0, else final4.", "",
         f"## GATE: picked - final4, pooled: {fmt(g)} (n {len(p)}) -> **{'PASS' if passed else 'FAIL'}** "
         "(>= +0.03 and CI above 0)", "",
         *[f"- {e}: {fmt(boot(x.gain, x['clip']))}; non-final4 picked on {100 * (x.setting != FINAL4).mean():.0f}% "
           f"of episodes" for e, x in p.groupby("enc")],
         "- by k: " + "; ".join(f"k{k} {x.gain.mean():+.3f}" for k, x in p.groupby("k")),
         f"- oracle per-cell best setting (in-sample, upper bound, not the gate): {orc_gain:+.3f}", "",
         "## Each setting vs final4 (val mean, all contexts)", "", single.round(3).to_markdown(), ""]
    open(f"{OUT}/gate.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
