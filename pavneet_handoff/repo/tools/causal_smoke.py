"""Smoke test of the causal env (D30): a few real episodes, the offline replay, and a finished policy evaluated in it.
  RC_CAUSAL=1 RC_WORK=<causal work dir> RC_BUDGETS=26,30,34,38,42 python tools/causal_smoke.py <non-causal work dir>
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, env as E, offrl, policies as P, runner  # noqa: E402

def main():
    assert C.CAUSAL
    src_work = sys.argv[1]
    infos = {g: offrl.slim(x) for g, x in runner.Stages("infos").load("infos").items()}
    test = sorted(g for g, x in infos.items() if x["gop"]["split"] == "test")[:3]
    for g in test:
        for b in (C.BUDGET_QPS[0], C.BUDGET_QPS[-1]):
            env = E.RateEnv({g: infos[g]}, k=0)
            env.force(g, b)
            o, _ = env.reset()
            assert np.all(o[E.F_GLOBAL + E.F_FRAME:E.OBS_DIM] == 0), "k=0 must show no future slots"
            done = False
            while not done:
                o, r, done, _, res = env.step(P.ZERO)
            print(f"{g} b={b} s={res['scale']} qbase0={res['qbase0']} B={res['budget_bits']:.0f} bits={res['bits']} "
                  f"score={res['score']:.2f} over={res['over_pct']:.1f}%")
    srch = runner.Stages("search").load("search_train")
    tr = [g for g, x in infos.items() if x["gop"]["split"] == "train" and g in srch][:3]
    for g in tr:
        O, A, R, D, B = offrl.trajectories((infos[g], srch[g], 5, "fixed", (), False, 0, offrl.LOG_CAP, ""))
        print(f"replay {g}: {O.shape[0]} plans kept, obs {O.shape}, acts {A.min() if len(A) else '-'}..{A.max() if len(A) else '-'}")
    ipath = os.path.join(C.WORK, "results_infos", "infos_slim.pkl")
    spec = {"kind": "torch", "path": os.path.join(src_work, "results_rl", "bc_k0_fixed_s0", "policy.pt")}
    rows = P.evaluate(spec, ipath, test, k=0, desc="smoke bc k0 (non-causal model in causal env)")
    print("bc k0 in causal env:", np.mean([r["score"] for r in rows]), [r["scale"] for r in rows])
    fb = {"kind": "fb", "base": spec, "gain": 2.0, "margin": 0.0}
    rows = P.evaluate(fb, ipath, test, k=0, desc="smoke bc+fb")
    print("bc+fb k0 in causal env:", np.mean([r["score"] for r in rows]))
    print("SMOKE OK")


if __name__ == "__main__":
    main()
