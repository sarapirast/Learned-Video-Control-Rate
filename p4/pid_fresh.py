"""Budget reliability on long fresh-film streams: PID policies vs fixed-lambda, PPO and the rule's margin curve."""
import os, sys, pickle, numpy as np, torch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pavneet_handoff", "repo"))
from experiments import stream_fresh as F, stream_rl as S
from rclib import streamenv as SE
from stable_baselines3 import PPO

V1, FR = os.environ["RC_V1WORK"], os.environ["RC_WORK"]
load = lambda *p: pickle.load(open(os.path.join(*p), "rb"))
torch.set_num_threads(1)
fresh = load(FR, "results_infos", "infos_slim.pkl")
base = load(V1, "results_stream", "baselines.pkl")
c0, rp = base["c0"], base["tune"][("rule", 2)]["rp"]
LOOK = 2
METHODS = sys.argv[1:] or ["bc_ppo_pid", "bc_ppo_lag", "ppo"]

def summary(rows):
    return (np.mean([r["score"] for r in rows]), 100 * np.mean([r["over"] for r in rows]),
            100 * np.mean([r["use"] for r in rows]))

for n in (8, 16, 32):
    print(f"\n== N={n}, L={LOOK} ==")
    rules = {}
    for m in (0.92, 0.94, 0.95, 0.96, 0.965, 0.97, 0.975, 0.98, 0.99, 1.00):
        rules[m] = F.evaluate(lambda o: SE.ZERO, fresh, n, LOOK, c0, m, "rule", rp)
        print("  rule m=%.3f   score %+.3f  over %4.1f%%  use %.1f%%" % ((m,) + summary(rules[m])))
    groups = np.array([r["group"] for r in rules[0.96]])
    rover = {m: summary(rows)[1] for m, rows in rules.items()}
    for meth in METHODS:
        seeds = []
        for s in (0, 1, 2):
            pol = PPO.load(os.path.join(V1, "results_stream", f"{meth}_L{LOOK}_s{s}", "model.zip"), device="cpu").policy
            seeds.append(F.evaluate(lambda o: int(pol.predict(o, deterministic=True)[0]), fresh, n, LOOK, c0))
        assert all(a["stream"] == b["stream"] and a["q0"] == b["q0"] and a["s"] == b["s"]
                   for a, b in zip(rules[0.96], seeds[0]))
        sc = np.mean([[r["score"] for r in rows] for rows in seeds], axis=0)
        over = np.mean([summary(rows)[1] for rows in seeds]); use = np.mean([summary(rows)[2] for rows in seeds])
        m = min(rover, key=lambda k: abs(rover[k] - over))          # rule margin with the closest over rate
        d = S.cboot(sc - np.array([r["score"] for r in rules[m]]), groups)
        print(f"  {meth:12s} score {sc.mean():+.3f}  over {over:4.1f}%  use {use:.1f}%   "
              f"vs rule@{m:.3f} ({rover[m]:.1f}% over): {d[0]:+.3f} [{d[1]:+.3f}, {d[2]:+.3f}]")