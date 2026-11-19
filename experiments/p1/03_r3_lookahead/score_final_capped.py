"""score_final_capped.py: final scoring of 03 (R3 / BC across lookahead) and 04 (R2c control) with ONE PSNR convention
everywhere: every plane's per-frame PSNR capped at 100 dB, including the constant-QP curves (Aayush's cap_fix_x264.pkl,
p2_data/exp_next/final/cap_fix.py, applied exactly as report.py --psnr-cap does).

Rows (x264, val, level-24 hole excluded, paired on (GOP, level), seeds averaged per episode before pairing):
  final4     = 02's shim re-run (rclib PSNR, already capped), k 0/2/5/10/29; checked against cap_fix's re-measured
               final4 PSNR where it has one
  BC         = R3 run's 20k checkpoint (actor frozen during the critic warm-up = the BC start)
  R3         = R3 run's final 180k model          (seeds 3-5 at k0/k5/k29, seed 3 at k2/k10)
  shift-only = R2c run's 20k checkpoint (standard init, frozen: always offset 0 = final4 + mean shift + bit cap)
  R2c        = R2c run's final 180k model          (seeds 3-5 at k0/k29; seed 0 at k5, current code)
Per k: BC - final4, R3 - final4, R3 - BC, shift-only - final4, R2c - final4, R3 - R2c, R2c - shift-only; overall,
stable and cut+gradual; 95 % clip bootstrap (2000 resamples of clips, re-seeded per comparison).
Not used: the k5 seed-0 R3 retrain (a reproduction check, see 04).
Inputs: results/baselines_val/rows_final4_k<k>.pkl, results/r3_kcurve/work/results_rl/*/eval*.pkl, Aayush's resh
infos.pkl and cap_fix_x264.pkl (read-only).
Outputs: results/r3_kcurve/summary_final.md, rows_final.parquet
--enc x265: the same for x265. final4 = Aayush's stored x265 rows with his capped PSNR (cap_fix_x265.pkl; no shim
re-run exists for x265); my x265 runs from work_x265/; where I have no run for a (method, k), Aayush's existing x265
runs are used and credited in the summary: R3 k2 (final 180k) and k5 (180,993 checkpoint) seeds 3-5, BC alone k0
(seeds 0-2) and k2 / k5 (seeds 3-5). Outputs then end in _x265.
Run (Aayush's ee599 env, seconds): python -I score_final_capped.py [--enc x265]
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

B = "/scratch1/ahhanagu/ee599/results"
ENC = sys.argv[sys.argv.index("--enc") + 1] if "--enc" in sys.argv else "x264"
assert ENC in ("x264", "x265"), ENC
TAG = "" if ENC == "x264" else f"_{ENC}"
RUNS = f"{B}/r3_kcurve/{'work' if ENC == 'x264' else 'work_' + ENC}/results_rl"
FIX = f"/scratch1/aayushso/ee599/results_v1/final/cap_fix_{ENC}.pkl"
INFOS = f"/scratch1/aayushso/rcwork_v1/{ENC}_resh/results_infos/infos.pkl"
AY_RL = f"/scratch1/aayushso/rcwork_v1/{ENC}_resh/results_rl"            # Aayush's stored runs (x265 only)
AY_EXP5 = "/scratch1/aayushso/ee599/results_v1/next/exp5"
AY_RUN = "res_k{k}_fixed_no-level_f4_lam0.17_st{st}_r6_capbit_meanpooled_bcinit_wu20k_s{s}"
PAT = re.compile(r"res_k(\d+)_fixed_no-level_f4_lam0\.17_st180k_r6_capbit_meanpooled_(bcinit_)?wu20k_s(\d+)$")
KS = (0, 2, 5, 10, 29)


def boot(d, clips, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([d[np.concatenate([idx[c] for c in rng.choice(u, len(u))])].mean() for _ in range(n)])
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def fmt(t, ci=True):
    star = " *" if t[1] > 0 or t[2] < 0 else ""
    return (f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" if ci else f"{t[0]:+.3f}") + star


def main():
    inf = pickle.load(open(INFOS, "rb"))
    fix = pickle.load(open(FIX, "rb"))

    def curve(g):                      # = report.py Scorer.curve with --psnr-cap
        cv = inf[g]["curve"]
        if g in fix["curves"]:
            assert len(cv["psnr"]) == len(fix["curves"][g])
            return {**cv, "psnr": fix["curves"][g]}
        return cv

    def row(method, k, seed, g, level, bits, psnr, src="mine"):
        x = inf[g]
        cv, Bg = curve(g), x["budget"][level]
        return {"method": method, "k": k, "seed": seed, "gid": g, "clip": x["gop"]["clip"], "level": level,
                "score": float(metrics.score(bits, psnr, cv, Bg)), "hole": bool(Bg > max(cv["bits"])),
                "cls": "cut+gradual" if x["gop"]["label"] in ("cut", "gradual") else "stable", "src": src}

    rows, chk = [], []
    # final4: 02's re-run (capped PSNR); compare with cap_fix's re-measured final4 PSNR where it exists
    n_fix = n_same = 0
    for k in (KS if ENC == "x264" else ()):          # x264: 02's shim re-run
        for r in pickle.load(open(f"{B}/baselines_val/rows_final4_k{k}.pkl", "rb"))["rows"]:
            f = fix["final4"].get((r["gid"], r["budget"], k))
            if f is not None:
                n_fix += 1
                n_same += int(abs(f["psnr"] - r["psnr"]) < 1e-9 and f["bits"] == r["bits"])
            rows.append(row("final4", k, -1, r["gid"], r["budget"], r["bits"], r["psnr"]))
    if ENC == "x264":
        chk.append(f"final4 re-run vs cap_fix's re-measured final4 (capped PSNR, bits) on its {n_fix} episodes: identical {n_same}/{n_fix}")
    else:                               # x265: Aayush's stored final4 rows, capped PSNR from cap_fix where it differs
        f4 = pd.concat(pd.read_parquet(f) for f in
                       glob.glob(f"/scratch1/aayushso/ee599/results_v1/controller_real/final4_{ENC}_val_*.parquet"))
        f4["gid"] = f4.clip_id + "@" + (30 * f4.gop).astype(str)
        for r in f4[f4.gid.isin(inf)].itertuples():
            f = fix["final4"].get((r.gid, int(r.level_q0), int(r.k)))
            n_fix += f is not None
            rows.append(row("final4", int(r.k), -1, r.gid, int(r.level_q0), float(r.bits),
                            float(r.psnr_yuv if f is None else f["psnr"]), "Aayush (stored)"))
        chk.append(f"final4 = Aayush's stored {ENC} rows; capped PSNR from cap_fix on {n_fix} episodes")
    # R3 / BC and R2c / shift-only
    used = []
    for d in sorted(glob.glob(f"{RUNS}/res_k*")):
        m = PAT.search(d)
        if not m:
            continue
        k, bc, s = int(m.group(1)), bool(m.group(2)), int(m.group(3))
        if bc and s == 0:
            continue                    # k5 seed-0 R3 retrain = reproduction check only
        final, start = ("R3", "BC") if bc else ("R2c", "shift-only")
        used.append(f"{final} k{k} s{s}")
        for r in pickle.load(open(f"{d}/eval.pkl", "rb"))["res"][("fixed", k, "val")]:
            rows.append(row(final, k, s, r["gid"], r["budget"], r["bits"], r["psnr"]))
        for r in pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"][(20000, "fixed", k, "val")]:
            rows.append(row(start, k, s, r["gid"], r["budget"], r["bits"], r["psnr"]))
    if ENC == "x265":                   # Aayush's existing x265 runs, only for (method, k) I have not run
        have = {(r["method"], r["k"]) for r in rows}
        n_chk = n_ok = 0

        def add(method, k, rr):
            nonlocal n_chk, n_ok
            if (method, k) in have:
                return
            seeds = sorted({r["seed"] for r in rr})
            for r in rr:
                lv = r["level"] if "level" in r else r["budget"]   # BC rows: budget = bits, level separate
                x = row(method, k, r["seed"], r["gid"], lv, r["bits"], r["psnr"], "Aayush")
                if r["gid"] not in fix["curves"]:      # stored scores use the old curves: compare where unchanged
                    n_chk += 1
                    n_ok += abs(x["score"] - r["score"]) < 1e-9
                rows.append(x)
            used.append(f"{method} k{k} s{','.join(map(str, seeds))} (Aayush)")

        for k, st, key in ((2, "180k", None), (5, "360k", (180993, "fixed", 5, "val"))):
            rr = []
            for s in (3, 4, 5):
                dd = f"{AY_RL}/{AY_RUN.format(k=k, st=st, s=s)}"
                res = (pickle.load(open(f"{dd}/eval.pkl", "rb"))["res"][("fixed", k, "val")] if key is None else
                       pickle.load(open(f"{dd}/eval_ckpt.pkl", "rb"))["res"][key])
                rr += [{**r, "seed": s} for r in res]
            add("R3", k, rr)
        bc = pickle.load(open(f"{AY_EXP5}/bc_rows_{ENC}_val_k25_s345.pkl", "rb"))
        bc0 = pickle.load(open(f"{AY_EXP5}/bc_rows_{ENC}_val_k0_s012.pkl", "rb"))
        for k in (0, 2, 5):
            add("BC", k, [r for r in (bc0 if k == 0 else bc) if r["k"] == k])
        chk.append(f"Aayush's stored scores reproduced by this scorer where the capped curve is unchanged: {n_ok}/{n_chk}")
    d = pd.DataFrame(rows)
    d.to_parquet(f"{B}/r3_kcurve/rows_final{TAG}.parquet")
    d = d[~d.hole]

    def ep(method, k):                 # seeds averaged per episode
        x = d[(d.method == method) & (d.k == k)]
        return x.groupby(["gid", "level", "clip", "cls"]).score.mean(), sorted(x.seed.unique())

    def comp(a, b):
        j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").reset_index()
        diff, cl = (j.a - j.b).to_numpy(), j["clip"].to_numpy()
        out = {"all": boot(diff, cl)}
        for c in ("stable", "cut+gradual"):
            mk = (j.cls == c).to_numpy()
            out[c] = boot(diff[mk], cl[mk])
        return out, len(j)

    PAIRS = [("BC − final4", "BC", "final4"), ("R3 − final4", "R3", "final4"), ("R3 − BC", "R3", "BC"),
             ("shift-only − final4", "shift-only", "final4"), ("R2c − final4", "R2c", "final4"),
             ("R3 − R2c", "R3", "R2c"), ("R2c − shift-only", "R2c", "shift-only")]
    main_t, long_t, scores = [], [], []
    for k in KS:
        e = {m: ep(m, k) for m in ("final4", "BC", "R3", "shift-only", "R2c")}
        scores.append({"k": k, **{m: (f"{e[m][0].mean():+.3f}" if len(e[m][0]) else "") for m in e},
                       "seeds R3 / R2c": f"{','.join(map(str, e['R3'][1]))} / {','.join(map(str, e['R2c'][1])) or '-'}"})
        mrow = {"k": k}
        for lab, a, b in PAIRS:
            if not len(e[a][0]) or not len(e[b][0]):
                mrow[lab] = ""
                continue
            o, n = comp(e[a][0], e[b][0])
            mrow[lab] = fmt(o["all"])
            long_t.append({"k": k, "comparison": lab, "n": n, "all": fmt(o["all"]), "stable": fmt(o["stable"]),
                           "cut+gradual": fmt(o["cut+gradual"])})
        main_t.append(mrow)
    mt = pd.DataFrame(main_t)
    n_k = len(d[(d.method == "final4") & (d.k == 0)])
    L = [f"# Final: R3, BC and R2c across lookahead ({ENC}, val, one PSNR cap everywhere)", "",
         "dB; score = dPSNR_B - 0.17 dB per 1 % over, every plane's PSNR capped at 100 dB including the constant-QP curves "
         f"(cap_fix_{ENC}.pkl); level-24 hole excluded (n = {n_k} per k); seeds averaged per episode; 95 % clip bootstrap, "
         "'*' excludes 0. BC = R3's 20k checkpoint, shift-only = R2c's 20k checkpoint (final4 + mean shift + bit cap).", "",
         "## Per k (all GOPs)", "", mt[["k", "BC − final4", "R3 − final4", "R3 − BC", "R2c − final4", "R3 − R2c"]].to_markdown(index=False),
         "", "## Setup-only terms", "", mt[["k", "shift-only − final4", "R2c − shift-only"]].to_markdown(index=False),
         "", "## Mean scores", "", pd.DataFrame(scores).to_markdown(index=False),
         "", "## Every comparison, stable vs cut+gradual", "", pd.DataFrame(long_t).to_markdown(index=False),
         "", "## Checks", "", *[f"- {c}" for c in chk], f"- runs used: {', '.join(used)}", ""]
    open(f"{B}/r3_kcurve/summary_final{TAG}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
