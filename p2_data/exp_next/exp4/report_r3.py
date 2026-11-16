"""Exp 4 R3 report (k5, val): R3 = R2 recipe + o[2] masked + mean[t] + bit cap + BC actor + 20k critic warm-up;
R2c = the same without the BC start. Pre-registration: exp_next/exp5/PREREG_BC.md REVISION 4.

Gate: R3 - final4 pooled over both encoders, point >= +0.03 dB and 95% clip-bootstrap CI lower bound > 0 (val, k5,
hole excluded, seeds averaged per episode). Also: R3 - R2c (BC-start effect), R3 - R2, R2c - R2, per encoder and
seed, 60k checkpoints, A / E-P / spend, x265 also vs final4 + per-qbin shift (Exp 5a REVISION 4 val rows).

  python -I exp_next/exp4/report_r3.py [--encs x264,x265]
Out: results_v1/next/exp4/r3_report.md
"""
import argparse
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp5")
from rclib import metrics  # noqa: E402
from shift_report import boot, fmt  # noqa: E402

RC = "/scratch1/aayushso/rcwork_v1"
OUT = "/scratch1/aayushso/ee599/results_v1/next/exp4"
EXP5 = "/scratch1/aayushso/ee599/results_v1/next/exp5"
RUNS = {"R3": "res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s{s}",
        "R2c": "res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_wu20k_s{s}",
        "R2": "res_k5_fixed_f4_lam0.17_st180k_r6_s{s}"}
SEEDS = (0, 1, 2)


