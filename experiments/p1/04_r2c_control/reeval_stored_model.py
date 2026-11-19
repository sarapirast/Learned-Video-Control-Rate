"""reeval_stored_model.py: evaluate one of Aayush's STORED k5 models on val with TODAY's code (this branch's rclib, shim
backend) and compare with the evaluation rows he stored when he trained it. No training.
Tells apart "the environment / evaluation changed" (his own model gives different QPs or scores today) from "only
training changed" (his model gives exactly his stored rows today, so the difference is in how models were trained).
Inputs: Aayush's run folder (read-only): model.zip + eval.pkl (its args give the env settings). Env settings for the res
arm come from ../03_r3_lookahead/env.sh (RC_RES_RECAP=bit etc.); the k5 mean shift equals Aayush's (checked in 03).
Output: printed comparison; also written to /scratch1/ahhanagu/ee599/results/r3_kcurve/<run name>_reeval_check.txt
x265: P1_ENC=x265 before sourcing env.sh (CLI backend); set RC_SHIFTS to the shifts file the stored run used.
Run (compute node, ~2 min per model):
  source ../03_r3_lookahead/env.sh; RC_WORKERS=2 $PY -I reeval_stored_model.py <run name>
"""
import json
import os
import pickle
import sys

sys.path.insert(0, "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/pavneet_pipeline")
sys.path.insert(0, "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate")   # x264env (shim backend); -I ignores PYTHONPATH
from rclib import config as C, policies as P, runner  # noqa: E402

STORED = "/scratch1/aayushso/rcwork_v1/{enc}_resh/results_rl/{name}"     # encoder from RC_CODEC (env.sh P1_ENC)
OUT = "/scratch1/ahhanagu/ee599/results/r3_kcurve/{name}_reeval_check.txt"


def main():
    name = sys.argv[1]
    d = STORED.format(enc=C.CODEC, name=name)
    ev = pickle.load(open(f"{d}/eval.pkl", "rb"))
    a = ev["args"]
    assert C.RES and C.RES_RECAP == "bit" and max(C.ACTIONS) == 6 and a["k"] == 5 and a["mode"] == "fixed"
    # env arguments exactly as rl.py builds them for evaluation (main(): envkw, then k_sampler=None)
    envkw = {"k": a["k"], "mode": a["mode"], "drop": tuple(x for x in a["drop"].split(",") if x), "prior": a["prior"],
             "extra": a["extra"], "k_sampler": None}
    if a["res_mean"]:
        envkw["res_mean"] = json.load(open(os.environ["RC_SHIFTS"]))[f"{C.CODEC}|{a['k']}|{a['res_mean']}"]
    ipath = os.path.join(runner.Stages("infos").dir, "infos_slim.pkl")
    stored = {(r["gid"], r["budget"]): r for r in ev["res"][("fixed", a["k"], "val")]}
    ids = sorted({g for g, _ in stored})
    rows = P.evaluate({"kind": "sb3", "path": f"{d}/model.zip", "algo": "ppo"}, ipath, ids, desc=f"reeval {name}",
                      **envkw)
    q = sum(list(r["qps"]) == list(stored[(r["gid"], r["budget"])]["qps"]) for r in rows)
    s = sum(abs(r["score"] - stored[(r["gid"], r["budget"])]["score"]) < 1e-9 for r in rows)
    lines = [f"{name}: Aayush's stored model re-evaluated with today's code (backend {os.environ.get('RC_BACKEND')}):",
             f"  identical QPs {q}/{len(rows)}, identical score {s}/{len(rows)} vs his stored eval rows"]
    open(OUT.format(name=name), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
