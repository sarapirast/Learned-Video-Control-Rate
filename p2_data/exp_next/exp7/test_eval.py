"""Exp 7 frozen configuration, Part 1 rows (exp_next/final/PREREG.md "Exp 7 frozen configuration"). Table lookups.

8-GOP v1 streams of the split (same-clip + mixed): the selected stream policy (x264 bc_ppo_L2, x265 ppo_L2; seeds 0-2),
the retuned rule (L2 and L0, rule_8_<enc>_v2.pkl) and the rule as reported (rule_wide.pkl). --split test also runs the
16 / 32-GOP windows of the ED / ToS segments (artifacts/<enc>/fresh; stride N / 2 as D35) with the policy, the rule
retuned on the train chains (rule_chain_<enc>_v2.pkl) and the 8-GOP rule as reported.
--split val reproduces the Part 1 selection numbers (select_<enc>.json) as a check.

  RC_CODEC=<enc> python exp_next/exp7/test_eval.py --split val     (check)
  RC_CODEC=<enc> python exp_next/exp7/test_eval.py --split test    (approved final pass only)
Out: results_v1/final/exp7_<split>_<enc>.pkl
"""
import argparse
import json
import os
import pickle
import sys

ENC = os.environ["RC_CODEC"]
SRC = "/scratch1/aayushso/ee599/exp_next/exp7/src_pavneet/pavneet_handoff"
os.environ["RC_WORK"] = f"{SRC}/artifacts/{ENC}/v1"
os.environ.setdefault("RC_V1", "1")
os.environ.setdefault("RC_BUDGETS", "24,30,36,42")
sys.path.insert(0, f"{SRC}/repo")
import numpy as np  # noqa: E402
from stable_baselines3 import PPO  # noqa: E402
from experiments import stream_fresh as F, stream_rl as S  # noqa: E402
from rclib import clipenv as CE, streamenv as SE  # noqa: E402

E7 = "/scratch1/aayushso/ee599/results_v1/next/exp7"
OUT = "/scratch1/aayushso/ee599/results_v1/final"
SELECTED = {"x264": "bc_ppo", "x265": "ppo"}


def rp_for(best, tabs, tr):
    return {"qpd": best[1], "cw": best[2], "c0": SE.prior_c0(tabs, tr, best[1])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("val", "test"), required=True)
    a = ap.parse_args()
    infos = S.load_infos()
    c0 = S.train_c0(infos)
    tr = S.split_ids(infos, "train")
    tabs = {g: CE.gop_table(infos[g]) for g in tr}
    r8 = pickle.load(open(f"{E7}/rule_8_{ENC}_v2.pkl", "rb"))
    rw = pickle.load(open(f"{os.environ['RC_WORK']}/results_stream/rule_wide.pkl", "rb"))
    zero = lambda o: SE.ZERO  # noqa: E731
    pols = {s: PPO.load(f"{os.environ['RC_WORK']}/results_stream/{SELECTED[ENC]}_L2_s{s}/model.zip", device="cpu").policy
            for s in (0, 1, 2)}
    res = {}
    for s, pol in pols.items():
        res[("policy", 8, s)] = S.evaluate(lambda o, p=pol: int(p.predict(o, deterministic=True)[0]), infos, a.split, 2, c0)
    for look in (2, 0):
        res[("rule_retuned", 8, look)] = S.evaluate(zero, infos, a.split, look, c0, r8[look]["best"][0], "rule",
                                                     rp_for(r8[look]["best"], tabs, tr))
        res[("rule_reported", 8, look)] = S.evaluate(zero, infos, a.split, look, c0, rw[look]["best"][0], "rule", rw[look]["rp"])
    if a.split == "val":
        sel = json.load(open(f"{E7}/select_{ENC}.json"))
        pol = np.mean([[r["score"] for r in res[("policy", 8, s)] if r["kind"] == "clip"] for s in (0, 1, 2)], axis=0)
        rule = np.array([r["score"] for r in res[("rule_retuned", 8, 2)] if r["kind"] == "clip"])
        rep = np.array([r["score"] for r in res[("rule_reported", 8, 2)] if r["kind"] == "clip"])
        c = sel["candidates"][SELECTED[ENC]]
        print(f"val check {ENC}: policy {pol.mean():+.6f} vs selection {c['score']:+.6f}; policy - retuned rule "
              f"{(pol - rule).mean():+.6f} vs {c['vs_rule']:+.6f}; - rule as reported {(pol - rep).mean():+.6f} vs "
              f"{c['vs_rule_reported']:+.6f}")
        return
    fresh = pickle.load(open(f"{SRC}/artifacts/{ENC}/fresh/results_infos/infos_slim.pkl", "rb"))
    rc = pickle.load(open(f"{E7}/rule_chain_{ENC}_v2.pkl", "rb"))
    for n in (16, 32):
        for s, pol in pols.items():
            res[("policy", n, s)] = F.evaluate(lambda o, p=pol: int(p.predict(o, deterministic=True)[0]), fresh, n, 2, c0)
        best = rc[(n, 2)]["best"]
        res[("rule_retuned", n, 2)] = F.evaluate(zero, fresh, n, 2, c0, best[0], "rule", rp_for(best, tabs, tr))
        res[("rule_reported", n, 2)] = F.evaluate(zero, fresh, n, 2, c0, rw[2]["best"][0], "rule", rw[2]["rp"])
    os.makedirs(OUT, exist_ok=True)
    dest = f"{OUT}/exp7_{a.split}_{ENC}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    pickle.dump(res, open(dest, "wb"))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
