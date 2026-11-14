"""Trace the tuned rule's quality vs over-budget trade-off by sweeping its margin (v1 val/test)."""
import os, sys, pickle, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pavneet_handoff", "repo"))
from experiments import stream_rl as S
from rclib import streamenv as SE

infos = S.load_infos()
base = pickle.load(open(os.path.join(S.C.WORK, "results_stream", "baselines.pkl"), "rb"))
c0 = base["c0"]
zero = lambda o: SE.ZERO

for look in (2, 0):
    rp = base["tune"][("rule", look)]["rp"]          # keep the tuned slope / prior, vary only the margin
    for split in ("val", "test"):
        for m in (0.88, 0.90, 0.92, 0.94, 0.96, 0.98, 1.00):
            rows = S.evaluate(zero, infos, split, look, c0, m, "rule", rp)
            print(look, split, m,
            f"score {np.mean([r['score'] for r in rows]):+.3f}",
            f"over {100 * np.mean([r['over'] for r in rows]):.1f}%",
            f"use {100 * np.mean([r['use'] for r in rows]):.1f}%")
    rule = S.evaluate(zero, infos, "test", look, c0, 0.96, "rule", rp)
    seeds = [pickle.load(open(os.path.join(S.C.WORK, "results_stream", f"ppo_pid_L{look}_s{s}", "eval.pkl"), "rb"))["res"]["test"] for s in (0, 1, 2)]
    assert all(a["stream"] == b["stream"] and a["q0"] == b["q0"] and a["s"] == b["s"] for a, b in zip(rule, seeds[0]))
    pid = np.mean([[r["score"] for r in rows] for rows in seeds], axis=0)
    diff = pid - np.array([r["score"] for r in rule])
    groups = np.array([r["group"] for r in rule])
    print(look, "ppo_pid vs rule@0.96:", S.cboot(diff, groups))    
    lag_seeds = [pickle.load(open(os.path.join(S.C.WORK, "results_stream", f"bc_ppo_lag_L{look}_s{s}", "eval.pkl"), "rb"))["res"]["test"] for s in (0, 1, 2)]
    lag = np.mean([[r["score"] for r in rows] for rows in lag_seeds], axis=0)
    print(look, "bc_ppo_lag vs rule@0.96:", S.cboot(lag - np.array([r["score"] for r in rule]), groups))
    if look == 2:
        bp_seeds = [pickle.load(open(os.path.join(S.C.WORK, "results_stream", f"bc_ppo_pid_L2_s{s}", "eval.pkl"), "rb"))["res"]["test"]
                    for s in (0, 1, 2)]
        bp = np.mean([[r["score"] for r in rows] for rows in bp_seeds], axis=0)
        print(look, "bc_ppo_pid vs rule@0.96:", S.cboot(bp - np.array([r["score"] for r in rule]), groups))
        print(look, "bc_ppo_pid vs bc_ppo_lag:", S.cboot(bp - lag, groups))