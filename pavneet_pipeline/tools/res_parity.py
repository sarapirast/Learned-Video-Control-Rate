"""Parity check for the residual arm (RC_ARM=res): with every offset at 0 the env must replay P2's published controller
run (results_v1/controller_real/final2_*, stored in info["ctrl"]) exactly: same per-frame QPs, same total bits, same
score. Run with the v1 job env:
  RC_ARM=res RC_CODEC=x264 source tools/job_env_v1.sh; python tools/res_parity.py [n_gops] [split] [ks]
"""
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, env as E, offrl, runner  # noqa: E402

assert C.RES, "set RC_ARM=res"


def one(item):
    info, gid, b, k = item
    env = E.make_env({gid: offrl.slim(info)}, k=k)   # same slim infos as experiments/rl.py (P2 11-11)
    env.force(gid, b)
    env.reset()
    zero = C.ACTIONS.index(0)
    done = False
    while not done:
        _, _, done, _, res = env.step(zero)
    ref = info["ctrl"][(b, k)]
    return {"gid": gid, "b": b, "k": k, "qps_ok": res["qps"] == ref["qps"] == res["ctrl_qps"],
            "bits_ok": res["bits"] == ref["bits"], "d_score": res["score"] - ref["score"],
            "reward": res["reward"], "score": res["score"]}


def main(n=6, split="val", ks="0,5"):
    with open(os.path.join(C.WORK, "results_infos", "infos.pkl"), "rb") as f:
        infos = pickle.load(f)
    gids = [g for g, x in infos.items() if x["gop"]["split"] == split and x["ctrl"]]
    gids = gids[::max(1, len(gids) // int(n))][:int(n)]
    items = [(infos[g], g, b, int(k)) for g in gids for b in C.BUDGET_QPS for k in ks.split(",")]
    rows = runner.pmap(one, items, desc="parity")
    ok = sum(r["qps_ok"] and r["bits_ok"] and abs(r["d_score"]) < 1e-6 for r in rows)
    for r in rows:
        if not (r["qps_ok"] and r["bits_ok"] and abs(r["d_score"]) < 1e-6):
            print("MISMATCH", r)
    print(f"{ok}/{len(rows)} episodes replay the controller exactly; max |d score| "
          f"{max(abs(r['d_score']) for r in rows):.2e}; reward (should be ~ -lam*over/10 only) mean "
          f"{np.mean([r['reward'] for r in rows]):.4f}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
