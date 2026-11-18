"""Experiment 5a fit (no encodes) + centred-BC go/no-go. Pre-registration: exp_next/exp5/PREREG_SHIFT.md.

From the Exp 5 dataset (results_v1/next/exp5/data_<enc>_k<k>.npz, plans_<enc>.pkl):
- shift vectors: weighted mean clipped label per frame index, w = exp(Delta / beta) clipped at its 99th percentile,
  beta 0.05 / 0.1 / 0.2, pooled and per budget level, rounded with floor(x + 0.5) -> results_v1/next/exp5/shifts.json
- stability across levels; share of position-centred labels outside -3..+3; share of logged plan frames a re-capped
  residual could not reproduce (step limit dmax 3 vs the plan's own previous QP, or P QP < I QP + pmin 1)
- go/no-go: R^2 of a GBM on BC's observation for the position-centred label (5-fold clip-grouped OOF, beta 0.1
  weights, plan subsample); train centred BC only if >= 0.10 on both encoders at k5.

  python -I exp_next/exp5/shift_fit.py [--nplans 4000]
Out: results_v1/next/exp5/shift_fit.md, shifts.json
"""
import argparse
import json
import zipfile

import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

OUT = "/scratch1/aayushso/ee599/results_v1/next/exp5"
BETAS, KS, LEVELS, GOP = (0.05, 0.1, 0.2), (0, 5), (24, 30, 36, 42), 30
KS = tuple(int(x) for x in os.environ.get("EXP5_KS", "0,5").split(","))   # final week 11-17: k2 added via EXP5_KS=2
OBS_QCTRL = 346          # f4 extra slot 0 = (final4's proposed QP - 30) / 10 (rclib/env.py _extra)
DMAX, PMIN, DI = 3, 1, 6  # final4 setting 1.0:6:1.0:2:3:4:1:1:1:0:3 -> dI 6, dmax 3, pmin 1


def npz_memmap(path, key):
    """Memory-map one array of an uncompressed .npz (np.savez) without reading it."""
    zf = zipfile.ZipFile(path)
    info = zf.getinfo(key + ".npy")
    assert info.compress_type == zipfile.ZIP_STORED
    with open(path, "rb") as f:
        f.seek(info.header_offset)
        h = f.read(30)
        n, m = int.from_bytes(h[26:28], "little"), int.from_bytes(h[28:30], "little")
        start = info.header_offset + 30 + n + m
        f.seek(start)
        ver = np.lib.format.read_magic(f)
        rd = np.lib.format.read_array_header_1_0 if ver == (1, 0) else np.lib.format.read_array_header_2_0
        shape, fortran, dtype = rd(f)
        off = f.tell()
    return np.memmap(path, dtype=dtype, mode="r", offset=off, shape=shape, order="F" if fortran else "C")


def weights(delta, beta):
    w = np.exp(delta / beta)
    return np.minimum(w, np.percentile(w, 99))


def wmean_by(lab, w, keys):
    d = pd.DataFrame({"y": lab * w, "w": w})
    g = d.groupby(keys)
    return g.y.sum() / g.w.sum()


