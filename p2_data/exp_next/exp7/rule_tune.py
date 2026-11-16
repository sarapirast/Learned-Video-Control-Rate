"""Exp 7 Part 1a / 1b: retune Pavneet's remaining-budget rule (exp_next/exp7/PREREG.md). Table lookups only.

  RC_CODEC=<enc> python exp_next/exp7/rule_tune.py --part 8       val same-clip 8-GOP streams, L 0 / 2
  RC_CODEC=<enc> python exp_next/exp7/rule_tune.py --part chain   16 / 32-GOP windows (stride 4) of the train chains
                                                                    bbb and sintel (clips in clip order; segments are
                                                                    far apart in the films, so each join acts like a cut)
Grid: margin 0.94-1.02 step 0.01, qpd 2.5-4.5 + 5.0, 5.5, 6.0, 7.0, cw 1, 3, 6, 12, 24; widened in any direction
whose optimum sits on the edge (margin +-0.01, qpd +1.0 / -0.5, cw x2 / /2) until interior (at most 6 rounds).
Objective: mean score over the cases (Pavneet's tuning objective, restricted to the pre-registered population).
Out: results_v1/next/exp7/rule_<part>_<enc>.pkl / .md
"""
import argparse
import itertools
import os
import pickle
import sys
from multiprocessing import Pool

ENC = os.environ["RC_CODEC"]
SRC = "/scratch1/aayushso/ee599/exp_next/exp7/src_pavneet/pavneet_handoff"
os.environ["RC_WORK"] = f"{SRC}/artifacts/{ENC}/v1"
os.environ.setdefault("RC_V1", "1")
os.environ.setdefault("RC_BUDGETS", "24,30,36,42")
sys.path.insert(0, f"{SRC}/repo")
import numpy as np  # noqa: E402
from experiments import stream_rl as S  # noqa: E402
from rclib import clipenv as CE, streamenv as SE  # noqa: E402

OUT = "/scratch1/aayushso/ee599/results_v1/next/exp7"
CHAINS = {"train": ("bbb", "sintel"), "val": ("sita",)}
_G = {}


def chain_cases(infos, groups, n, stride=4):
    out = []
    for grp in groups:
        gs = sorted((g for g, x in infos.items() if x["gop"]["group"] == grp),
                    key=lambda g: (infos[g]["gop"]["clip"], infos[g]["gop"]["start"]))
        for i in range(0, len(gs) - n + 1, stride):
            out += [("chain", grp, tuple(gs[i:i + n]), q0, s) for q0 in SE.LEVELS for s in SE.EVAL_S]
    return out


def run_cases(look, m, rp, n):
    infos, cases = _G["infos"], _G["cases"]
    env = SE.StreamEnv(infos, _G["ids"], look=look, c0=_G["c0"], margin=m, mode="rule", rp=rp, n=n)
    rows = []
    for kind, grp, st, q0, s in cases:
        env.force(st, q0, s)
        env.reset()
        done = False
        while not done:
            _, _, done, _, res = env.step(SE.ZERO)
        rows.append({**res, "kind": kind, "group": grp})
    return rows


def score(args):
    look, n, (m, q, w) = args
    rp = {"qpd": q, "cw": w, "c0": _G["c0q"](q)}
    return (m, q, w), float(np.mean([r["score"] for r in run_cases(look, m, rp, n)]))


def init(infos, cases, ids, c0, tabs, tr):
    cache = {}

    def c0q(q):
        if q not in cache:
            cache[q] = SE.prior_c0(tabs, tr, q)
        return cache[q]
    _G.update(infos=infos, cases=cases, ids=ids, c0=c0, c0q=c0q)


