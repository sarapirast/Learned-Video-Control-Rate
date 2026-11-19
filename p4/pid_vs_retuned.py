"""PID-Lagrangian PPO vs the RETUNED stream rule at equal reliability, margin matched on VAL (report Table: stream level).

Fixes the original comparison (rule_margin_sweep.py), where the rule stayed on its original grid (qpd at the grid
edge) and the matching margin was read off TEST over-budget rates.

For each lookahead L in {2, 0}, the rule is retuned on val over one wide grid (margin x qpd x cw), twice:
  rule A: tuned on single-clip val streams     rule B: tuned on all val streams (clip + mixed)
Then, for each rule and each population (single-clip, all), the margin is swept with that rule's (qpd, cw) fixed;
for each policy the margin whose VAL over-budget rate is closest to the policy's VAL rate is chosen, and TEST is
read once. Policies: Sara's PID-Lagrangian runs (p4/models: ppo_pid at L 0/2, bc_ppo_pid at L 2), 3 seeds averaged
from their stored eval rows. Pavneet's bc_ppo_lag (fixed lambda) is printed as a reference, outside the PID range.
Sensitivity (descriptive, uses test): the rule at the smallest margin whose TEST over-rate is >= the policy's.

Run from p4/:  RC_V1=1 RC_CODEC=x264 RC_WORK=<copy of pavneet_handoff/artifacts/x264/v1> python -u pid_vs_retuned.py
"""
import os, sys, pickle, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pavneet_handoff", "repo"))
from experiments import stream_rl as S
from rclib import streamenv as SE, clipenv as CE, config as C

infos = S.load_infos()
tr = S.split_ids(infos, "train")
tabs = {g: CE.gop_table(infos[g]) for g in tr}
c0 = S.train_c0(infos)
zero = lambda o: SE.ZERO
QP = (3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0)
CW = (0.015625, 0.0625, 0.25, 1.0, 3.0, 6.0, 12.0, 24.0, 48.0)
MT = (0.96, 0.97, 0.98, 0.99, 1.00)                                   # margins for tuning
MS = (0.88, 0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99, 1.00)     # margins for the reliability sweep
POPS = {"single-clip": lambda rs: [r for r in rs if r["kind"] == "clip"], "all": lambda rs: rs}
TUNE_POP = {"rule A": "single-clip", "rule B": "all"}
PID = {2: ("ppo_pid", "bc_ppo_pid"), 0: ("ppo_pid",)}
score = lambda rs: float(np.mean([r["score"] for r in rs]))
over = lambda rs: 100 * float(np.mean([r["over"] for r in rs]))
c0q = {q: SE.prior_c0(tabs, tr, q) for q in QP}

def rows(split, look, m, q, w):
    return S.evaluate(zero, infos, split, look, c0, m, "rule", {"qpd": q, "cw": w, "c0": c0q[q]})

def load_pol(meth, look):
    base = os.path.join(HERE, "models", C.CODEC) if "pid" in meth else os.path.join(C.WORK, "results_stream")
    return [pickle.load(open(os.path.join(base, f"{meth}_L{look}_s{s}", "eval.pkl"), "rb"))["res"] for s in range(3)]

def compare(ev, R, pick, M):
    vo = np.mean([over(pick(e["val"])) for e in ev])
    m = min(M, key=lambda k: abs(over(pick(R["val"][k])) - vo))                 # matched on VAL
    te = [pick(e["test"]) for e in ev]
    rt = pick(R["test"][m])
    assert all(a["stream"] == b["stream"] and a["q0"] == b["q0"] and a["s"] == b["s"] for a, b in zip(te[0], rt))
    p = np.mean([[r["score"] for r in t] for t in te], axis=0)
    g = np.array([r["group"] for r in rt])
    d = S.cboot(p - np.array([r["score"] for r in rt]), g)
    po = np.mean([over(t) for t in te])
    ms = next((k for k in M if over(pick(R["test"][k])) >= po), M[-1])          # sensitivity: rule >= RL over-rate
    ds = S.cboot(p - np.array([r["score"] for r in pick(R["test"][ms])]), g)
    return vo, m, p.mean(), po, score(rt), over(rt), d, ms, over(pick(R["test"][ms])), ds

star = lambda d: " *" if d[1] > 0 or d[2] < 0 else ""
fmt = lambda d: f"{d[0]:+.3f} [{d[1]:+.3f}, {d[2]:+.3f}]{star(d)}"
summary = []

for look in (2, 0):
    grid = {(m, q, w): rows("val", look, m, q, w) for m in MT for q in QP for w in CW}
    tuned = {}
    for rname, pop in TUNE_POP.items():
        val = {k: score(POPS[pop](v)) for k, v in grid.items()}
        best = max(val, key=val.get)
        edge = best[0] == MT[0] or best[1] in (QP[0], QP[-1]) or best[2] in (CW[0], CW[-1])
        tuned[rname] = best[1:]
        top = "; ".join(f"{k}: {v:+.3f}" for k, v in sorted(val.items(), key=lambda kv: -kv[1])[:5])
        print(f"[{C.CODEC} L={look}] {rname} tuned on {pop} val streams: margin {best[0]}, qpd {best[1]}, cw {best[2]}"
              f" -> val {val[best]:+.3f}{'  (EDGE)' if edge else ''}\n   top 5: {top}")
    pols = {m: load_pol(m, look) for m in PID[look]}
    pols["bc_ppo_lag (ref)"] = load_pol("bc_ppo_lag", look)
    for rname, (q, w) in tuned.items():
        R = {s: {m: rows(s, look, m, q, w) for m in MS} for s in ("val", "test")}
        for pop, pick in POPS.items():
            print(f"\n== {C.CODEC} L={look}  {rname} (qpd {q}, cw {w}), {pop} streams ==")
            print("   rule test curve: " + "  ".join(f"{m}:{score(pick(R['test'][m])):+.3f}/{over(pick(R['test'][m])):.1f}%" for m in MS))
            for meth, ev in pols.items():
                vo, m, ps, po, rs, ro, d, ms, mo, ds = compare(ev, R, pick, MS)
                print(f"   {meth:17s} val over {vo:4.1f}% -> margin {m:.2f} | test: RL {ps:+.3f} / {po:4.1f}% over, "
                      f"rule {rs:+.3f} / {ro:4.1f}% over | RL - rule {fmt(d)} | sens. rule@{ms:.2f} ({mo:.1f}%): {fmt(ds)}")
                if "ref" not in meth:
                    summary.append((rname, pop, look, meth, d, ds))

print(f"\n==== {C.CODEC} SUMMARY: PID-Lagrangian runs only (ppo_pid L0/L2, bc_ppo_pid L2), val-matched margin ====")
for rname in TUNE_POP:
    for pop in POPS:
        s = [x for x in summary if x[0] == rname and x[1] == pop]
        lo, hi = min(x[4][0] for x in s), max(x[4][0] for x in s)
        sig = sum(x[4][1] > 0 or x[4][2] < 0 for x in s)
        slo, shi = min(x[5][0] for x in s), max(x[5][0] for x in s)
        print(f"   PID - {rname} (retuned), {pop:11s}: {lo:+.2f} to {hi:+.2f}  ({sig}/{len(s)} CIs exclude 0)"
              f"   | sensitivity: {slo:+.2f} to {shi:+.2f}")