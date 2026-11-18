"""Score all R3 k-curve runs (x264, val): per k, seeds averaged per episode.

  BC alone   = the 20k checkpoint (actor frozen during the 20k critic warm-up = the BC start)
  R3         = the final model (180k)
Per k: BC - final4, R3 - final4, R3 - BC, all paired on (GOP, level), level-24 hole excluded, split stable vs
cut+gradual; 95 % clip bootstrap (re-seeded per comparison) and rclib metrics.paired_ci. final4 = the shim re-run
(results/baselines_val/rows_scored.parquet), same PSNR convention (rclib, 100 dB cap) as every R3 row here.
Also per seed (R3 - final4, BC - final4), and the k5 seed 4/5 reruns vs Aayush's stored runs (episodes).
  python -I score_lookahead_all.py     (Aayush's ee599 env)   -> ../summary_all.md, ../rows_all.parquet
"""
import glob
import os
import pickle
import re
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/pavneet_pipeline")
from rclib import metrics  # noqa: E402

B = "/scratch1/ahhanagu/ee599/results/r3_kcurve"
PAT = re.compile(r"res_k(\d+)_fixed_no-level_f4_lam0\.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s(\d+)$")
STORED = ("/scratch1/aayushso/rcwork_v1/x264_resh/results_rl/"
          "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s{s}")


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

    def row(r, k, s, what):
        x = inf[r["gid"]]
        cv, Bg = x["curve"], x["budget"][r["budget"]]
        sc = float(metrics.score(r["bits"], r["psnr"], cv, Bg))
        assert abs(sc - r["score"]) < 1e-9, (r["gid"], sc, r["score"])
        return {"k": k, "seed": s, "what": what, "gid": r["gid"], "clip": x["gop"]["clip"], "level": r["budget"],
                "score": sc, "hole": bool(Bg > max(cv["bits"])),
                "cls": "cut/gradual" if x["gop"]["label"] in ("cut", "gradual") else "stable"}

    rows, runs = [], []
    for d in sorted(glob.glob(f"{B}/work/results_rl/res_k*_s*")):
        m = PAT.search(d)
        if not m or not os.path.exists(f"{d}/eval.pkl"):
            continue
        k, s = int(m.group(1)), int(m.group(2))
        runs.append((k, s))
        rows += [row(r, k, s, "R3") for r in pickle.load(open(f"{d}/eval.pkl", "rb"))["res"][("fixed", k, "val")]]
        rows += [row(r, k, s, "BC") for r in pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"][(20000, "fixed", k, "val")]]
    d = pd.DataFrame(rows)
    d.to_parquet(f"{B}/rows_all.parquet")
    d = d[~d.hole]
    f4 = pd.read_parquet("/scratch1/ahhanagu/ee599/results/baselines_val/rows_scored.parquet")
    f4 = f4[(f4.enc == "x264") & (f4.method == "final4")].set_index(["k", "gid", "level"]).score

    def ep(sub):   # seeds averaged per episode
        return sub.groupby(["gid", "level", "clip", "cls"]).score.mean().reset_index()

    def comp(a, b):   # a - b on matching episodes -> overall, stable, cut/gradual
        j = a.merge(b, on=["gid", "level", "clip", "cls"], suffixes=("", "_b"))
        diff, cl = (j.score - j.score_b).to_numpy(), j["clip"].to_numpy()
        out = [fmt(boot(diff, cl)), "{:+.3f} ± {:.3f}".format(*metrics.paired_ci(j.score, j.score_b))]
        for c in ("stable", "cut/gradual"):
            mk = (j.cls == c).to_numpy()
            out.append(fmt(boot(diff[mk], cl[mk])) + f" (n {mk.sum()})")
        return len(j), out

    T, S = [], []
    for k in sorted(d.k.unique()):
        dk = d[d.k == k]
        seeds = sorted(dk.seed.unique())
        r3, bc = ep(dk[dk.what == "R3"]), ep(dk[dk.what == "BC"])
        base = f4.loc[k].reset_index()
        base = base.merge(r3[["gid", "level", "clip", "cls"]], on=["gid", "level"])
        for lab, a, b in (("BC − final4", bc, base), ("R3 − final4", r3, base), ("R3 − BC", r3, bc)):
            n, (o, pci, st, cg) = comp(a, b)
            T.append({"k": k, "seeds": ",".join(map(str, seeds)), "comparison": lab, "n": n, "Δ [clip boot]": o,
                      "paired_ci": pci, "Δ stable": st, "Δ cut+gradual": cg})
        T.append({"k": k, "seeds": "", "comparison": "(scores: final4 / BC / R3)", "n": len(base),
                  "Δ [clip boot]": f"{base.score.mean():+.3f} / {bc.score.mean():+.3f} / {r3.score.mean():+.3f}"})
        for s in seeds:
            for what in ("BC", "R3"):
                e = dk[(dk.seed == s) & (dk.what == what)].set_index(["gid", "level"]).score
                S.append({"k": k, "seed": s, "what": what,
                          "Δ vs final4": (e - f4.loc[k].loc[e.index]).mean()})
    s = pd.DataFrame(S).pivot_table(index=["k", "seed"], columns="what", values="Δ vs final4").reset_index()
    s[["k", "seed"]] = s[["k", "seed"]].astype(int).astype(str)      # keep +.3f formatting for the scores only

    chk = []
    for sd in (4, 5):
        p = f"{B}/work/results_rl/res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s{sd}/eval.pkl"
        if not os.path.exists(p):
            chk.append(f"k5 s{sd}: no rerun yet")
            continue
        mine = {(r["gid"], r["budget"]): r for r in pickle.load(open(p, "rb"))["res"][("fixed", 5, "val")]}
        st = {(r["gid"], r["budget"]): r for r in
              pickle.load(open(f"{STORED.format(s=sd)}/eval_ckpt.pkl", "rb"))["res"][(180993, "fixed", 5, "val")]}
        q = sum(list(mine[x]["qps"]) == list(st[x]["qps"]) for x in st)
        sc = sum(abs(mine[x]["score"] - st[x]["score"]) < 1e-9 for x in st)
        chk.append(f"k5 s{sd} rerun vs Aayush's model_180993: identical QPs {q}/{len(st)}, identical score {sc}/{len(st)}")
    wc = f"{B}/weights_check_b2.txt"
    if os.path.exists(wc):
        chk += open(wc).read().strip().splitlines()

    L = ["# R3 across lookahead, all runs (x264, val, shim backend)", "",
         f"Runs: {sorted(runs)}. Per k: seeds averaged per episode, then paired with final4 at the same k; level-24 "
         "hole excluded; BC = 20k checkpoint (the BC start), R3 = final 180k model. '*' = 95 % clip bootstrap "
         "excludes 0. Score = dPSNR_B - 0.17 dB x %over, PSNR capped at 100 dB per plane for every method.", "",
         pd.DataFrame(T).fillna("").to_markdown(index=False), "", "## Per seed (mean Δ vs final4)", "",
         s.to_markdown(index=False, floatfmt="+.3f"), "", "## Reproduction checks", "", *[f"- {c}" for c in chk], ""]
    open(f"{B}/summary_all.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
