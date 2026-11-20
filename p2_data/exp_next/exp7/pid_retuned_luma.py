"""Sara's Part 4 (PID-Lagrangian PPO vs the RETUNED stream rule, margin matched on val) rescored in luma PSNR.

Part 4 = team repo p4/pid_vs_retuned.py (method in p4/README.md "Part 4"; outputs p4/outputs/pid_vs_retuned_<enc>.txt),
scored in 6:1:1 YUV PSNR. This repeats it on her code path and rescores every TEST row (policies and rule) from its
per-GOP QPs in luma PSNR of pooled MSE, as exp_next/exp7/pid_luma.py did for Part 2 (Pavneet's D50 definition; luma
MSE table results_v1/final/luma_gop_mse.pkl). Same per-GOP QPs, same rule tuning, same val-matched margins (the
over-budget flags are bits only, so the margin choice does not depend on the PSNR convention). No encodes, no training.

Rule tuning: the (qpd, cw) her val grid chose (TUNED below, read from her outputs) are used directly, not re-searched
(the grid is ~25 min of rule evaluations); the check below confirms them: every YUV line of her output (val-matched
margin, RL - rule, sensitivity margin and RL - rule) is reproduced to 3 decimals, and each tuned point's val score
matches her printed one.
Policies: ppo_pid (L 0/2), bc_ppo_pid (L 2) from repo p4/models, 3 seeds averaged; bc_ppo_lag (Pavneet's) as the
reference row, outside the PID range. CIs: stream_rl.cboot.

  /scratch1/aayushso/envs/rc/bin/python -I exp_next/exp7/pid_retuned_luma.py
Out: results_v1/final/pid_retuned_luma.md
"""
import os
import pickle
import re
import sys

import numpy as np

ROOT = "/scratch1/aayushso/ee599"
REPO = f"{ROOT}/repo"
HO = f"{REPO}/pavneet_handoff"
OUT = f"{ROOT}/results_v1/final"
# her val-tuned rule parameters (p4/outputs/pid_vs_retuned_<enc>.txt): (enc, L, rule) -> (qpd, cw, val score at tuning)
TUNED = {("x264", 2, "rule A"): (5.0, 0.0625, -0.499, 1.0), ("x264", 2, "rule B"): (5.0, 12.0, -0.645, 0.99),
         ("x264", 0, "rule A"): (5.5, 0.015625, -0.615, 1.0), ("x264", 0, "rule B"): (4.5, 3.0, -0.865, 0.98),
         ("x265", 2, "rule A"): (4.5, 0.0625, -0.294, 0.99), ("x265", 2, "rule B"): (4.5, 6.0, -0.508, 0.99),
         ("x265", 0, "rule A"): (5.0, 0.25, -0.506, 1.0), ("x265", 0, "rule B"): (4.0, 6.0, -0.768, 0.99)}
MS = (0.88, 0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99, 1.00)
POPS = {"single-clip": lambda rs: [r for r in rs if r["kind"] == "clip"], "all": lambda rs: rs}
PID = {2: ("ppo_pid", "bc_ppo_pid"), 0: ("ppo_pid",)}
RULES = ("rule A", "rule B")


def hers(enc):
    """Parse her output: (L, rule, pop, method) -> (margin, d, sens margin, sens d)."""
    out, key = {}, None
    for line in open(f"{REPO}/p4/outputs/pid_vs_retuned_{enc}.txt", encoding="utf-8"):
        m = re.match(r"== \S+ L=(\d)\s+(rule [AB]) .*\), (single-clip|all) streams ==", line)
        if m:
            key = (int(m[1]), m[2], m[3])
            continue
        m = re.match(r"\s+(\S+(?: \(ref\))?)\s+val over .*-> margin ([\d.]+) .*RL - rule ([+-][\d.]+) .*sens\. rule@([\d.]+)"
                     r" \([\d.]+%\): ([+-][\d.]+)", line)
        if m and key:
            out[key + (m[1],)] = (float(m[2]), float(m[3]), float(m[4]), float(m[5]))
    return out


