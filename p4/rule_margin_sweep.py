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
            # TODO: print look, split, m, mean score, share over (mean of r["over"]), mean use
            print(look, split, m,
            f"score {np.mean([r['score'] for r in rows]):+.3f}",
            f"over {100 * np.mean([r['over'] for r in rows]):.1f}%",
            f"use {100 * np.mean([r['use'] for r in rows]):.1f}%")