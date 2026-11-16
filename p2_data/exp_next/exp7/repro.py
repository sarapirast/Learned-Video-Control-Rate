"""Exp 7 step 1: reproduce Pavneet's stored D34 val numbers with his own code (copy at commit eb08445, see
PROVENANCE.txt) and his stored policies / rule settings. Table lookups only, deterministic -> must match exactly
(or within 0.005 dB). Writes only results_v1/next/exp7/repro_<enc>.md; reads the artifacts in place.

  RC_CODEC=<enc> python exp_next/exp7/repro.py
"""
import os
import pickle
import sys
import time

ENC = os.environ["RC_CODEC"]
SRC = "/scratch1/aayushso/ee599/exp_next/exp7/src_pavneet/pavneet_handoff"
os.environ["RC_WORK"] = f"{SRC}/artifacts/{ENC}/v1"
os.environ.setdefault("RC_V1", "1")
os.environ.setdefault("RC_BUDGETS", "24,30,36,42")
sys.path.insert(0, f"{SRC}/repo")
import numpy as np  # noqa: E402
from stable_baselines3 import PPO  # noqa: E402
from experiments import stream_rl as S  # noqa: E402

OUT = "/scratch1/aayushso/ee599/results_v1/next/exp7"
TOL = 0.005


def compare(new, old):
    assert len(new) == len(old), (len(new), len(old))
    d = np.array([a["score"] - b["score"] for a, b in zip(new, old)])
    return float(np.abs(d).max()), float(np.mean([a["score"] for a in new])), float(np.mean([b["score"] for b in old]))


def main():
    os.makedirs(OUT, exist_ok=True)
    infos = S.load_infos()
    c0 = S.train_c0(infos)
    rs = f"{os.environ['RC_WORK']}/results_stream"
    L = [f"# Exp 7 step 1: reproduce Pavneet's D34 val numbers, {ENC} (exp_next/exp7/repro.py)", "",
         f"His code (eb08445) and stored policies / rule settings; val, all {len(S.cases(infos, 'val'))} cases. Pass = "
         f"max |new - stored| per row <= {TOL} dB.", "",
         "| what | val mean (re-run) | val mean (stored) | max abs row diff | pass |", "|---|---|---|---|---|"]
    zero = lambda o: S.SE.ZERO  # noqa: E731
    rw = pickle.load(open(f"{rs}/rule_wide.pkl", "rb"))
    for look, v in sorted(rw.items()):
        new = S.evaluate(zero, infos, "val", look, c0, v["best"][0], "rule", v["rp"])
        mx, a, b = compare(new, v["rows"]["val"])
        L.append(f"| rule_wide L{look} {v['best']} | {a:+.4f} | {b:+.4f} | {mx:.2e} | {'OK' if mx <= TOL else 'FAIL'} |")
    bl = pickle.load(open(f"{rs}/baselines.pkl", "rb"))
    for look in S.LOOKS:
        t = bl["tune"][("rule", look)]
        new = S.evaluate(zero, infos, "val", look, c0, t["best"][0], "rule", t["rp"])
        mx, a, b = compare(new, bl["rows"][("rule", look, "val")])
        L.append(f"| baselines rule L{look} {t['best']} | {a:+.4f} | {b:+.4f} | {mx:.2e} | {'OK' if mx <= TOL else 'FAIL'} |")
    for d in sorted(x for x in os.listdir(rs) if os.path.isdir(f"{rs}/{x}")):
        ev = pickle.load(open(f"{rs}/{d}/eval.pkl", "rb"))
        pol = PPO.load(f"{rs}/{d}/model.zip", device="cpu").policy
        t0 = time.time()
        new = S.evaluate(lambda o: int(pol.predict(o, deterministic=True)[0]), infos, "val", ev["args"]["look"], c0)
        mx, a, b = compare(new, ev["res"]["val"])
        L.append(f"| {d} | {a:+.4f} | {b:+.4f} | {mx:.2e} | {'OK' if mx <= TOL else 'FAIL'} |")
        print(L[-1], f"({time.time() - t0:.0f}s)", flush=True)
    n_fail = sum("FAIL" in x for x in L)
    L += ["", f"**{'ALL REPRODUCE' if n_fail == 0 else f'{n_fail} DO NOT REPRODUCE: stop, do not build on them'}**", ""]
    open(f"{OUT}/repro_{ENC}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
