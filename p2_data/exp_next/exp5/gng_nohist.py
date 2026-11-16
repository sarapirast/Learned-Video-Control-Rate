"""Centred-BC go/no-go, revision 2 (exp_next/exp5/PREREG_SHIFT.md): without the plan's own history.

Same protocol as shift_fit.py's go/no-go (4000 plans per (encoder, k), seed 0, 5-fold OOF grouped by clip, beta 0.1
weights, GBM default settings), but the observation drops the own-history slots: o[5] last frame's bits / per-frame
budget, o[6] previous offset (the plan's own previous label), o[7] last frame's bits / its first pass, o[8] bits
spent / first pass so far. Budget state (o[3], o[4]) and the final4-state features (f4, recomputed causally) are kept.
Primary statistic: R^2 of the GBM for the position-centred label, 1 - SSE(GBM) / SSE(position mean), out of fold.
GO only if >= 0.10 at k5 on both encoders. Also reported at k5: dropping o[6] only.

  python -I exp_next/exp5/gng_nohist.py [--nplans 4000]
Out: results_v1/next/exp5/gng_nohist.md
"""
import argparse
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp5")
from shift_fit import GOP, KS, OUT, npz_memmap, weights, wmean_by  # noqa: E402

HIST = [5, 6, 7, 8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nplans", type=int, default=4000)
    a = ap.parse_args()
    rng = np.random.default_rng(0)            # same draws as shift_fit.py (one rng.choice per (enc, k), same order)
    L = ["# Centred-BC go/no-go without own history (exp_next/exp5/gng_nohist.py)", "",
         f"{a.nplans} plans per (encoder, k), OOF by clip, beta 0.1 weights. Dropped obs slots {HIST} (own history).", "",
         "| enc | k | features | R^2 label: position | R^2 label: GBM | **R^2 centred label** |", "|---|---|---|---|---|---|"]
    res = {}
    for enc in ("x264", "x265"):
        plans = pd.read_pickle(f"{OUT}/plans_{enc}.pkl").set_index("pid")
        for k in KS:
            p = f"{OUT}/data_{enc}_k{k}.npz"
            z = np.load(p)
            lab, t, pid = z["label"].astype(float), z["t"].astype(int), z["pid"]
            w = weights(z["delta"].astype(float), 0.1)
            clip = np.array([g.split("@")[0] for g in plans.gid.reindex(pid)])
            up = np.unique(pid)
            sel = np.sort(rng.choice(up, min(a.nplans, len(up)), replace=False))
            rows = (np.searchsorted(pid[::GOP], sel)[:, None] * GOP + np.arange(GOP)).ravel()
            X = np.asarray(npz_memmap(p, "obs")[rows], np.float32)
            y, ws, ts, gs = lab[rows], w[rows], t[rows], clip[rows]
            variants = [("no own history", HIST)] + ([("drop o[6] only", [6])] if k == 5 else [])
            for name, drop in variants:
                keep = [c for c in range(X.shape[1]) if c not in drop]
                oof_i, oof_ii = np.zeros_like(y), np.zeros_like(y)
                for tr, te in GroupKFold(5).split(X, y, gs):
                    oof_i[te] = wmean_by(y[tr], ws[tr], [ts[tr]]).reindex(ts[te]).to_numpy()
                    oof_ii[te] = HistGradientBoostingRegressor(random_state=0).fit(
                        X[tr][:, keep], y[tr], sample_weight=ws[tr]).predict(X[te][:, keep])
                sse = lambda pr: float(np.sum(ws * (y - pr) ** 2))          # noqa: E731
                sst = float(np.sum(ws * (y - np.average(y, weights=ws)) ** 2))
                rc = 1 - sse(oof_ii) / sse(oof_i)
                res[(enc, k, name)] = rc
                L.append(f"| {enc} | {k} | {name} | {1 - sse(oof_i) / sst:.3f} | {1 - sse(oof_ii) / sst:.3f} | "
                         f"**{rc:.3f}** |")
                print(enc, k, name, f"{rc:.3f}", flush=True)
    ok = all(res[(e, 5, "no own history")] >= 0.10 for e in ("x264", "x265"))
    L += ["", "Full observation (shift_fit.md, same plans): x264 k0 0.590, k5 0.517; x265 k0 0.597, k5 0.524.", "",
          f"**{'GO: train centred BC without own history in the observation' if ok else 'NO-GO: BC and R3 drop down the priority list'}**"
          " (rule: >= 0.10 at k5, both encoders, no own history)", ""]
    open(f"{OUT}/gng_nohist.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
