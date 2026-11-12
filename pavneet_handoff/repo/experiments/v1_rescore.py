"""D33: copy a finished v1 work dir's infos (budgets, scenes, controller plans) into a new work dir and recompute the
controller plan's score with the current metrics (e.g. with RC_UNDER_PENALTY set). No encoding: the plans, bits and
PSNR are unchanged; only 'score' depends on the reward. The hindsight search starts from this score, so it must match.

  RC_V1=1 RC_WORK=<new> RC_UNDER_PENALTY=1 python experiments/v1_rescore.py --src <old work dir>
"""
import argparse
import os
import pickle
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, metrics  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    assert C.V1, "run with RC_V1=1"
    q = "_quick" if a.quick else ""
    out_dir = os.path.join(C.WORK, f"results_infos{q}")
    out = os.path.join(out_dir, "infos.pkl")
    if os.path.exists(out):
        print(f"{out} exists, nothing to do")
        return
    os.makedirs(out_dir, exist_ok=True)
    infos = pickle.load(open(os.path.join(a.src, f"results_infos{q}", "infos.pkl"), "rb"))
    old, new = [], []
    for x in infos.values():
        for b, s in x["static"].items():
            old.append(s["score"])
            s["score"] = float(metrics.score(s["total_bits"], s["mean_psnr"], x["curve"], x["budget"][b]))
            new.append(s["score"])
    for f in ("controller_model.json",):
        shutil.copy(os.path.join(a.src, f), os.path.join(C.WORK, f))
    for d in ("results_scenes", "results_scenes_quick"):
        if os.path.isdir(os.path.join(a.src, d)) and not os.path.exists(os.path.join(C.WORK, d)):
            shutil.copytree(os.path.join(a.src, d), os.path.join(C.WORK, d))
    tmp = out + ".part"
    pickle.dump(infos, open(tmp, "wb"), protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, out)
    print(f"under penalty {metrics.UNDER_PENALTY} tol {metrics.UNDER_TOL}: controller score {np.mean(old):.2f} -> "
          f"{np.mean(new):.2f} over {len(new)} (GOP, budget) cases")


if __name__ == "__main__":
    main()
