"""Experiment 3 report: residual on final4 at lambda 0.17 (new) vs lambda 0.34 (item 37), both at 180k PPO steps.
Pre-registration: exp_next/exp3/PREREG.md.

Runs: rcwork_v1/<enc>_resh/results_rl/res_k<k>_fixed_lam0.17_st180k_s<s>/{eval,eval_ckpt}.pkl (new, 60k checkpoint in
eval_ckpt) and res_k<k>_fixed_st180k_s<s>/eval.pkl (old). final4's stored score per episode = each row's
'static_score' (the env's stored ctrl row). Val only. Flat GOPs are not in the infos; level-24-hole episodes (budget
above the QP-18 curve point) excluded from the primary endpoint.
Primary: new - old, paired on (GOP, level, k), seeds averaged per episode, pooled over both encoders and k 0/5;
95% bootstrap over clips (each clip carries both encoders). Pass = CI above 0, no encoder CI entirely below 0,
point >= 0 at k0 and k5, same sign of the mean difference for seeds 0/1/2 (seed s vs seed s).

  python -I exp_next/exp3/report.py
Out: results_v1/next/exp3/report.md, episodes.parquet
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
OUT = "/scratch1/aayushso/ee599/results_v1/next/exp3"
KS, SEEDS = (0, 5), (0, 1, 2)
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)])
    lo, hi = np.percentile(ms, 2.5), np.percentile(ms, 97.5)
    return d.mean(), lo, hi


def fmt(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" + (" *" if t[1] > 0 or t[2] < 0 else "")


def load():
    rows = []
    for enc in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
        for k in KS:
            for s in SEEDS:
                srcs = {"lam0.17": (f"res_k{k}_fixed_lam0.17_st180k_s{s}", "eval", ("fixed", k, "val")),
                        "lam0.17@60k": (f"res_k{k}_fixed_lam0.17_st180k_s{s}", "eval_ckpt", (60000, "fixed", k, "val")),
                        "lam0.34": (f"res_k{k}_fixed_st180k_s{s}", "eval", ("fixed", k, "val"))}
                for lab, (run, f, key) in srcs.items():
                    ev = pickle.load(open(f"{RC}/{enc}_resh/results_rl/{run}/{f}.pkl", "rb"))["res"][key]
                    for r in ev:
                        g, b = r["gid"], r["budget"]
                        cv, B = infos[g]["curve"], infos[g]["budget"][b]
                        offs = np.array(r["qps"]) - np.array(r["ctrl_qps"])
                        rows.append({"enc": enc, "method": lab, "k": k, "seed": s, "gid": g,
                                     "clip": infos[g]["gop"]["clip"], "level": b, "score": r["score"],
                                     "final4": r["static_score"], "rho": r["bits"] / B,
                                     "A": float(r["psnr"] - metrics.psnr_at_bits(cv, r["bits"])),
                                     "hole": B > max(cv["bits"]), "mean_abs_off": float(np.abs(offs).mean()),
                                     "share_zero": float((offs == 0).mean()), "mean_off": float(offs.mean())})
    return pd.DataFrame(rows)


def decomp(x):
    return pd.Series({"n": len(x), "score": x.score.mean(), "A": x.A.mean(), "E-P": (x.score - x.A).mean(),
                      "mean |err| %": 100 * (x.rho - 1).abs().mean(), "signed err %": 100 * (x.rho - 1).mean(),
                      "% over": 100 * (x.rho > 1).mean(), "p90 |err| %": 100 * (x.rho - 1).abs().quantile(0.9),
                      "mean |offset|": x.mean_abs_off.mean(), "share offset 0": x.share_zero.mean(),
                      "mean offset": x.mean_off.mean()})


def main():
    os.makedirs(OUT, exist_ok=True)
    d = load()
    d.to_parquet(f"{OUT}/episodes.parquet")
    key = ["enc", "k", "gid", "clip", "level", "hole"]
    L = ["# Exp 3: residual on final4 at lambda 0.17 vs 0.34 (exp_next/exp3/report.py)", "",
         "Val. Score in dB. Paired on (GOP, level, k); 95% bootstrap over clips ('*' = CI excludes 0). Primary "
         "excludes level-24-hole episodes. Pre-registration: exp_next/exp3/PREREG.md.", ""]
    piv = d.groupby(key + ["method"]).score.mean().unstack("method").reset_index()      # seeds averaged
    f4 = d[d.method == "lam0.34"].groupby(key).final4.first().reset_index()
    piv = piv.merge(f4, on=key)
    assert len(piv) == len(f4) and piv[["lam0.17", "lam0.34"]].notna().all().all()
    p = piv[~piv.hole]
    diff = p["lam0.17"] - p["lam0.34"]
    prim = boot(diff, p["clip"])
    per_enc = {e: boot(diff[p.enc == e], p.loc[p.enc == e, "clip"]) for e in ("x264", "x265")}
    per_k = {k: diff[p.k == k].mean() for k in KS}
    s = d[~d.hole].pivot_table(index=key + ["seed"], columns="method", values="score").reset_index()
    per_seed = {sd: (s.loc[s.seed == sd, "lam0.17"] - s.loc[s.seed == sd, "lam0.34"]).mean() for sd in SEEDS}
    passed = (prim[1] > 0 and all(v[2] >= 0 for v in per_enc.values()) and all(v >= 0 for v in per_k.values())
              and len({np.sign(v) for v in per_seed.values()}) == 1)
    L += ["## PRIMARY: lambda 0.17 (180k) - lambda 0.34 (180k), both encoders, k 0/5", "",
          f"- pooled: {fmt(prim)} (n {len(p)} episodes)",
          *[f"- {e}: {fmt(v)}" for e, v in per_enc.items()],
          *[f"- k{k}: {v:+.3f}" for k, v in per_k.items()],
          *[f"- seed {sd}: {v:+.3f}" for sd, v in per_seed.items()],
          f"- **{'PASS' if passed else 'FAIL'}** (CI above 0; no encoder CI entirely below 0; >= 0 at each k; "
          "same sign in all seeds)", ""]
    rows = []
    for lab in ("lam0.17", "lam0.17@60k", "lam0.34"):
        for e in ("x264", "x265"):
            q = piv[(piv.enc == e) & ~piv.hole]
            rows.append({"method": lab, "enc": e, "score": q[lab].mean(), "final4": q.final4.mean(),
                         "minus final4": fmt(boot(q[lab] - q.final4, q["clip"]))})
        q = piv[~piv.hole]
        rows.append({"method": lab, "enc": "both", "score": q[lab].mean(), "final4": q.final4.mean(),
                     "minus final4": fmt(boot(q[lab] - q.final4, q["clip"]))})
    L += ["## Secondary: each vs final4 (val, hole excluded, seeds averaged)", "",
          pd.DataFrame(rows).round(3).to_markdown(index=False), "",
          "## 60k checkpoint vs 180k (lambda 0.17)", "",
          f"180k - 60k pooled: {fmt(boot(p['lam0.17'] - p['lam0.17@60k'], p['clip']))}", "",
          "## Decomposition by method x encoder x k (val, hole excluded, seed-level episodes)", "",
          d[~d.hole].groupby(["method", "enc", "k"]).apply(decomp, include_groups=False).round(3).to_markdown(), "",
          "## With the level-24 hole included", "",
          f"lambda 0.17 - 0.34 pooled: {fmt(boot(piv['lam0.17'] - piv['lam0.34'], piv['clip']))} (n {len(piv)})", ""]
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
