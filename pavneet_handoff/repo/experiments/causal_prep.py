"""Causal per-GOP setting (D30), preparation and checks. No encodes.

1. Fit the GOP-level rate model on train STATIC encodes (least squares, env.gop_features):
   log2(STATIC bits / total first-pass bits) = w0 . x + (q - 30) w1 . x. Written to $RC_WORK/causal_prior.json.
2. How good the causal base QP is (s = 1): model QP - b on train and test.
3. The causal flags with every frame visible must equal the stored flags; share of frames whose stored flags differ
   from what the detector knows at k = 0 (what the leak contained).
4. Share of logged search plans that stay inside -3..3 when re-expressed on the causal base QP (offline data).

  RC_CAUSAL=1 RC_WORK=... RC_BUDGETS=26,30,34,38,42 python experiments/causal_prep.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, env as E, offrl, runner  # noqa: E402
from rclib.runner import log  # noqa: E402


def main():
    assert C.CAUSAL, "run with RC_CAUSAL=1"
    infos = runner.Stages("infos").load("infos")
    tr = [g for g, x in infos.items() if x["gop"]["split"] == "train"]
    X, Y = [], []
    for g in tr:
        x = E.gop_features(infos[g])
        fp = np.maximum(np.asarray(infos[g]["fp_bits"], float), 8).sum()
        for b in C.BUDGET_QPS:
            X.append(np.r_[x, (b - 30) * x])
            Y.append(np.log2(infos[g]["static"][b]["total_bits"] / fp))
    X, Y = np.array(X), np.array(Y)
    w = np.linalg.lstsq(X, Y, rcond=None)[0]
    nf = X.shape[1] // 2
    res = Y - X @ w
    prior = {"w0": w[:nf].tolist(), "w1": w[nf:].tolist(), "n_fit": int(len(Y)),
             "resid_log2_std": float(res.std()), "resid_log2_iqr": float(np.subtract(*np.percentile(res, [75, 25])))}
    p = os.path.join(C.WORK, "causal_prior.json")
    json.dump(prior, open(p, "w"), indent=1)
    E._PRIOR = None
    log(f"wrote {p}: {prior}")

    lines = [f"# Causal setting checks ({C.CODEC}, budgets {C.BUDGET_QPS})", "", f"Rate model (train): {prior}", ""]
    slim = {g: offrl.slim(x) for g, x in infos.items()}
    for split in ("train", "test"):
        ids = [g for g, x in infos.items() if x["gop"]["split"] == split]
        for k in (0,):
            d = np.array([E.gop_qhat(infos[g], infos[g]["budget"][b]) - b for g in ids for b in C.BUDGET_QPS])
            lines.append(f"- {split}: GOP model base QP - b at s = 1: mean {d.mean():+.2f}, "
                         f"|error| <= 1 for {100 * np.mean(np.abs(d) <= 1):.0f}%, <= 2 for "
                         f"{100 * np.mean(np.abs(d) <= 2):.0f}%, range {d.min():+.1f}..{d.max():+.1f}")
    test = [g for g, x in infos.items() if x["gop"]["split"] == "test"]
    same, diff_k0, n = 0, 0, 0
    for g in test:
        an = infos[g]["an"]
        full = E.causal_flags(an, infos[g]["fp_bits"], C.GOP - 1)
        same += all(np.array_equal(full[k], np.asarray(an[k], np.int8)) for k in ("cut", "flash", "fade"))
        for t in range(C.GOP):
            fl = E.causal_flags(an, infos[g]["fp_bits"], t)
            n += 1
            diff_k0 += any(int(fl[k][t]) != int(an[k][t]) for k in ("cut", "flash", "fade"))
    lines += [f"- causal flags with all frames visible equal the stored flags on {same}/{len(test)} test GOPs",
              f"- at k = 0, frame t's stored flags differ from what the detector knows at t on {diff_k0}/{n} "
              f"test frames ({100 * diff_k0 / n:.1f}%)"]
    srch = runner.Stages("search").load("search_train")
    sub = [g for g in tr if g in srch][:40]
    for k in (0, 5):
        kept = tot = 0
        rng = np.random.default_rng(0)
        for g in sub:
            for b, entry in srch[g].items():
                for pl in offrl.select_plans(entry, rng):
                    _, acts = E.plan_observations(slim[g], b, pl["acts"], pl["bits"], k=k)
                    tot += 1
                    kept += bool(acts.min() >= 0 and acts.max() < offrl.NA)
        lines.append(f"- k={k}: logged plans that stay inside -3..3 on the causal base QP: {kept}/{tot} "
                     f"({100 * kept / max(tot, 1):.0f}%, {len(sub)} train GOPs)")
    out = os.path.join(C.REPORTS, "causal_prep.md")
    os.makedirs(C.REPORTS, exist_ok=True)
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
