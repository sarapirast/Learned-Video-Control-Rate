"""Experiment 4, rung R2 report: residual on final4 with offsets -6..+6 and final4-state features (f4) vs R1
(Exp 3: offsets -3..+3, no f4), both lambda 0.17, 180k PPO steps. Pre-registration: exp_next/exp4/PREREG_R2.md.

Runs: rcwork_v1/<enc>_resh/results_rl/res_k<k>_fixed_f4_lam0.17_st180k_r6_s<s>/{eval,eval_ckpt}.pkl (R2, 60k
checkpoint in eval_ckpt) and res_k<k>_fixed_lam0.17_st180k_s<s>/eval.pkl (R1). final4 = each row's 'static_score'.
Val only. Level-24-hole episodes (budget above the QP-18 curve point) excluded from the primary endpoint.
Gate: R2 - R1 paired on (GOP, level, k), seeds averaged per episode, pooled over both encoders and k 0/5, 95%
bootstrap over clips (each clip carries both encoders). Pass = CI above 0, no encoder CI entirely below 0, point
>= 0 at k0 and k5, same sign of the mean difference for seeds 0/1/2 (seed s vs seed s).
Checks before R3: share of non-zero offsets beyond final4's dmax / fcap or clipped to 11..51 (> 20% -> report),
offset histogram, mean |offset|, spend error.

  python -I exp_next/exp4/report_r2.py
Out: results_v1/next/exp4/r2_report.md, r2_episodes.parquet
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import metrics  # noqa: E402

RC = "/scratch1/aayushso/rcwork_v1"
OUT = "/scratch1/aayushso/ee599/results_v1/next/exp4"
KS, SEEDS = (0, 5), (0, 1, 2)
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)])
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def fmt(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" + (" *" if t[1] > 0 or t[2] < 0 else "")


def load():
    rows, offs_all = [], []
    for enc in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
        for k in KS:
            for s in SEEDS:
                r2 = f"res_k{k}_fixed_f4_lam0.17_st180k_r6_s{s}"
                srcs = {"R2": (r2, "eval", ("fixed", k, "val")),
                        "R2@60k": (r2, "eval_ckpt", (60000, "fixed", k, "val")),
                        "R1": (f"res_k{k}_fixed_lam0.17_st180k_s{s}", "eval", ("fixed", k, "val"))}
                for lab, (run, f, key) in srcs.items():
                    ev = pickle.load(open(f"{RC}/{enc}_resh/results_rl/{run}/{f}.pkl", "rb"))["res"][key]
                    for r in ev:
                        g, b = r["gid"], r["budget"]
                        cv, B = infos[g]["curve"], infos[g]["budget"][b]
                        offs = np.array(r["qps"]) - np.array(r["ctrl_qps"])
                        hole = B > max(cv["bits"])
                        rows.append({"enc": enc, "method": lab, "k": k, "seed": s, "gid": g,
                                     "clip": infos[g]["gop"]["clip"], "level": b, "score": r["score"],
                                     "final4": r["static_score"], "rho": r["bits"] / B,
                                     "A": float(r["psnr"] - metrics.psnr_at_bits(cv, r["bits"])), "hole": hole,
                                     "mean_abs_off": float(np.abs(offs).mean()), "share_zero": float((offs == 0).mean()),
                                     "mean_off": float(offs.mean()), "n_nonzero": int((offs != 0).sum()),
                                     "n_dmax": r.get("n_beyond_dmax", np.nan), "n_fcap": r.get("n_beyond_fcap", np.nan),
                                     "n_range": r.get("n_clip_range", np.nan)})
                        if lab != "R1" and not hole:
                            offs_all += [(lab, enc, k, int(o)) for o in offs]
    return pd.DataFrame(rows), pd.DataFrame(offs_all, columns=["method", "enc", "k", "off"])


def decomp(x):
    return pd.Series({"n": len(x), "score": x.score.mean(), "A": x.A.mean(), "E-P": (x.score - x.A).mean(),
                      "mean |err| %": 100 * (x.rho - 1).abs().mean(), "signed err %": 100 * (x.rho - 1).mean(),
                      "% over": 100 * (x.rho > 1).mean(), "p90 |err| %": 100 * (x.rho - 1).abs().quantile(0.9),
                      "mean |offset|": x.mean_abs_off.mean(), "share offset 0": x.share_zero.mean(),
                      "mean offset": x.mean_off.mean()})


def main():
    os.makedirs(OUT, exist_ok=True)
    d, offs = load()
    d.to_parquet(f"{OUT}/r2_episodes.parquet")
    key = ["enc", "k", "gid", "clip", "level", "hole"]
    L = ["# Exp 4 R2: offsets -6..+6 + final4-state features vs R1 (exp_next/exp4/report_r2.py)", "",
         "Val. Score in dB. Paired on (GOP, level, k); 95% bootstrap over clips ('*' = CI excludes 0). Primary "
         "excludes level-24-hole episodes. Pre-registration: exp_next/exp4/PREREG_R2.md. R2's range and features "
         "changed jointly (amendment 5); the effect is not attributed to either.", ""]
    piv = d.groupby(key + ["method"]).score.mean().unstack("method").reset_index()      # seeds averaged
    f4 = d[d.method == "R1"].groupby(key).final4.first().reset_index()
    piv = piv.merge(f4, on=key)
    assert len(piv) == len(f4) and piv[["R2", "R1", "R2@60k"]].notna().all().all()
    p = piv[~piv.hole]
    diff = p["R2"] - p["R1"]
    prim = boot(diff, p["clip"])
    per_enc = {e: boot(diff[p.enc == e], p.loc[p.enc == e, "clip"]) for e in ("x264", "x265")}
    per_k = {k: diff[p.k == k].mean() for k in KS}
    s = d[~d.hole].pivot_table(index=key + ["seed"], columns="method", values="score").reset_index()
    per_seed = {sd: (s.loc[s.seed == sd, "R2"] - s.loc[s.seed == sd, "R1"]).mean() for sd in SEEDS}
    passed = (prim[1] > 0 and all(v[2] >= 0 for v in per_enc.values()) and all(v >= 0 for v in per_k.values())
              and len({np.sign(v) for v in per_seed.values()}) == 1)
    L += ["## PRIMARY: R2 (180k) - R1 (180k), both encoders, k 0/5", "",
          f"- pooled: {fmt(prim)} (n {len(p)} episodes)",
          *[f"- {e}: {fmt(v)}" for e, v in per_enc.items()],
          *[f"- k{k}: {v:+.3f}" for k, v in per_k.items()],
          *[f"- seed {sd}: {v:+.3f}" for sd, v in per_seed.items()],
          f"- **{'PASS' if passed else 'FAIL'}** (CI above 0; no encoder CI entirely below 0; >= 0 at each k; "
          "same sign in all seeds)", ""]
    rows = []
    for lab in ("R2", "R2@60k", "R1"):
        for e in ("x264", "x265", "both"):
            q = piv[~piv.hole & ((piv.enc == e) if e != "both" else True)]
            rows.append({"method": lab, "enc": e, "score": q[lab].mean(), "final4": q.final4.mean(),
                         "minus final4": fmt(boot(q[lab] - q.final4, q["clip"]))})
    L += ["## Secondary: each vs final4 (val, hole excluded, seeds averaged)", "",
          pd.DataFrame(rows).round(3).to_markdown(index=False), "",
          "## 60k checkpoint vs 180k (R2)", "",
          f"180k - 60k pooled: {fmt(boot(p['R2'] - p['R2@60k'], p['clip']))}", ""]
    # caps / clipping check (amendment 12): realised non-zero offsets as the denominator
    c = d[~d.hole & (d.method != "R1")].groupby(["method", "enc", "k"])[["n_nonzero", "n_dmax", "n_fcap",
                                                                         "n_range"]].sum()
    for col in ("n_dmax", "n_fcap", "n_range"):
        c[f"% {col[2:]}"] = 100 * c[col] / c.n_nonzero.clip(lower=1)
    c["% any (sum, upper bound)"] = c[["% dmax", "% fcap", "% range"]].sum(axis=1)
    worst = c.loc[("R2",), "% any (sum, upper bound)"].max()
    L += ["## Check: non-zero offsets beyond final4's limits (caps not re-applied; hole excluded)", "",
          "dmax = |QP - ref| beyond final4's step limit and further than final4's own QP; fcap = below final4's fcap "
          "floor and below final4's QP; range = clipped to 11..51. Denominator = realised non-zero offsets.", "",
          c.round(2).to_markdown(), "",
          f"R2 (180k) worst cell, any: {worst:.1f}% -> "
          f"{'> 20%: REPORT TO THE HUMAN BEFORE R3' if worst > 20 else '<= 20%, no flag'}", ""]
    h = offs[offs.method == "R2"].groupby(["enc", "k"]).off.value_counts(normalize=True).unstack("off").fillna(0)
    h = (100 * h).reindex(columns=range(-6, 7), fill_value=0)
    L += ["## Realised offset histogram, R2 180k (% of frames, hole excluded)", "", h.round(1).to_markdown(), "",
          "## Decomposition by method x encoder x k (val, hole excluded, seed-level episodes)", "",
          d[~d.hole].groupby(["method", "enc", "k"]).apply(decomp, include_groups=False).round(3).to_markdown(), "",
          "## With the level-24 hole included", "",
          f"R2 - R1 pooled: {fmt(boot(piv['R2'] - piv['R1'], piv['clip']))} (n {len(piv)})", ""]
    open(f"{OUT}/r2_report.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
