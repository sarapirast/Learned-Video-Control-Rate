"""Parity check for the lfq learners (tracker 30d; v1-data branch, P2 2026-11-10): the env, driven by a search plan
re-expressed around the causal base (offrl.trajectories / env.offsets_for), must reproduce the search's own encode
of that plan exactly (total bits, mean PSNR, score), and plan_observations must match the env's live observations.

  RC_ARM=lfq RC_CODEC=x264 python tools/lfq_parity.py [--n 4] [--split train] [--ks 0,29]
"""
import argparse
import os
import pickle
import sys

os.environ.setdefault("RC_ACT_RANGE", "10")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402

from rclib import config as C, env as E, runner  # noqa: E402

assert C.LFQ_LEARN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--split", default="train")
    ap.add_argument("--ks", default="0,29")
    a = ap.parse_args()
    with open(os.path.join(C.WORK, "results_infos", "infos_learn.pkl"), "rb") as f:
        infos = pickle.load(f)
    srch = runner.Stages("search").load(f"search_{a.split}")
    rng = np.random.default_rng(0)
    ids = [g for g in srch if g in infos]
    ids = [ids[i] for i in rng.choice(len(ids), a.n, replace=False)]
    ok = bad = skipped = 0
    for g in ids:
        for b in C.BUDGET_QPS:
            e = srch[g][b]
            sa = np.asarray(e["actions"])
            qps = np.clip(np.round(e["base_q"] + E.STATIC_OFF + sa[e["best_acts"]]), C.QP_LO, C.QP_HI)
            for k in map(int, a.ks.split(",")):
                acts = E.offsets_for(qps, infos[g]["base"][(b, k)])
                if acts is None:
                    skipped += 1
                    continue
                env = E.RateEnv({g: infos[g]}, k=k)
                env.force(g, b)
                obs = [env.reset()[0]]
                for t, x in enumerate(acts):
                    o, r, done, _, res = env.step(int(x))
                    if not done:
                        obs.append(o)
                po = E.plan_observations(infos[g], b, acts, res["frame_bits"], k=k)
                same = (res["qps"] == [int(q) for q in qps] and res["bits"] == e["total_bits"]
                        and abs(res["psnr"] - e["psnr"]) < 1e-9 and abs(res["score"] - e["best_score"]) < 1e-9
                        and np.allclose(np.stack(obs), po))
                ok += same
                bad += not same
                print(f"{g} b{b} k{k} base {env.base:.2f} (hind {e['base_q']}): bits {res['bits']} vs {e['total_bits']}"
                      f" score {res['score']:.4f} vs {e['best_score']:.4f} reward {res['reward']:+.4f} "
                      f"{'OK' if same else 'MISMATCH'}", flush=True)
    print(f"parity: {ok} OK, {bad} mismatch, {skipped} plans out of range")


if __name__ == "__main__":
    main()
