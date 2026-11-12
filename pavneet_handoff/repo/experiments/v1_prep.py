"""Dataset v1 preparation (D31), after infos + scenes: Aayush's clip-level budgets (budgets.csv, the 'leak-free' ones), the
hindsight constant QP that meets each budget, the controller's rate model fitted on train, and the controller's plan
at each budget (start of the search, so logged plans stay near the residual action range).

  RC_V1=1 RC_WORK=... RC_BUDGETS=24,30,36,42 python experiments/v1_prep.py [--quick]
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import codec, config as C, controller, data, metrics, runner  # noqa: E402
from rclib.runner import log  # noqa: E402


def q_fit(curve, B):
    lb = np.log(np.asarray(curve["bits"], float))
    return float(np.clip(np.interp(-np.log(B), -lb, C.QPS), C.QP_MIN, C.QP_MAX))


def _static(x):
    """The controller's own plan with the whole GOP visible: where the hindsight search starts (the 'static' entry)."""
    p, src, out = data.gop_path(x["gop"]), data.gop_frames(x["gop"]), {}
    fp = np.maximum(np.asarray(x["fp_bits"], float), 8)
    for b, B in x["budget"].items():
        qps, bits = [], []
        for t in range(C.GOP):
            qps.append(controller.decide(t, bits, qps, fp, B, C.GOP - 1))
            r = codec.encode(p, qps, measure=t == C.GOP - 1, src=src)
            bits = [int(v) for v in r["bits"]]
        out[b] = {"plan": qps, "bits": r["bits"], "psnr": r["psnr"], "total_bits": r["total_bits"], "mean_psnr": r["mean_psnr"],
                  "saving": float(metrics.saving(r["total_bits"], r["mean_psnr"], x["curve"])),
                  "score": float(metrics.score(r["total_bits"], r["mean_psnr"], x["curve"], B)), "over": r["total_bits"] > B}
    return x["gop"]["id"], out


def main():
    a = runner.args()
    assert C.V1, "run with RC_V1=1"
    st = runner.Stages("infos", a.quick)
    infos = st.load("infos")
    bud = pd.read_csv(C.V1_BUDGETS).query("encoder == @C.CODEC").set_index(["clip_id", "gop", "level_q0"])["budget_bits"]
    for x in infos.values():
        g = x["gop"]
        x["budget_own"] = {b: int(x["curve"]["bits"][C.QPS.index(b)]) for b in C.BUDGET_QPS}
        x["budget"] = {b: float(bud.loc[(g["clip"], g["v1_gop"], b)]) for b in C.BUDGET_QPS}
        x["qfit"] = {b: q_fit(x["curve"], B) for b, B in x["budget"].items()}
    m = controller.fit(infos)
    json.dump(m, open(os.path.join(C.WORK, "controller_model.json"), "w"), indent=1)
    st_out = dict(runner.pmap(_static, list(infos.values()), desc="controller plans"))
    for g, s in st_out.items():
        infos[g]["static"] = s
    st.save("infos", infos)
    r = [x["budget"][b] / x["budget_own"][b] for x in infos.values() for b in C.BUDGET_QPS]
    log(f"rate model {m}")
    log(f"budget / own spend: median {np.median(r):.2f}, 10-90% {np.percentile(r, 10):.2f}-{np.percentile(r, 90):.2f}")


if __name__ == "__main__":
    main()
