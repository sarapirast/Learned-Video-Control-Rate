"""Experiment 10 report: ABR+VBV at target margins m in {0.95, 0.97, 0.99} (new encodes) and 1.00 (the existing
baselines_v1 abr_vbv rows), val, k in {0, 5}, scored on the dB metric against the real budget (lfq infos curves and
budgets; flat GOPs excluded). Selection rule (exp_next/exp10/PREREG.md): per encoder, the m with the highest mean
val score pooled over k 0/5 and the 4 levels, level-24-hole episodes excluded; ties within 0.005 dB -> larger m.

  python -I exp_next/exp10/abr_margin_report.py
Out: results_v1/next/exp10/abr_margin.md
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
OUT = f"{ROOT}/results_v1/next/exp10"
PEN = metrics.OVER_PENALTY_DB


def main():
    gops = pd.read_csv(f"{ROOT}/data/v1/320x180/gops.csv").set_index(["clip_id", "gop"]).start_frame
    base = pd.read_parquet(f"{ROOT}/results_v1/baselines_v1.parquet")
    L = ["# Exp 10: ABR+VBV with a target margin (exp_next/exp10/abr_margin_report.py)", "",
         "Val, k 0/5, flat GOPs excluded, dB metric vs the real budget. m = 1.00 = the existing abr_vbv rows. "
         "'hole' = budget above the QP-18 curve point (excluded from the selection).", ""]
    pick = {}
    for enc in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{enc}_lfq/results_infos/infos_learn.pkl", "rb"))
        new = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{OUT}/rows_{enc}_val_*of*.parquet")) if "_limit" not in f], ignore_index=True)
        old = base[(base.encoder == enc) & (base.split == "val") & (base.method == "abr_vbv") & base.k.isin([0, 5])]
        old = old.assign(margin=1.0, rate_q=np.nan)
        x = pd.concat([new, old], ignore_index=True)
        x["gid"] = [f"{a}@{gops[(a, g)]}" for a, g in zip(x.clip_id, x.gop)]
        x = x[x.gid.isin(infos)].copy()
        B = np.array([infos[g]["budget"][int(l)] for g, l in zip(x.gid, x.level_q0)])
        assert np.allclose(B, x.budget_bits.to_numpy(), rtol=1e-6), "budget mismatch vs lfq infos"
        cv = [infos[g]["curve"] for g in x.gid]
        x["score_db"] = [float(metrics.score(b, p, c, bb)) for b, p, c, bb in zip(x.bits, x.psnr_yuv, cv, B)]
        x["A"] = [float(p - metrics.psnr_at_bits(c, b)) for b, p, c in zip(x.bits, x.psnr_yuv, cv)]
        x["rho"] = x.bits / B
        x["hole"] = [bb > max(c["bits"]) for bb, c in zip(B, cv)]
        x["EP"] = x.score_db - x.A
        y = x[~x.hole]
        t = y.groupby("margin").agg(n=("score_db", "size"), score=("score_db", "mean"), A=("A", "mean"),
                                    E_minus_P=("EP", "mean"),
                                    mean_abs_err_pct=("rho", lambda r: 100 * (r - 1).abs().mean()),
                                    signed_err_pct=("rho", lambda r: 100 * (r - 1).mean()),
                                    over_pct=("rho", lambda r: 100 * (r > 1).mean()))
        t["score with hole"] = x.groupby("margin").score_db.mean()
        best = t.score.max()
        m = max(mm for mm in t.index if t.score[mm] >= best - 0.005)
        pick[enc] = m
        L += [f"## {enc}", "", t.round(3).to_markdown(), "",
              "By k and level (score, hole excluded):", "",
              y.pivot_table(index=["k", "level_q0"], columns="margin", values="score_db").round(3).to_markdown(), "",
              f"Rate quantisation (realised / intended rate) over new rows: median {new.rate_q.median():.3f}, "
              f"range {new.rate_q.min():.3f}-{new.rate_q.max():.3f}.", "",
              f"**Selected margin ({enc}): {m:.2f}**", ""]
    L += ["## Selection", "", ", ".join(f"{e}: m = {v:.2f}" for e, v in pick.items()),
          "These margins go into the single final test run (k 0/2/5/10/29); the codec-to-oracle gap uses them.", ""]
    open(f"{OUT}/abr_margin.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
