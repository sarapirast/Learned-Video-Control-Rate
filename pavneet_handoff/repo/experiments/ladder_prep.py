"""D44 preparation (TA feedback: budgets and initialisation available at decision time), after the original dataset's
infos and scenes. No change to the GOPs, curves or detector; only budgets, the controller and its plans.

1. Budgets from a fixed bitrate ladder: for budget QP b, B_b = the median over TRAIN GOPs of constant-QP bits at b. The
   same B_b for every GOP, so a budget says nothing about the GOP's own cost (D30 used s x the GOP's own bits).
2. The causal online controller's rate model (rclib/controller.py, fit) on train. The controller uses only frame 0 and
   the visible frames, so the base QP no longer comes from a whole-GOP first pass (D30's gop_qhat did).
3. The controller's plan with the whole GOP visible at each budget: the start of the hindsight search, stored as the
   'static' entry (as v1_prep.py does).

  RC_LADDER=1 RC_CODEC=x265 RC_BUDGETS=30,34,38,42 RC_WORK=/scratch1/pbanga/rcwork_ladder/x265 \
      python experiments/ladder_prep.py --src /scratch1/pbanga/rcwork_wide [--quick]
--quick keeps 6 GOPs per split (results_infos_quick) for the debug test; the ladder is still from all train GOPs.
"""
import argparse
import json
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments.v1_prep import _static, q_fit  # noqa: E402
from rclib import config as C, controller, runner  # noqa: E402
from rclib.runner import log  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="work dir whose results_infos/infos.pkl holds the curves (5 budgets)")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    assert C.LADDER, "run with RC_LADDER=1"
    st = runner.Stages("infos", a.quick)
    if st.done("infos"):
        log("infos already prepared; nothing to do")
        return
    infos = pickle.load(open(os.path.join(a.src, "results_infos", "infos.pkl"), "rb"))
    tr = [g for g, x in infos.items() if x["gop"]["split"] == "train"]
    lad = {b: float(np.median([infos[g]["curve"]["bits"][C.QPS.index(b)] for g in tr])) for b in C.BUDGET_QPS}
    if a.quick:
        keep = [g for s in ("train", "val", "test") for g in sorted(g for g, x in infos.items() if x["gop"]["split"] == s)[::97][:6]]
        infos = {g: infos[g] for g in keep}
    n_out = 0
    for x in infos.values():
        cb = np.asarray(x["curve"]["bits"], float)
        x["budget_own"] = {b: int(cb[C.QPS.index(b)]) for b in C.BUDGET_QPS}
        x["budget"] = dict(lad)
        x["qfit"] = {b: q_fit(x["curve"], B) for b, B in lad.items()}
        n_out += sum(int(B > cb.max() or B < cb.min()) for B in lad.values())
    m = controller.fit(infos) if not a.quick else controller.fit(pickle.load(
        open(os.path.join(a.src, "results_infos", "infos.pkl"), "rb")))
    json.dump(m, open(os.path.join(C.WORK, "controller_model.json"), "w"), indent=1)
    json.dump({str(b): v for b, v in lad.items()}, open(os.path.join(C.WORK, "ladder.json"), "w"), indent=1)
    st_out = dict(runner.pmap(_static, list(infos.values()), desc="controller plans"))
    for g, s in st_out.items():
        infos[g]["static"] = s
    st.save("infos", infos)
    q = np.array([x["qfit"][b] for x in infos.values() if x["gop"]["split"] == "test" for b in C.BUDGET_QPS])
    log(f"ladder (bits per GOP): { {b: round(v) for b, v in lad.items()} }")
    log(f"rate model {m}")
    log(f"cases outside the QP 18-50 curve: {n_out} of {len(infos) * len(lad)}; test hindsight constant QP p10/50/90 "
        f"{np.percentile(q, [10, 50, 90]).round(1).tolist()}")
    sc = {b: round(float(np.mean([x["static"][b]["score"] for x in infos.values()])), 2) for b in C.BUDGET_QPS}
    log(f"controller plan (whole GOP visible) mean score by budget: {sc}")


if __name__ == "__main__":
    main()