def run(enc):
    os.environ.update(RC_CODEC=enc, RC_WORK=f"{HO}/artifacts/{enc}/v1", RC_V1="1", RC_BUDGETS="24,30,36,42",
                      RC_METRIC="dpsnr")
    sys.path.insert(0, f"{HO}/repo")
    for m in [m for m in sys.modules if m.split(".")[0] in ("rclib", "experiments")]:
        del sys.modules[m]
    from experiments import stream_rl as S
    from rclib import clipenv as CE, config as C, streamenv as SE
    assert C.CODEC == enc
    infos = S.load_infos()
    tr = S.split_ids(infos, "train")
    tabs_tr = {g: CE.gop_table(infos[g]) for g in tr}
    c0 = S.train_c0(infos)
    zero = lambda o: SE.ZERO  # noqa: E731
    mse = pickle.load(open(f"{OUT}/luma_gop_mse.pkl", "rb"))[enc]
    lt = {}
    for g in infos:
        b, p = np.full(C.QP_MAX + 1, np.nan), np.full(C.QP_MAX + 1, np.nan)
        b[C.QPS] = infos[g]["curve"]["bits"]
        p[C.QPS] = 10 * np.log10(255.0 ** 2 / np.maximum(mse[g], 1e-10))
        lt[g] = {"bits": b, "psnr": p}

    def luma(rows):
        out = []
        for x in rows:
            tb = [lt[g] for g in x["stream"]]
            q = [int(v) for v in x["qps"]]
            tot = float(sum(t["bits"][v] for t, v in zip(tb, q)))
            assert abs(tot / x["bits"] - 1) < 1e-6, (x["stream"], tot, x["bits"])
            mp = float(CE.pooled([t["psnr"][v] for t, v in zip(tb, q)]))
            out.append({**x, "score": SE.stream_score(tb, tot, mp, x["budget"])[2]})
        return out

    over = lambda rs: 100 * float(np.mean([r["over"] for r in rs]))  # noqa: E731
    sc = lambda rs: np.array([r["score"] for r in rs])  # noqa: E731

    def rule_rows(split, look, m, q, w):
        return S.evaluate(zero, infos, split, look, c0, m, "rule", {"qpd": q, "cw": w, "c0": SE.prior_c0(tabs_tr, tr, q)})

    def load_pol(meth, look):
        base = f"{REPO}/p4/models/{enc}" if "pid" in meth else f"{C.WORK}/results_stream"
        return [pickle.load(open(f"{base}/{meth}_L{look}_s{s}/eval.pkl", "rb"))["res"] for s in range(3)]

    ref = hers(enc)
    res = []
    for look in (2, 0):
        pols = {m: load_pol(m, look) for m in PID[look]}
        pols["bc_ppo_lag (ref)"] = load_pol("bc_ppo_lag", look)
        pols_l = {m: [luma(e["test"]) for e in ev] for m, ev in pols.items()}
        for rname in RULES:
            q, w, vscore, vmargin = TUNED[(enc, look, rname)]
            tpop = POPS["single-clip" if rname == "rule A" else "all"]
            got = float(np.mean(sc(tpop(rule_rows("val", look, vmargin, q, w)))))
            assert abs(got - vscore) < 6e-4, (enc, look, rname, got, vscore)
            R = {s: {m: rule_rows(s, look, m, q, w) for m in MS} for s in ("val", "test")}
            Rl = {m: luma(R["test"][m]) for m in MS}
            for pop, pick in POPS.items():
                for meth, ev in pols.items():
                    vo = np.mean([over(pick(e["val"])) for e in ev])
                    m = min(MS, key=lambda k: abs(over(pick(R["val"][k])) - vo))
                    te = [pick(e["test"]) for e in ev]
                    rt = pick(R["test"][m])
                    assert all(a["stream"] == b["stream"] and a["q0"] == b["q0"] and a["s"] == b["s"] for a, b in zip(te[0], rt))
                    g = np.array([r["group"] for r in rt])
                    po = np.mean([over(t) for t in te])
                    ms = next((k for k in MS if over(pick(R["test"][k])) >= po), MS[-1])
                    row = {"enc": enc, "L": look, "rule": rname, "pop": pop, "meth": meth, "m": m, "ms": ms, "n": len(rt),
                           "over_rl": po, "over_rule": over(rt), "over_sens": over(pick(R["test"][ms]))}
                    for lab, P, RR in (("yuv", [sc(t) for t in te], R["test"]),
                                       ("luma", [sc(pick(t)) for t in pols_l[meth]], Rl)):
                        p = np.mean(P, axis=0)
                        row[lab] = S.cboot(p - sc(pick(RR[m])), g)
                        row[lab + "_s"] = S.cboot(p - sc(pick(RR[ms])), g)
                    h = ref[(look, rname, pop, meth)]
                    assert (m, ms) == (h[0], h[2]) and abs(row["yuv"][0] - h[1]) < 6e-4 and abs(row["yuv_s"][0] - h[3]) < 6e-4, \
                        (enc, look, rname, pop, meth, m, ms, row["yuv"][0], row["yuv_s"][0], h)
                    res.append(row)
                    print(enc, look, rname, pop, meth, f"{row['yuv'][0]:+.3f} -> luma {row['luma'][0]:+.3f}", flush=True)
    assert len(res) == len(ref), (len(res), len(ref))
    sys.path.remove(f"{HO}/repo")
    return res


