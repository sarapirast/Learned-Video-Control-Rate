"""Experiment 1, step 6: how predictable is the hindsight search's per-frame QP shape from causal features?
See exp_next/exp1/PREREG.md (stop rule 2: R^2 of (search shape - final4 shape) at k=5 on val < 0.1).

shape_t = QP_t - mean of the P-frame QPs (frames 1..29); frame 0 = the I-frame offset.
Search plans (lfq arm): QP_t = clip(round(base_q + RAMP[t] + ACTIONS[a_t]), 11, 51) (rclib/search.py qps_of).
  Train: shape averaged over every tied-best logged plan (score within 1e-9 of the best of the 600 encodes;
  amendment 4). Val: the stored best plan.
final4 realised shape: its stored per-frame QPs for the same (GOP, level, k) (results_v1/controller_real/final4_*).
Features for frame t at lookahead k (first pass = lfq infos fp_bits, frames 0..t+k only): t, is_I, level,
  log2(B / 30 / mean visible first pass), log2(fp_t / mean visible P fp), log2(fp_t / fp_{t-1}), log2(fp_t / fp_0),
  max and mean of log2(fp_j / mean visible P fp) over the visible frames ahead, number of visible frames ahead.
Models: (i) frame index + type only = per-frame-index mean of the train target; (ii) HistGradientBoostingRegressor
  (default settings, random_state 0). Train R^2 out-of-fold by clip (GroupKFold 5); val R^2 from a fit on all train.
R^2 reported over all frames and over P frames only. Flat GOPs excluded (lfq infos_learn.pkl set).

  python -I exp_next/exp1/shape_r2.py
Out: results_v1/next/exp1/shape_r2.md
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold

os.environ["RC_ARM"] = "lfq"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
OUT = f"{ROOT}/results_v1/next/exp1"
RAMP = np.array(C.static_offsets(), float)
ACT = np.array(C.ACTIONS, float)
KS = (0, 2, 5)
assert len(RAMP) == 30 and list(ACT) == list(range(-5, 6)), (RAMP, ACT)


def qps(base, acts):
    return np.clip(np.round(base + RAMP + ACT[np.asarray(acts, int)]), C.QP_LO, C.QP_HI)


def shape(q):
    q = np.asarray(q, float)
    return q - q[1:].mean()


def search_shapes(enc, split, infos):
    s = pickle.load(open(f"{RC}/{enc}_lfq/results_search/search_{split}.pkl", "rb"))
    out, nties = {}, []
    for g, x in s.items():
        if g not in infos:
            continue
        for lv, e in x.items():
            if split == "train":
                logs = [r for run in e["logs"] for r in run]
                sc = np.array([r["score"] for r in logs])
                best = sc.max()
                tied = [r for r, v in zip(logs, sc) if v >= best - 1e-9]
                nties.append(len(tied))
                out[(g, lv)] = np.mean([shape(qps(e["base_q"], r["acts"])) for r in tied], axis=0)
            else:
                out[(g, lv)] = shape(qps(e["base_q"], e["best_acts"]))
    return out, nties


def final4_shapes(enc, split, gops):
    fs = glob.glob(f"{ROOT}/results_v1/controller_real/final4_{enc}_{split}_*.parquet")
    c = pd.concat(pd.read_parquet(f, columns=["clip_id", "gop", "level_q0", "k", "qps"]) for f in fs)
    return {(f"{a}@{gops[(a, b)]}", int(lv), int(k)): shape(q)
            for a, b, lv, k, q in zip(c.clip_id, c.gop, c.level_q0, c.k, c.qps)}


def feats(info, lv, k):
    fp = np.maximum(np.asarray(info["fp_bits"], float), 8.0)
    B = info["budget"][lv]
    rows = []
    for t in range(30):
        end = min(29, t + k)
        vis_p = fp[1:end + 1] if end >= 1 else fp[:1] / 6.0
        mp = vis_p.mean()
        ahead = np.log2(fp[t + 1:end + 1] / mp) if end > t else np.zeros(1)
        rows.append([t, t == 0, lv, np.log2(B / 30 / fp[:end + 1].mean()), np.log2(fp[t] / mp),
                     np.log2(fp[t] / fp[t - 1]) if t else 0.0, np.log2(fp[t] / fp[0]), ahead.max(), ahead.mean(),
                     end - t])
    return np.array(rows, float)


def table(enc, split, infos, ss, f4, k):
    X, y_s, y_d, grp = [], [], [], []
    for (g, lv), sh in ss.items():
        if (g, lv, k) not in f4:
            continue
        X.append(feats(infos[g], lv, k))
        y_s.append(sh)
        y_d.append(sh - f4[(g, lv, k)])
        grp += [infos[g]["gop"]["clip"]] * 30
    return np.vstack(X), np.concatenate(y_s), np.concatenate(y_d), np.array(grp)


def r2s(y, p, X):
    pf = X[:, 1] == 0
    return r2_score(y, p), r2_score(y[pf], p[pf])


def main():
    gops = pd.read_csv(f"{ROOT}/data/v1/320x180/gops.csv").set_index(["clip_id", "gop"]).start_frame
    L = ["# Exp 1: predictability of the search's per-frame shape (exp_next/exp1/shape_r2.py)", "",
         "shape_t = QP_t - mean P-frame QP; R^2 over all frames / P frames only. 'search' = the search shape; "
         "'search - final4' = the search shape minus final4's realised shape at the same (GOP, level, k). "
         "Train: clip-grouped 5-fold out-of-fold; val: fit on all train. Model (i) = per-frame-index mean; "
         "(ii) = GBM on causal first-pass features at k.", ""]
    prim = {}
    for enc in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{enc}_lfq/results_infos/infos_learn.pkl", "rb"))
        ss_tr, nties = search_shapes(enc, "train", infos)
        ss_va, _ = search_shapes(enc, "val", infos)
        f4_tr, f4_va = final4_shapes(enc, "train", gops), final4_shapes(enc, "val", gops)
        L += [f"## {enc}", "", f"Tied-best plans per train (GOP, level): median {int(np.median(nties))}, "
              f"mean {np.mean(nties):.1f}, max {max(nties)}, share with ties {np.mean(np.array(nties) > 1):.2f}.", "",
              "| k | target | train OOF (i) all / P | train OOF (ii) all / P | val (i) all / P | val (ii) all / P |",
              "|---|---|---|---|---|---|"]
        for k in KS:
            Xt, yst, ydt, gt = table(enc, "train", infos, ss_tr, f4_tr, k)
            Xv, ysv, ydv, _ = table(enc, "val", infos, ss_va, f4_va, k)
            for name, yt, yv in (("search", yst, ysv), ("search - final4", ydt, ydv)):
                # (i) per-frame-index mean
                idx_t = Xt[:, 0].astype(int)
                oof_i = np.zeros_like(yt)
                oof_ii = np.zeros_like(yt)
                for tr, te in GroupKFold(5).split(Xt, yt, gt):
                    mu = pd.Series(yt[tr]).groupby(idx_t[tr]).mean()
                    oof_i[te] = mu.reindex(idx_t[te]).to_numpy()
                    m = HistGradientBoostingRegressor(random_state=0).fit(Xt[tr], yt[tr])
                    oof_ii[te] = m.predict(Xt[te])
                mu = pd.Series(yt).groupby(idx_t).mean()
                pv_i = mu.reindex(Xv[:, 0].astype(int)).to_numpy()
                pv_ii = HistGradientBoostingRegressor(random_state=0).fit(Xt, yt).predict(Xv)
                c = [r2s(yt, oof_i, Xt), r2s(yt, oof_ii, Xt), r2s(yv, pv_i, Xv), r2s(yv, pv_ii, Xv)]
                L.append(f"| {k} | {name} | " + " | ".join(f"{a:.3f} / {b:.3f}" for a, b in c) + " |")
                if name == "search - final4" and k == 5:
                    prim[enc] = c[3][0]
        L.append("")
    L += ["## PRIMARY (stop rule 2): R^2 on val of (search shape - final4 shape) at k = 5, model (ii), all frames", "",
          ", ".join(f"{e}: {v:.3f}" for e, v in prim.items()), "",
          "Stop rule 2 (PREREG): < 0.1 -> expect Experiment 4 rung 3 to gain at most a few hundredths of a dB.", ""]
    open(f"{OUT}/shape_r2.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
