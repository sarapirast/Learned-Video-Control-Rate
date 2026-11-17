"""Score the R3 k-curve runs (x264, seed 3) against final4 at the same k, val, consistent PSNR (rclib, 100 dB cap).

final4 rows = the shim re-run in results/baselines_val/rows_scored.parquet (re-scored there with metrics.score on the
resh infos.pkl). R3 rows = rl.py's eval.pkl (final model, 180k) and eval_ckpt.pkl (20k = the BC start: the actor is
frozen during the 20k critic warm-up, 60k, 120k), re-scored the same way. Level-24 hole excluded; paired on (GOP,
level); CIs: rclib metrics.paired_ci and the team's 95 % clip bootstrap (re-seeded per comparison).
Also: the k5 retrain vs the stored R3 seed-3 run (episodes and model weights).
  python -I score_kcurve.py     (Aayush's ee599 env)   -> ../summary.md, ../rows_scored.parquet
"""

import os
import pickle
import sys


import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/pavneet_pipeline")
from rclib import metrics  # noqa: E402

B = "/scratch1/ahhanagu/ee599/results/r3_kcurve"
RUN = B + "/work/results_rl/res_k{k}_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s3"
STORED = ("/scratch1/aayushso/rcwork_v1/x264_resh/results_rl/"
          "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s3")
KS = (0, 5, 29)
CK = {20000: "20k (BC start)", 60000: "60k", 120000: "120k", "final": "180k (final)"}


def boot(d, clips, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([d[np.concatenate([idx[c] for c in rng.choice(u, len(u))])].mean() for _ in range(n)])
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def fmt(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" + (" *" if t[1] > 0 or t[2] < 0 else "")


def main():
    inf = pickle.load(open("/scratch1/aayushso/rcwork_v1/x264_resh/results_infos/infos.pkl", "rb"))

    def row(r, k, ck):
        x = inf[r["gid"]]
        cv, Bg = x["curve"], x["budget"][r["budget"]]
        s = float(metrics.score(r["bits"], r["psnr"], cv, Bg))
        assert abs(s - r["score"]) < 1e-9, (r["gid"], s, r["score"])       # same metric as rl.py's own eval
        return {"k": k, "ckpt": CK[ck], "gid": r["gid"], "clip": x["gop"]["clip"], "level": r["budget"],
                "score": s, "hole": bool(Bg > max(cv["bits"])), "over": r["bits"] > Bg,
                "cls": "cut/gradual" if x["gop"]["label"] in ("cut", "gradual") else "stable"}

    rows = []
    for k in KS:
        d = RUN.format(k=k)
        rows += [row(r, k, "final") for r in pickle.load(open(f"{d}/eval.pkl", "rb"))["res"][("fixed", k, "val")]]
        ck = pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"]
        for n in (20000, 60000, 120000):
            rows += [row(r, k, n) for r in ck[(n, "fixed", k, "val")]]
    d = pd.DataFrame(rows)
    d.to_parquet(f"{B}/rows_scored.parquet")
    f4 = pd.read_parquet("/scratch1/ahhanagu/ee599/results/baselines_val/rows_scored.parquet")
    f4 = f4[(f4.enc == "x264") & (f4.method == "final4")].set_index(["gid", "level", "k"]).score

    T = []
    for (k, ck), g in d[~d.hole].groupby(["k", "ckpt"], sort=False):
        base = f4.loc[pd.MultiIndex.from_frame(g[["gid", "level"]].assign(k=k))].to_numpy()
        diff = g.score.to_numpy() - base
        mu, hw = metrics.paired_ci(g.score, base)
        r = {"k": k, "checkpoint": ck, "n": len(g), "R3 score": g.score.mean(), "final4 score": base.mean(),
             "Δ vs final4 [clip boot]": fmt(boot(diff, g["clip"].to_numpy())), "paired_ci": f"{mu:+.3f} ± {hw:.3f}",
             "% over": 100 * g.over.mean()}
        for c in ("stable", "cut/gradual"):
            m = (g.cls == c).to_numpy()
            r[f"Δ {c}"] = fmt(boot(diff[m], g["clip"].to_numpy()[m])) + f" (n {m.sum()})"
        T.append(r)
    t = pd.DataFrame(T)
    order = {v: i for i, v in enumerate(CK.values())}
    t = t.sort_values(["k", "checkpoint"], key=lambda s: s.map(order) if s.name == "checkpoint" else s)

    # PPO's own contribution at each k: final - BC start, paired
    P = []
    for k in KS:
        a = d[(d.k == k) & ~d.hole & (d.ckpt == CK["final"])].set_index(["gid", "level"]).score
        b = d[(d.k == k) & ~d.hole & (d.ckpt == CK[20000])].set_index(["gid", "level"]).score.loc[a.index]
        clips = d[(d.k == k) & ~d.hole & (d.ckpt == CK["final"])]["clip"].to_numpy()
        P.append({"k": k, "final - BC start [clip boot]": fmt(boot(a.to_numpy() - b.to_numpy(), clips))})

    # k5 retrain vs the stored seed-3 run: same episodes? same weights?
    mine = {(r["gid"], r["budget"]): r for r in pickle.load(open(f"{RUN.format(k=5)}/eval.pkl", "rb"))["res"][("fixed", 5, "val")]}
    st = {(r["gid"], r["budget"]): r for r in pickle.load(open(f"{STORED}/eval_ckpt.pkl", "rb"))["res"][(180993, "fixed", 5, "val")]}
    same_q = sum(list(mine[x]["qps"]) == list(st[x]["qps"]) for x in st)
    same_s = sum(abs(mine[x]["score"] - st[x]["score"]) < 1e-9 for x in st)

    # weights compared in the rc env (this env has no torch): weights_check.txt, written by the one-liner in the README
    check = [f"episodes with identical QPs: {same_q}/{len(st)}; identical score: {same_s}/{len(st)}",
             open(f"{B}/weights_check.txt").read().strip()]

    L = ["# R3 across lookahead (x264, seed 3, val; shim backend)", "",
         "score = dPSNR_B - 0.17 dB x %over (rclib metrics.score, PSNR capped at 100 dB per plane = same convention for "
         "R3 and final4). Δ = R3 - final4 at the same k, paired on (GOP, level), level-24 hole excluded. "
         "20k = the BC start (actor frozen during the critic warm-up). '*' = clip-bootstrap 95 % CI excludes 0.", "",
         t.to_markdown(index=False, floatfmt="+.3f"), "", "## PPO's contribution (final - BC start)", "",
         pd.DataFrame(P).to_markdown(index=False), "", "## k5 retrain vs stored R3 seed 3 (model_180993)", "",
         *[f"- {c}" for c in check], ""]
    open(f"{B}/summary.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
