"""Retune the stream rule at N=16/32, leave-one-film-out: tune on one film's segments, test on the other."""
import os, sys, pickle, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pavneet_handoff", "repo"))
from experiments import stream_fresh as F, stream_rl as S
from rclib import streamenv as SE, clipenv as CE

V1, FR = os.environ["RC_V1WORK"], os.environ["RC_WORK"]
load = lambda *p: pickle.load(open(os.path.join(*p), "rb"))

# v1 train GOPs -> the rule's c0 prior for each slope (same as stream_rule_wide.py)
v1inf = load(V1, "results_infos", "infos_slim.pkl")
tr = [g for g, x in v1inf.items() if x["gop"]["split"] == "train" and x["gop"]["family"] != "splice"]
tabs = {g: CE.gop_table(v1inf[g]) for g in tr}
c0 = load(V1, "results_stream", "baselines.pkl")["c0"]

fresh = load(FR, "results_infos", "infos_slim.pkl")
film = lambda pre: {g: x for g, x in fresh.items() if x["gop"]["clip"].startswith(pre)}
FILMS = {"ed_": film("ed_"), "tos_": film("tos_")}

QP, CW, M = (4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0), (0.1, 0.25, 0.5, 1.0, 3.0, 6.0, 12.0, 24.0, 48.0, 100.0, 200.0), (0.98, 1.00, 1.02)
c0q = {q: SE.prior_c0(tabs, tr, q) for q in QP}
zero = lambda o: SE.ZERO

def rule_rows(infos, n, look, m, q, w):
    return F.evaluate(zero, infos, n, look, c0, m, "rule", {"qpd": q, "cw": w, "c0": c0q[q]})

for n in (16, 32):
    stored = load(FR, "results_stream_fresh", f"n{n}.pkl")   # PPO / bc_ppo rows, keyed (method, L, seed)
    for look in (0, 2):
        for tune_on, test_on in (("ed_", "tos_"), ("tos_", "ed_")):
            val = {}
            for m in M:
                for q in QP:
                    for w in CW:
                        rows= rule_rows(FILMS[tune_on],n,look,m,q,w)
                        val[(m,q,w)]= np.mean([r["score"] for r in rows])
            best = max(val, key=val.get)
            top = sorted(val.items(), key=lambda kv: -kv[1])[:5]
            print("   top 5:", "; ".join(f"{k}: {v:+.3f}" for k, v in top))
            print(f"n={n} L={look} tuned on {tune_on}:best{best} -> {val[best]:+.3f} dB")
            m,q,w= best
            test_rows= rule_rows(FILMS[test_on],n,look,m,q,w)
            edge = (m == M[0]) or (q in (QP[0], QP[-1])) or (w in (CW[0], CW[-1]))
            if edge:
                print("  WARNING: best is on the grid edge -> widen that range and rerun")            
            pick = lambda rows: [r for r in rows if r["group"].startswith(test_on)]
            old_rule = pick(stored[("rule", look, 0)])
            new = np.array([r["score"] for r in test_rows])
            old = np.array([r["score"] for r in old_rule])
            groups = np.array([r["group"] for r in test_rows])
            print(f"  test on {test_on}: rule old {old.mean():+.3f} -> retuned {new.mean():+.3f} dB")
            for meth in ("ppo", "bc_ppo"):
                seeds = [pick(stored[(meth, look, s)]) for s in (0, 1, 2)]
                assert all(a["stream"] == b["stream"] and a["q0"] == b["q0"] and a["s"] == b["s"]
                           for a, b in zip(test_rows, seeds[0]))
                pol = np.mean([[r["score"] for r in rows] for rows in seeds], axis=0)
                d_old, d_new = S.cboot(pol - old, groups), S.cboot(pol - new, groups)
                print(f"  {meth:7s} vs old rule:     {d_old[0]:+.3f} [{d_old[1]:+.3f}, {d_old[2]:+.3f}]")
                print(f"  {meth:7s} vs retuned rule: {d_new[0]:+.3f} [{d_new[1]:+.3f}, {d_new[2]:+.3f}]")