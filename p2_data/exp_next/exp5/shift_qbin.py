"""Experiment 5a REVISION 3: causal per-qbin shift vectors. PREREG: exp_next/exp5/PREREG_SHIFT.md (REVISION 3).

Same 4-parameter weighted LS as shift_smooth.py (beta 0.1, clipped labels, fitting clips), but plans are grouped by
the bin of final4's frame-0 planning QP (controller decide() diag "level" at t = 0, Exp 5 observation f4 slot 1 =
(level - 30) / 10) instead of the budget level. Bins: < 27 -> Q24, [27, 33) -> Q30, [33, 39) -> Q36, >= 39 -> Q42.
Also reported: how well the bin tracks the budget level (cross-tab) and the per-qbin vs per-level parameters.

  python -I exp_next/exp5/shift_qbin.py
Out: results_v1/next/exp5/shifts_qbin.json ({"enc|k|Q<lv>": [30 floats], "...|params": [4]}), shift_qbin.md
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp5")
from shift_fit import GOP, KS, LEVELS, OUT, npz_memmap, weights  # noqa: E402
from shift_smooth import fit  # noqa: E402

OBS_LEVEL = 347          # f4 extra slot 1 = (final4's planning level - 30) / 10 (rclib/env.py _extra)
EDGES = (27, 33, 39)


def qbin(level):
    """final4's frame-0 planning QP -> bin label (24 / 30 / 36 / 42)."""
    return np.asarray(LEVELS)[np.searchsorted(EDGES, np.asarray(level, float), side="right")]


def main():
    dest = f"{OUT}/shifts_qbin.json"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    sm = json.load(open(f"{OUT}/shifts_smooth.json"))
    out, L = {}, ["# Exp 5a REVISION 3: per-qbin shift (exp_next/exp5/shift_qbin.py)", "",
                  "Plans grouped by final4's frame-0 planning QP (causal), bins < 27 / 27-33 / 33-39 / >= 39 -> "
                  "Q24 / Q30 / Q36 / Q42. Beta 0.1 weights, clipped labels, fitting clips only. Params = I offset, "
                  "frame-1 offset, ramp at frame 2, ramp at frame 29 (QP).", ""]
    rows = []
    for enc in ("x264", "x265"):
        plans = pd.read_pickle(f"{OUT}/plans_{enc}.pkl").set_index("pid")
        for k in KS:
            p = f"{OUT}/data_{enc}_k{k}.npz"
            z = np.load(p)
            lab, t, pid = z["label"].astype(float), z["t"].astype(int), z["pid"]
            assert (t[::GOP] == 0).all() and (pid[::GOP] == pid[GOP - 1::GOP]).all()
            w = weights(z["delta"].astype(float), 0.1)
            lv0 = np.asarray(npz_memmap(p, "obs")[::GOP, OBS_LEVEL], float) * 10 + 30     # one per plan
            qb = np.repeat(qbin(lv0), GOP)
            lev = plans.level.reindex(pid).to_numpy()
            ct = pd.crosstab(pd.Series(lev[::GOP], name="budget level"), pd.Series(qb[::GOP], name="qbin"))
            agree = float(np.mean(lev[::GOP] == qb[::GOP]))
            L += [f"## {enc} k{k}", "", f"Plans per (budget level, qbin) (agreement {100 * agree:.1f}%):", "",
                  ct.to_markdown(), "",
                  "final4 frame-0 planning QP by budget level (mean, p10, p90): " + "; ".join(
                      f"L{v} {lv0[lev[::GOP] == v].mean():.1f} ({np.percentile(lv0[lev[::GOP] == v], 10):.1f}, "
                      f"{np.percentile(lv0[lev[::GOP] == v], 90):.1f})" for v in LEVELS), ""]
            for b in LEVELS:
                m = qb == b
                assert m.sum() > 0, (enc, k, b)
                vec, par, _ = fit(lab[m], w[m], t[m])
                out[f"{enc}|{k}|Q{b}"] = [float(x) for x in vec]
                out[f"{enc}|{k}|Q{b}|params"] = par
                rows.append({"enc": enc, "k": k, "bin": b, "plans": int(m.sum() // GOP),
                             **{f"Q {n}": v for n, v in zip(("I", "f1", "f2", "f29"), par)},
                             **{f"L {n}": v for n, v in zip(("I", "f1", "f2", "f29"), sm[f"{enc}|{k}|L{b}|params"])}})
    L += ["## Parameters: per-qbin (Q) vs per-level (L, shifts_smooth.json)", "",
          pd.DataFrame(rows).round(2).to_markdown(index=False), ""]
    json.dump(out, open(dest, "w"), indent=0)
    open(f"{OUT}/shift_qbin.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