def fmt(t):
    m, lo, hi = t
    return f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]" + (" *" if lo > 0 or hi < 0 else "")


def sig(t):
    return t[1] > 0 or t[2] < 0


def main():
    rows = run("x264") + run("x265")
    L = ["# Part 4: PID-Lagrangian PPO vs the re-tuned rule (margin matched on val), in luma PSNR "
         "(exp_next/exp7/pid_retuned_luma.py)", "",
         "Sara's Part 4 (team repo p4/pid_vs_retuned.py; p4/README.md \"Part 4\"): rules A (tuned on single-clip val "
         "streams) and B (tuned on all val streams) re-tuned on val; for each policy the rule's margin is the one whose "
         "VAL over-budget rate is closest to the policy's; TEST read once. Every test row (policies and rule) is "
         "rescored here from its per-GOP QPs in luma PSNR of pooled MSE (Pavneet's D50 definition, as pid_luma.md). "
         "Same QPs, same tuning, same matched margins; over-budget rates are bits only, so identical in both "
         "conventions. Policies: 3 seeds averaged; 8-GOP v1 test streams; bc_ppo_lag (fixed lambda, Pavneet's) is a "
         "reference row outside the PID range. CIs: stream_rl.cboot; * = CI excludes 0. Sensitivity (descriptive, "
         "uses test): the rule at the smallest margin whose TEST over-rate is >= the policy's. No encodes.", "",
         "**Paper row: PID - rule B, all streams.**", ""]
    for rname in ("rule B", "rule A"):
        for pop in ("all", "single-clip"):
            L += [f"## RL - {rname} (re-tuned), {pop} streams", "",
                  "| enc | L | policy | margin (val-matched) | YUV 6:1:1 (her output) | luma | over: RL / rule (%) "
                  "| sens. margin | sens. YUV | sens. luma | n |",
                  "|---|---:|---|---:|---|---|---|---:|---|---|---:|"]
            for r in rows:
                if r["rule"] == rname and r["pop"] == pop:
                    L.append(f"| {r['enc']} | {r['L']} | {r['meth']} | {r['m']:.2f} | {fmt(r['yuv'])} | {fmt(r['luma'])} "
                             f"| {r['over_rl']:.1f} / {r['over_rule']:.1f} | {r['ms']:.2f} ({r['over_sens']:.1f} %) "
                             f"| {fmt(r['yuv_s'])} | {fmt(r['luma_s'])} | {r['n']} |")
            L.append("")
    L += ["## Summary: PID runs only (ppo_pid L0 / L2, bc_ppo_pid L2), val-matched margin", "",
          "| enc | comparison | YUV range (CIs excl. 0) | luma range (CIs excl. 0) | sens. YUV | sens. luma |",
          "|---|---|---|---|---|---|"]
    for enc in ("x264", "x265"):
        for rname in ("rule B", "rule A"):
            for pop in ("all", "single-clip"):
                s = [r for r in rows if r["enc"] == enc and r["rule"] == rname and r["pop"] == pop and "ref" not in r["meth"]]
                c = []
                for lab in ("yuv", "luma", "yuv_s", "luma_s"):
                    v = [r[lab][0] for r in s]
                    c.append(f"{min(v):+.2f} to {max(v):+.2f}" + (f" ({sum(sig(r[lab]) for r in s)}/{len(s)})"
                                                                     if lab in ("yuv", "luma") else ""))
                L.append(f"| {enc} | PID - {rname}, {pop} | " + " | ".join(c) + " |")
    for enc in ("x264", "x265"):
        s = [r for r in rows if r["enc"] == enc and r["rule"] == "rule B" and r["pop"] == "all" and "ref" not in r["meth"]]
        y, lu = [r["yuv"][0] for r in s], [r["luma"][0] for r in s]
        L.append(f"\n{enc} paper row (PID - rule B, all streams): YUV {min(y):+.2f} to {max(y):+.2f}; "
                 f"luma {min(lu):+.2f} to {max(lu):+.2f}")
    L += ["", "Checks passed: with the tuned (qpd, cw) taken from her outputs, each tuned point's val score matches her "
          "printed value, and every comparison line of p4/outputs/pid_vs_retuned_<enc>.txt is reproduced in YUV "
          "(val-matched margin, sensitivity margin, RL - rule and sensitivity RL - rule to 3 decimals); the luma tables' "
          "bits equal every row's stored bits."]
    open(f"{OUT}/pid_retuned_luma.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
