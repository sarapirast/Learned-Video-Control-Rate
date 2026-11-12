"""Residual RL on P2's causal controller (tracker item 27): each run vs the controller alone and the leak-free search.

Reads rcwork_v1/<codec>_res/results_rl[_quick]/res_k<k>_fixed_s<seed>/eval.pkl. Each episode row carries the
controller's own score on the same GOP x level x k ("static_score" in the res arm); the search's best score comes
from rcwork_v1/<codec>_lf/results_search/search_<split>.pkl. Flat (grayscale) GOPs are not in the res arm at all.
Reported per k (seeds pooled, and per seed), and per GOP class:
  score res / ctrl / search, diff = res - ctrl with a 95% bootstrap CI over clips, % of episodes over budget,
  gap_closed_% = mean(res - ctrl) / mean(search - ctrl) (share of the controller-to-search gap the residual closes),
  mean |offset| (how far the policy moves off the controller's QP) and % of frames with a nonzero offset,
  budget use (bits / budget) and dPSNR@B = PSNR minus the GOP's constant-QP PSNR at exactly the budget (quality at the
  budget; added 11-09 after finding that the score does not penalise unused budget, see results_v1/res_offsets_*.md).

  python -I scripts/res_compare.py [x264] [--quick]
Out: results_v1/res_compare_<codec>[_quick].md (+ .csv per episode)
"""
import glob
import os
import pickle
import re
import sys

import numpy as np
import pandas as pd

RC = "/scratch1/aayushso/rcwork_v1"
OUT = "/scratch1/aayushso/ee599/results_v1"
RNG = np.random.default_rng(0)
CLASSES = ("stable", "cut", "gradual")


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def psnr_at(curve, B):
    lb, p = np.log(np.asarray(curve["bits"], float)), np.asarray(curve["psnr"], float)
    o = np.argsort(lb)
    return float(np.interp(np.log(B), lb[o], p[o]))      # constant-QP PSNR at exactly B (clamped at the curve ends)


def load(codec, quick):
    work = f"{RC}/{codec}_res"
    infos = pickle.load(open(f"{work}/results_infos/infos.pkl", "rb"))
    cp = pd.concat([pd.read_parquet(p) for p in glob.glob(
        f"/scratch1/aayushso/ee599/results_v1/controller_real/final2_{codec}_*.parquet")])
    cp = cp[cp.setting == "0.97:3.0:0.3:2.0:3.0:4.0:0.0:1.0:0.0:0.0"].set_index(["clip_id", "gop", "level_q0", "k"])
    srch = {}
    for s in ("val", "test"):
        p = f"{RC}/{codec}_lf/results_search/search_{s}.pkl"
        if os.path.exists(p):
            srch.update(pickle.load(open(p, "rb")))
    rows = []
    for p in sorted(glob.glob(f"{work}/results_rl{'_quick' if quick else ''}/res_k*_fixed_s*/eval.pkl")):
        run = os.path.basename(os.path.dirname(p))
        m = re.match(r"res_k(\d+)_fixed_s(\d+)$", run)
        if not m:
            continue
        k, seed = int(m.group(1)), int(m.group(2))
        for (mode, kk, split), eps in pickle.load(open(p, "rb"))["res"].items():
            for e in eps:
                g = infos[e["gid"]]["gop"]
                B = infos[e["gid"]]["budget"][e["budget"]]
                ref = psnr_at(infos[e["gid"]]["curve"], B)
                cr = cp.loc[(g["clip"], int(g["v1_gop"]), e["budget"], kk)]
                off = np.asarray(e["qps"]) - np.asarray(e["ctrl_qps"])
                rows.append({"k": kk, "seed": seed, "split": split, "gid": e["gid"], "clip": g["clip"],
                             "cls": g["label"], "budget": e["budget"], "res": e["score"], "ctrl": e["static_score"],
                             "over": bool(e["over"]),
                             "ctrl_over": infos[e["gid"]]["ctrl"][(e["budget"], kk)]["over_pct"] > 0,
                             "search": srch[e["gid"]][e["budget"]]["best_score"] if e["gid"] in srch else np.nan,
                             "abs_off": float(np.abs(off).mean()), "nz_off": float((off != 0).mean()),
                             "use_res": e["bits"] / B, "use_ctrl": cr.bits / B,
                             "dpsnr_res": e["psnr"] - ref, "dpsnr_ctrl": cr.psnr_yuv - ref})
    return pd.DataFrame(rows)


def table(d):
    out = []
    for (split, k), x in d.groupby(["split", "k"]):
        for cls in ("all",) + CLASSES:
            y = x if cls == "all" else x[x.cls == cls]
            if len(y) < 2:
                continue
            m, lo, hi = boot(y.res - y.ctrl, y["clip"])
            gap = (y.search - y.ctrl).mean()
            out.append({"split": split, "k": k, "class": cls, "n": len(y), "res": y.res.mean(), "ctrl": y.ctrl.mean(),
                        "search": y.search.mean(), "diff [CI]": f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]",
                        "gap_closed_%": 100 * m / gap if gap > 0 else np.nan, "%over res": 100 * y.over.mean(),
                        "%over ctrl": 100 * y.ctrl_over.mean(), "mean|off|": y.abs_off.mean(),
                        "%frames off": 100 * y.nz_off.mean(), "use res": y.use_res.mean(),
                        "use ctrl": y.use_ctrl.mean(), "dPSNR@B res": y.dpsnr_res.mean(),
                        "dPSNR@B ctrl": y.dpsnr_ctrl.mean(),
                        "dPSNR diff [CI]": "{:+.2f} [{:+.2f}, {:+.2f}]".format(*boot(y.dpsnr_res - y.dpsnr_ctrl, y["clip"]))})
    return pd.DataFrame(out)


def md(df):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        L.append("| " + " | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(L)


def main(codec="x264", *flags):
    quick = "--quick" in flags
    d = load(codec, quick)
    if d.empty:
        raise SystemExit("no res runs found")
    tag = f"{codec}{'_quick' if quick else ''}"
    d.to_csv(f"{OUT}/res_compare_{tag}.csv", index=False)
    t = table(d)
    L = [f"# Residual RL on the causal controller ({tag})", "",
         "Generated by `scripts/res_compare.py`. res = controller QP + learned offset (-3..+3); ctrl = P2's controller "
         "alone (setting 0.97:3:0.3:2:3:4:0:1, real encodes); search = leak-free hindsight search (upper reference). "
         "Leak-free budgets (4 levels), P1 settings, flat GOPs excluded. Seeds pooled; CI = 95% bootstrap over clips. "
         "Score: % bits saved at equal PSNR vs the GOP's constant-QP curve, minus 2 per 1% over budget.", ""]
    for split in ("test", "val"):
        x = t[t.split == split].drop(columns="split")
        if len(x):
            L += [f"## {split}", "", "**All GOPs, by k**", "", md(x[x["class"] == "all"].drop(columns="class")), "",
                  "**By class**", "", md(x[x["class"] != "all"]), ""]
            s = d[d.split == split].groupby(["k", "seed"]).apply(lambda y: (y.res - y.ctrl).mean()).unstack()
            L += ["**Per seed, res - ctrl**", "", md(s.round(2).reset_index().rename(columns=str)), ""]
    open(f"{OUT}/res_compare_{tag}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(*sys.argv[1:])