def load(encs):
    rows = []
    for enc in encs:
        inf = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
        for m, tmpl in RUNS.items():
            for s in SEEDS:
                d = f"{RC}/{enc}_resh/results_rl/{tmpl.format(s=s)}"
                srcs = [(m, pickle.load(open(f"{d}/eval.pkl", "rb"))["res"][("fixed", 5, "val")])]
                if m != "R2" and os.path.exists(f"{d}/eval_ckpt.pkl"):
                    srcs.append((m + "@60k", pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"][(60000, "fixed", 5, "val")]))
                for lab, ev in srcs:
                    for r in ev:
                        g, b = r["gid"], r["budget"]
                        cv, B = inf[g]["curve"], inf[g]["budget"][b]
                        c = inf[g]["ctrl"][(b, 5)]
                        p4 = c["dpsnr"] + metrics.psnr_at_bits(cv, B)
                        offs = np.array(r["qps"]) - np.array(r["ctrl_qps"])
                        rows.append({"enc": enc, "method": lab, "seed": s, "gid": g, "clip": inf[g]["gop"]["clip"],
                                     "level": b, "hole": B > max(cv["bits"]), "score": r["score"],
                                     "final4": r["static_score"], "rho": r["bits"] / B,
                                     "A": float(r["psnr"] - metrics.psnr_at_bits(cv, r["bits"])),
                                     "rho_f4": c["bits"] / B, "A_f4": float(p4 - metrics.psnr_at_bits(cv, c["bits"])),
                                     "mean_off": float(offs.mean()), "mean_abs_off": float(np.abs(offs).mean()),
                                     "cls": "cut/gradual" if inf[g]["gop"]["label"] in ("cut", "gradual") else "stable"})
    return pd.DataFrame(rows)


def dec(x, f4=False):
    s, A, rho = (x.final4, x.A_f4, x.rho_f4) if f4 else (x.score, x.A, x.rho)
    return {"n": len(x), "score": s.mean(), "A": A.mean(), "E-P": (s - A).mean(),
            "mean |err| %": 100 * (rho - 1).abs().mean(), "p90 |err| %": 100 * (rho - 1).abs().quantile(0.9),
            "signed err %": 100 * (rho - 1).mean(), "% over": 100 * (rho > 1).mean()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encs", default="x264,x265")
    a = ap.parse_args()
    encs = a.encs.split(",")
    d = load(encs)
    y = d[~d.hole]
    key = ["enc", "gid", "clip", "level", "cls"]
    p = y.pivot_table(index=key, columns="method", values="score").reset_index()     # seeds averaged
    p = p.merge(y.groupby(key).final4.first().reset_index(), on=key)
    assert p[list(RUNS)].notna().all().all()
    g = boot(p.R3 - p.final4, p["clip"])
    passed = g[0] >= 0.03 and g[1] > 0
    L = ["# Exp 4 R3 (k5, val): PPO from the BC actor (exp_next/exp4/report_r3.py)", "",
         "Pre-registration: exp_next/exp5/PREREG_BC.md REVISION 4. Paired on (GOP, level), seeds averaged per episode, "
         "95% clip bootstrap ('*' excludes 0), level-24 hole excluded. Encoders: " + ", ".join(encs) + ".", "",
         "Runs: **R3** = R2's recipe + o[2] masked + mean[t] (real-valued, before final4's rounding) + bit cap + 20k-step "
         "critic warm-up + actor from BC. **R2c (control)** = R3's exact setup, actor from rl.py's standard residual "
         "init instead of BC (its warm-up freezes that actor, so 160k actor-update steps vs R2's 180k). R2 = stored R2 "
         "(o[2] present, no mean[t], no bit cap, no warm-up). o[5..8] are live in all three (only BC training masked "
         "them). Hence R3 - R2c = the BC-start effect; R2c - R2 = what the setup changes cost on their own (the "
         "handicap BC has to make up).", "",
         "## GATE: R3 - final4, pooled", "",
         f"- {fmt(g)} (n {len(p)}) -> **{'PASS' if passed else 'FAIL'}** (point >= +0.03 and CI lower bound > 0)"
         + ("" if len(encs) == 2 else " -- PARTIAL: not all encoders in yet, not the gate")]
    if "x265" in encs:              # the second x265 k5 baseline, next to the gate (not part of it)
        sh = {(r["gid"], r["level"]): r["score"]
              for r in pickle.load(open(f"{EXP5}/shift_rows_x265_val_qbin_k5_0of1.pkl", "rb"))}
        q = p[p.enc == "x265"].copy()
        q["shift"] = [sh[(gg, lv)] for gg, lv in zip(q.gid, q.level)]
        L += [f"- x265 bar = final4 + per-qbin shift (Exp 5a REVISION 4, val +0.153 vs final4): R3 - (final4 + shift) "
              f"{fmt(boot(q.R3 - q['shift'], q['clip']))}; R3 - final4 (x265) {fmt(boot(q.R3 - q.final4, q['clip']))}; "
              f"(final4 + shift) - final4 on these episodes {fmt(boot(q['shift'] - q.final4, q['clip']))}"]
    L += [""]
    comp = [("R3 - final4", p.R3 - p.final4), ("R3 - R2c = effect of the BC start", p.R3 - p.R2c),
            ("R2c - R2 = cost of R3's setup changes alone", p.R2c - p.R2), ("R3 - R2", p.R3 - p.R2),
            ("R2c - final4", p.R2c - p.final4), ("R2 - final4", p.R2 - p.final4)]
    if "R3@60k" in p:
        comp.append(("R3 180k - R3 60k", p.R3 - p["R3@60k"]))
    L += ["## Comparisons per encoder", "", "| comparison | " + " | ".join(encs + ["pooled"]) + " |",
          "|---|" + "---|" * (len(encs) + 1)]
    for name, dd in comp:
        L.append(f"| {name} | " + " | ".join(fmt(boot(dd[p.enc == e], p.loc[p.enc == e, "clip"])) for e in encs)
                 + f" | {fmt(boot(dd, p['clip']))} |")
    ps = y[y.method.isin(["R3", "R2c"])].pivot_table(index=key + ["seed"], columns="method", values="score")
    ps = ps.join(y[y.method == "R3"].set_index(key + ["seed"]).final4).reset_index()
    L += ["", "Per seed (R3 - final4 / R3 - R2c): " + "; ".join(
        f"s{s} {(q.R3 - q.final4).mean():+.3f} / {(q.R3 - q.R2c).mean():+.3f}" for s, q in ps.groupby("seed")),
          "Cut/gradual vs stable (R3 - final4): " + "; ".join(
        f"{c} {fmt(boot(q.R3 - q.final4, q['clip']))} (n {len(q)})" for c, q in p.groupby("cls")), ""]
    rows = []
    for (e, m), x in y.groupby(["enc", "method"]):
        rows.append({"enc": e, "method": m, **dec(x), "mean offset": x.mean_off.mean(), "mean |offset|": x.mean_abs_off.mean()})
    for e, x in y[y.method == "R3"].groupby("enc"):
        rows.append({"enc": e, "method": "final4", **dec(x, True)})
    L += ["## Decomposition (seed-level episodes; offset = QP - final4's QP, includes mean[t])", "",
          "Signed spend error < 0 = under budget. Going over costs 2-3x more than going under (Exp 1 slope), so "
          "landing under more often can be a cheaper mistake; read % over together with signed and p90 error.", "",
          pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
    open(f"{OUT}/r3_report{'' if len(encs) == 2 else '_' + '_'.join(encs)}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