def tune(look, n, workers):
    M = [round(0.94 + 0.01 * i, 2) for i in range(9)]
    Q = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0]
    W = [1.0, 3.0, 6.0, 12.0, 24.0]
    val, rounds = {}, []
    with Pool(workers) as p:
        for r in range(10):
            todo = [(look, n, k) for k in itertools.product(M, Q, W) if k not in val]
            val.update(dict(p.map(score, todo, chunksize=4)))
            best = max(val, key=val.get)
            edges = {"m": (best[0] == min(M), best[0] == max(M)), "q": (best[1] == min(Q), best[1] == max(Q)),
                     "w": (best[2] == min(W), best[2] == max(W))}
            rounds.append((len(val), best, val[best], edges))
            print(ENC, f"L{look} n{n} round {r}: {len(val)} settings, best {best} {val[best]:+.4f}, edges {edges}", flush=True)
            if not any(any(e) for e in edges.values()):
                break
            if edges["m"][0]: M.insert(0, round(M[0] - 0.01, 2))      # noqa: E701
            if edges["m"][1]: M.append(round(M[-1] + 0.01, 2))        # noqa: E701
            if edges["q"][0] and Q[0] > 1.0: Q.insert(0, Q[0] - 0.5)  # noqa: E701
            if edges["q"][1]: Q.append(Q[-1] + 1.0)                   # noqa: E701
            if edges["w"][0] and W[0] > 1e-6:                         # cw -> 0: prior only for the first GOP
                W.insert(0, W[0] / 4 if W[0] / 4 > 0.004 else 1e-6)
            if edges["w"][1]: W.append(W[-1] * 2)                     # noqa: E701
    best = max(val, key=val.get)
    return {"val": val, "best": best, "score": val[best], "rounds": rounds,
            "interior": not any(any(e) for e in rounds[-1][3].values()),
            "at_cw_limit": best[2] <= 1e-6,      # cw at its natural lower bound (0+): counts as resolved
            "rp": {"qpd": best[1], "cw": best[2], "c0": _G["c0q"](best[1])}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("8", "chain"), required=True)
    ap.add_argument("--tag", default="", help="output name suffix (v2: cw widened to 1e-6)")
    ap.add_argument("--workers", type=int, default=max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", 2))))
    a = ap.parse_args()
    infos = S.load_infos()
    c0 = S.train_c0(infos)
    tr = S.split_ids(infos, "train")
    tabs = {g: CE.gop_table(infos[g]) for g in tr}
    dest = f"{OUT}/rule_{a.part}_{ENC}{'_' + a.tag if a.tag else ''}"
    assert not os.path.exists(dest + ".pkl"), f"{dest}.pkl exists; never overwrite"
    res, L = {}, [f"# Exp 7 rule retuning, part {a.part}, {ENC} (exp_next/exp7/rule_tune.py)", ""]
    rw = pickle.load(open(f"{os.environ['RC_WORK']}/results_stream/rule_wide.pkl", "rb"))
    if a.part == "8":
        cases = [c for c in S.cases(infos, "val") if c[0] == "clip"]
        init(infos, cases, S.split_ids(infos, "val"), c0, tabs, tr)
        L += [f"Val same-clip 8-GOP streams: {len(cases)} cases. 'As reported' = rule_wide.pkl (tuned by Pavneet on all "
              "val 8-GOP cases incl. mixed).", "",
              "| L | as reported (m, qpd, cw) | its same-clip val score | retuned (m, qpd, cw) | retuned score | interior | settings tried |",
              "|---|---|---|---|---|---|---|"]
        for look in S.LOOKS:
            r = tune(look, SE.N_GOP, a.workers)
            rep = rw[look]
            rep_score = float(np.mean([x["score"] for x in run_cases(look, rep["best"][0], rep["rp"], SE.N_GOP)]))
            r["as_reported"] = {"best": rep["best"], "rp": rep["rp"], "score": rep_score}
            res[look] = r
            L.append(f"| {look} | {rep['best']} | {rep_score:+.4f} | {r['best']} | {r['score']:+.4f} | {r['interior'] or r['at_cw_limit']}{' (cw at 0+ limit)' if r['at_cw_limit'] else ''} | {len(r['val'])} |")
    else:
        L += ["Train chains bbb + sintel (6 clips each, in clip order; segments far apart in the films, so every join "
              "every 10 GOPs acts like a scene cut), windows of 16 / 32 GOPs, stride 4. Descriptive val check on the "
              "sita chain with the train-chain settings.", "",
              "| N | L | retuned (m, qpd, cw) | train-chain score | interior | sita (val) score, retuned | sita, 8-GOP rule as reported |",
              "|---|---|---|---|---|---|---|"]
        for n in (16, 32):
            for look in S.LOOKS:
                cases = chain_cases(infos, CHAINS["train"], n)
                ids = [g for g, x in infos.items() if x["gop"]["group"] in CHAINS["train"]]
                r = tune_chain(look, n, a.workers, infos, cases, ids, c0, tabs, tr)
                vcases = chain_cases(infos, CHAINS["val"], n)
                vids = [g for g, x in infos.items() if x["gop"]["group"] in CHAINS["val"]]
                init(infos, vcases, vids, c0, tabs, tr)
                sita = float(np.mean([x["score"] for x in run_cases(look, r["best"][0], r["rp"], n)]))
                rep = rw[look]
                sita_rep = float(np.mean([x["score"] for x in run_cases(look, rep["best"][0], rep["rp"], n)]))
                r.update(sita=sita, sita_as_reported=sita_rep, n_cases=len(cases), n_val_cases=len(vcases))
                res[(n, look)] = r
                L.append(f"| {n} | {look} | {r['best']} | {r['score']:+.4f} | {r['interior'] or r['at_cw_limit']}{' (cw at 0+ limit)' if r['at_cw_limit'] else ''} | {sita:+.4f} | {sita_rep:+.4f} |")
    pickle.dump(res, open(dest + ".pkl", "wb"))
    open(dest + ".md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


def tune_chain(look, n, workers, infos, cases, ids, c0, tabs, tr):
    init(infos, cases, ids, c0, tabs, tr)
    return tune(look, n, workers)


if __name__ == "__main__":
    main()
