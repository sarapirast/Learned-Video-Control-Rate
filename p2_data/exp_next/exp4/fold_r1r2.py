"""Exp 4 R3 precondition (PREREG_BC.md REVISION 1): fold evaluation of the stored 180k R1 / R2 models at k5.
R2's setup is used for R3 unless R2 clearly loses to R1 on the fold (R2 - R1 95% clip CI entirely below 0).
Evaluation only, each run's own stored env settings, deterministic, train-select fold (8 clips, 75 GOPs).

  R2: RC_ARM=res RC_RES_RANGE=6 RC_CTRL_SETTING=<final4> RC_WORK=rcwork_v1/<enc>_resh ... python fold_r1r2.py --group R2
  R1: RC_ARM=res               RC_CTRL_SETTING=<final4> RC_WORK=rcwork_v1/<enc>_resh ... python fold_r1r2.py --group R1
  python -I fold_r1r2.py --report        (after all four jobs)
Out: results_v1/next/exp4/fold_<group>_<enc>.pkl = {(k, seed): rows}; fold_r1r2.md
"""
import argparse
import json
import os
import pickle
import sys

ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/next/exp4"
TMPL = {"R2": "res_k{k}_fixed_f4_lam0.17_st180k_r6_s{s}", "R1": "res_k{k}_fixed_lam0.17_st180k_s{s}"}


def run(group, ks, seeds, workers):
    sys.path.insert(0, f"{ROOT}/repo-pavneet")
    from rclib import config as C, policies as P, runner
    assert C.RES and max(C.ACTIONS) == (6 if group == "R2" else 3) and not C.RES_RECAP
    assert os.environ.get("RC_CTRL_SETTING") == "1.0:6:1.0:2:3:4:1:1:1:0:3"
    ipath = os.path.join(runner.Stages("infos").dir, "infos_slim.pkl")
    infos = pickle.load(open(ipath, "rb"))
    fold = set(json.load(open(f"{ROOT}/exp_next/folds.json"))["train_select_clips"])
    gids = sorted(g for g, x in infos.items() if x["gop"]["split"] == "train" and x["gop"]["clip"] in fold)
    dest = f"{OUT}/fold_{group}_{C.CODEC}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    res = {}
    for k in ks:
        for s in seeds:
            name = TMPL[group].format(k=k, s=s)
            ev = pickle.load(open(os.path.join(C.results_dir("rl"), name, "eval.pkl"), "rb"))
            ra = ev["args"]
            assert ra["k"] == k and ra["mode"] == "fixed"
            envkw = {"k": k, "mode": "fixed", "drop": tuple(x for x in ra["drop"].split(",") if x),
                     "prior": ra["prior"], "extra": ra.get("extra") or "", "k_sampler": None}
            res[(k, s)] = P.evaluate(ev["spec"], ipath, gids, workers=workers, desc=f"fold {name}", **envkw)
            print(f"{C.CODEC} {name}: {len(res[(k, s)])} fold episodes", flush=True)
    os.makedirs(OUT, exist_ok=True)
    pickle.dump(res, open(dest + ".part", "wb"))
    os.replace(dest + ".part", dest)
    print(f"-> {dest}")


def report():
    import numpy as np
    import pandas as pd
    sys.path.insert(0, f"{ROOT}/exp_next/exp5")
    from shift_report import boot, fmt
    rows = []
    for enc in ("x264", "x265"):
        inf = pickle.load(open(f"/scratch1/aayushso/rcwork_v1/{enc}_resh/results_infos/infos.pkl", "rb"))
        for grp in ("R1", "R2"):
            for (k, s), rr in pickle.load(open(f"{OUT}/fold_{grp}_{enc}.pkl", "rb")).items():
                for r in rr:
                    cv, B = inf[r["gid"]]["curve"], inf[r["gid"]]["budget"][r["budget"]]
                    rows.append({"enc": enc, "grp": grp, "k": k, "seed": s, "gid": r["gid"],
                                 "clip": inf[r["gid"]]["gop"]["clip"], "level": r["budget"], "score": r["score"],
                                 "final4": r["static_score"], "hole": B > max(cv["bits"])})
    d = pd.DataFrame(rows)
    d = d[~d.hole]
    p = d.pivot_table(index=["enc", "k", "gid", "clip", "level"], columns="grp", values="score").reset_index()
    f4 = d.groupby(["enc", "k", "gid", "level"]).final4.first().reset_index()
    p = p.merge(f4, on=["enc", "k", "gid", "level"])
    diff = p.R2 - p.R1
    pooled = boot(diff, p["clip"])
    L = ["# Exp 4 R3 precondition: R2 vs R1 on the fold, k5 (exp_next/exp4/fold_r1r2.py)", "",
         "Stored 180k models, seeds averaged per episode, paired, 95% clip bootstrap over the 8 fold clips, hole "
         "excluded. Rule (PREREG_BC.md REVISION 1): R2's setup unless R2 - R1 CI is entirely below 0.", "",
         f"- R2 - R1 pooled: {fmt(pooled)} (n {len(p)})",
         *[f"- {e}: R2 - R1 {fmt(boot(x.R2 - x.R1, x['clip']))}; R2 - final4 {fmt(boot(x.R2 - x.final4, x['clip']))}; "
           f"R1 - final4 {fmt(boot(x.R1 - x.final4, x['clip']))}" for e, x in p.groupby("enc")],
         f"- **{'R2 CLEARLY LOSES: R3 as designed cannot run (BC has R2 shape)' if pooled[2] < 0 else 'R2 setup stands for R3'}**",
         ""]
    open(f"{OUT}/fold_r1r2.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=tuple(TMPL))
    ap.add_argument("--ks", default="5")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        return report()
    run(a.group, [int(x) for x in a.ks.split(",")], [int(x) for x in a.seeds.split(",")], a.workers)


if __name__ == "__main__":
    main()
