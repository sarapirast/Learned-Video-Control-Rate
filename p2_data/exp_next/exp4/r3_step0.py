"""Exp 4 R3 step-0 reproduction check (PREREG_BC.md REVISION 2): the PPO policy built as rl.py builds R3 (R2's
architecture, res offset-0 bias init, then load_bc_actor), evaluated deterministically in R3's env (extra f4, drop
"level" only -- o[5..8] present but zero-weighted, res_mean pooled, RC_RES_RECAP=bit), must reproduce the BC-only
rung's fold rows (bc_rows_<enc>_fold.pkl: env with o[5..8] masked) exactly: same QPs, bits, score.

  RC_ARM=res RC_RES_RANGE=6 RC_RES_RECAP=bit RC_CODEC=<enc> ... python exp_next/exp4/r3_step0.py [--n 8] [--k 5]
"""
import argparse
import json
import pickle
import sys

import numpy as np
import torch

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet/experiments")
from rclib import config as C, env as E, offrl  # noqa: E402
import rl  # noqa: E402
from stable_baselines3 import PPO  # noqa: E402

assert C.RES and max(C.ACTIONS) == 6 and C.RES_RECAP == "bit"
EXP5 = "/scratch1/aayushso/ee599/results_v1/next/exp5"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--seeds", default="0,1,2")
    a = ap.parse_args()
    full = pickle.load(open(f"/scratch1/aayushso/rcwork_v1/{C.CODEC}_resh/results_infos/infos.pkl", "rb"))
    mean = json.load(open(f"{EXP5}/shifts_smooth.json"))[f"{C.CODEC}|{a.k}|pooled"]
    rows = [r for r in pickle.load(open(f"{EXP5}/bc_rows_{C.CODEC}_fold.pkl", "rb")) if r["k"] == a.k]
    rng = np.random.default_rng(0)
    ok = tot = 0
    for s in [int(x) for x in a.seeds.split(",")]:
        rs = [r for r in rows if r["seed"] == s]
        pick = [rs[i] for i in rng.choice(len(rs), a.n, replace=False)]
        g0 = pick[0]["gid"]
        env0 = E.make_env({g0: offrl.slim(full[g0])}, k=a.k, extra="f4", drop=("level",), res_mean=mean)
        pk = {"net_arch": {"pi": [256, 256], "vf": [256, 256]}, "activation_fn": torch.nn.ReLU}
        model = PPO("MlpPolicy", env0, seed=s, device="cpu", policy_kwargs=pk, verbose=0)
        n, i0 = len(C.ACTIONS), C.ACTIONS.index(0)
        with torch.no_grad():                                       # rl.py's res init, then BC overrides it
            b = model.policy.action_net.bias
            b.zero_()
            b[i0] = float(np.log(rl.CFG["res_p0"] / (1 - rl.CFG["res_p0"]) * (n - 1)))
        rl.load_bc_actor(model, f"{EXP5}/bc/bc_{C.CODEC}_k{a.k}_s{s}.pt")
        for r in pick:
            g = r["gid"]
            env = E.make_env({g: offrl.slim(full[g])}, k=a.k, extra="f4", drop=("level",), res_mean=mean)
            env.force(g, r["level"], a.k)
            obs, _ = env.reset()
            done = False
            while not done:
                act, _ = model.predict(obs, deterministic=True)
                obs, _, done, _, res = env.step(int(act))
            same = list(res["qps"]) == r["qps"] and res["bits"] == r["bits"] and abs(res["score"] - r["score"]) < 1e-9
            ok += same
            tot += 1
            if not same:
                print("MISMATCH", s, g, r["level"], res["qps"][:10], r["qps"][:10])
    print(f"R3 step 0 {C.CODEC} k{a.k}: PPO with BC weights (o[5..8] live, zero-weighted) reproduces the BC-only rows "
          f"{ok}/{tot}")


if __name__ == "__main__":
    main()