def rnd(x):
    return np.floor(np.asarray(x) + 0.5).astype(int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nplans", type=int, default=4000)
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    shifts, L, gng = {}, ["# Exp 5a fit + centred-BC go/no-go (exp_next/exp5/shift_fit.py)", "",
                          "Pre-registration: exp_next/exp5/PREREG_SHIFT.md. Fitting clips only (train minus the "
                          "train-select fold, minus flat GOPs). Labels clipped to -6..+6.", ""], {}
    for enc in ("x264", "x265"):
        plans = pd.read_pickle(f"{OUT}/plans_{enc}.pkl").set_index("pid")
        for k in KS:
            p = f"{OUT}/data_{enc}_k{k}.npz"
            z = np.load(p)
            lab, t, pid, delta = (z["label"].astype(float), z["t"].astype(int), z["pid"], z["delta"].astype(float))
            lev = plans.level.reindex(pid).to_numpy()
            clip = np.array([g.split("@")[0] for g in plans.gid.reindex(pid)])
            L += [f"## {enc} k{k}", "", f"rows {len(lab)}, plans {len(np.unique(pid))}", ""]
            tab = {}
            for beta in BETAS:
                w = weights(delta, beta)
                pooled = wmean_by(lab, w, [t]).reindex(range(GOP)).to_numpy()
                per = wmean_by(lab, w, [lev, t])
                shifts[f"{enc}|{k}|{beta}|pooled"] = rnd(pooled).tolist()
                for lv in LEVELS:
                    shifts[f"{enc}|{k}|{beta}|L{lv}"] = rnd(per.loc[lv].reindex(range(GOP)).to_numpy()).tolist()
                tab[f"pooled b{beta}"] = pooled
                for lv in LEVELS:
                    tab[f"L{lv} b{beta}"] = per.loc[lv].reindex(range(GOP)).to_numpy()
                if beta == 0.1:
                    dev = max(np.abs(per.loc[lv].reindex(range(GOP)).to_numpy() - pooled).max() for lv in LEVELS)
                    ndiff = sum(int((rnd(per.loc[lv].reindex(range(GOP)).to_numpy()) != rnd(pooled)).sum())
                                for lv in LEVELS)
                    L += [f"Stability (beta 0.1): max |per-level - pooled| over frames and levels {dev:.2f} QP; "
                          f"rounded per-level vectors differ from the rounded pooled one on {ndiff} of 120 "
                          f"(level, frame) entries.", ""]
            df = pd.DataFrame(tab, index=range(GOP)).T
            L += ["Weighted mean label by frame index (rows: variant; before rounding):", "",
                  df.round(2).to_markdown(), "",
                  "Rounded pooled vectors: " + "; ".join(f"b{b} {shifts[f'{enc}|{k}|{b}|pooled']}" for b in BETAS), ""]
            # centred labels, range, re-cap reproducibility (beta 0.1, pooled position mean)
            w = weights(delta, 0.1)
            mu_t = wmean_by(lab, w, [t]).reindex(range(GOP)).to_numpy()
            cen = lab - mu_t[t]
            raw = z["raw"].astype(int)
            qc = np.rint(npz_memmap(p, "obs")[:, OBS_QCTRL].astype(np.float32) * 10 + 30).astype(int)
            q = (qc + raw).reshape(-1, GOP)
            ref = np.concatenate([q[:, :1] + DI, q[:, 1:-1]], axis=1)              # ref for frames 1..29
            bad_step = np.abs(q[:, 1:] - ref) > DMAX
            bad_pmin = q[:, 1:] < q[:, :1] + PMIN
            bad = bad_step | bad_pmin
            L += [f"Centred labels (beta 0.1 position mean) outside -3..+3: {100 * np.mean(np.abs(cen) > 3):.2f}% "
                  f"(raw clipped labels outside -3..+3: {100 * np.mean(np.abs(lab) > 3):.2f}%).",
                  f"Logged plan frames 1-29 a re-capped residual could not reproduce: {100 * bad.mean():.1f}% (step "
                  f"limit {100 * bad_step.mean():.1f}%, pmin {100 * bad_pmin.mean():.1f}%); plans with any such "
                  f"frame {100 * bad.any(axis=1).mean():.1f}%; weighted (beta 0.1) frame share "
                  f"{100 * np.average(bad.mean(axis=1), weights=w[::GOP]):.1f}%.", ""]
            # go/no-go: GBM on the full observation vs position only, OOF by clip
            up = np.unique(pid)
            sel = np.sort(rng.choice(up, min(a.nplans, len(up)), replace=False))
            rows = (np.searchsorted(pid[::GOP], sel)[:, None] * GOP + np.arange(GOP)).ravel()
            assert (pid[rows] == np.repeat(sel, GOP)).all()
            X = np.asarray(npz_memmap(p, "obs")[rows], np.float32)
            y, ws, ts, gs, ls = lab[rows], w[rows], t[rows], clip[rows], lev[rows]
            oof_i, oof_il, oof_ii = np.zeros_like(y), np.zeros_like(y), np.zeros_like(y)
            for tr, te in GroupKFold(5).split(X, y, gs):
                oof_i[te] = wmean_by(y[tr], ws[tr], [ts[tr]]).reindex(ts[te]).to_numpy()
                m = wmean_by(y[tr], ws[tr], [ls[tr], ts[tr]])
                oof_il[te] = m.reindex(pd.MultiIndex.from_arrays([ls[te], ts[te]])).to_numpy()
                oof_ii[te] = HistGradientBoostingRegressor(random_state=0).fit(X[tr], y[tr], sample_weight=ws[tr]) \
                    .predict(X[te])
            sse = lambda pr: float(np.sum(ws * (y - pr) ** 2))                 # noqa: E731
            sst = float(np.sum(ws * (y - np.average(y, weights=ws)) ** 2))
            r_i, r_il, r_ii = 1 - sse(oof_i) / sst, 1 - sse(oof_il) / sst, 1 - sse(oof_ii) / sst
            r_c = 1 - sse(oof_ii) / sse(oof_i)
            gng[(enc, k)] = r_c
            L += [f"Go/no-go ({len(sel)} plans, {len(np.unique(gs))} clips, OOF by clip, beta 0.1 weights): R^2 of the "
                  f"label: position only {r_i:.3f}, position x level {r_il:.3f}, GBM on the observation {r_ii:.3f}. "
                  f"**R^2 of the GBM on the position-centred label: {r_c:.3f}**", ""]
            print(enc, k, "done", flush=True)
    ok = all(gng[(e, 5)] >= 0.10 for e in ("x264", "x265"))
    L += ["## Centred-BC go/no-go (k5, both encoders, >= 0.10)", "",
          ", ".join(f"{e} k{k}: {v:.3f}" for (e, k), v in gng.items()), "",
          f"**{'GO: train centred BC' if ok else 'NO-GO: BC and R3 drop down the priority list'}**", "",
          "Exp 1 (val, k5, search shape - final4 shape): position only 0.159 / 0.182, GBM 0.331 / 0.375 "
          "(x264 / x265).", ""]
    json.dump(shifts, open(f"{OUT}/shifts.json", "w"), indent=0)
    open(f"{OUT}/shift_fit.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
