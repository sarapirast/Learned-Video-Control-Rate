"""Learned rate control on the quality-at-budget metric (tracker item 30g/30f): every learned run vs the references.

Metric (rclib/metrics.py METRIC=dpsnr): score = dPSNR_B - 0.17 dB per 1% over budget, dPSNR_B = PSNR minus the GOP's
constant-QP PSNR at exactly the budget (0 = a fractional constant QP that spends exactly B). Leak-free budgets
(4 levels), P1 settings, flat GOPs excluded.
Runs: rcwork_v1/<codec>_lfq/results_rl/<method>_k<k>_fixed_s<seed>/eval.pkl (bc, cql_ppo, lagr: causal base +
offsets, tracker 30d) and rcwork_v1/<codec>_resq/results_rl/res_k<k>_fixed_s<seed>/eval.pkl (residual on the
retuned controller, 30f), whichever exist.
References, per GOP x level (x k): the lfq hindsight search's best plan (ceiling) and its start plan (ramp at the
hindsight base; rcwork_v1/<codec>_lfq/results_search/search_<split>.pkl); the causal controller
(results_v1/controller_real/<ctrl-tag>_<codec>_<split>_*.parquet, one setting), rescored here with the same metric.
Reported per split, method and k (seeds pooled; per-seed means alongside):
  score, dPSNR_B, budget use, % of episodes over budget, diff vs the controller at the same k with a 95% bootstrap CI
  over clips, gap_closed_% = mean(method - ctrl) / mean(search - ctrl); then the score by GOP class.

  python -I scripts/lfq_compare.py <x264|x265> [--ctrl-tag final3 --ctrl-setting 1.0:9.0:...] [--quick]
Out: results_v1/lfq_compare_<codec>[_quick].md and .csv (one row per episode).
"""
import argparse
import glob
import os
import pickle
import re
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import metrics  # noqa: E402

RC = "/scratch1/aayushso/rcwork_v1"
ROOT = "/scratch1/aayushso/ee599"
D = f"{ROOT}/data/v1/320x180"
RNG = np.random.default_rng(0)
CLASSES = ("stable", "cut", "gradual")
LEVELS = (24, 30, 36, 42)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def load(codec, quick, ctrl_tag, ctrl_setting):
    infos = pickle.load(open(f"{RC}/{codec}_lfq/results_infos/infos_learn.pkl", "rb"))
    gops = pd.read_csv(f"{D}/gops.csv")
    label = {f"{r.clip_id}@{r.start_frame}": r.label for r in gops.itertuples()}
    srch = {}
    for s in ("val", "test"):
        p = f"{RC}/{codec}_lfq/results_search/search_{s}.pkl"
        if os.path.exists(p):
            srch.update(pickle.load(open(p, "rb")))
    ctrl = {}
    files = glob.glob(f"{ROOT}/results_v1/controller_real/{ctrl_tag}_{codec}_*.parquet") if ctrl_tag else []
    if files:
        cp = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
        if ctrl_setting:
            cp = cp[cp.setting == ":".join(str(float(v)) for v in ctrl_setting.split(":"))]
        assert cp.setting.nunique() == 1, f"controller files hold {cp.setting.nunique()} settings; pass --ctrl-setting"
        for r in cp.itertuples():
            g = f"{r.clip_id}@{30 * r.gop}"
            if g in infos:
                ctrl[(g, int(r.level_q0), int(r.k))] = float(metrics.score(r.bits, r.psnr_yuv, infos[g]["curve"],
                                                                           infos[g]["budget"][int(r.level_q0)]))
    rows = []
    sub = "results_rl" + ("_quick" if quick else "")
    paths = sorted(glob.glob(f"{RC}/{codec}_lfq/{sub}/*/eval.pkl") + glob.glob(f"{RC}/{codec}_resq/{sub}/*/eval.pkl")
                   + glob.glob(f"{RC}/{codec}_lfqp/{sub}/*/eval.pkl")    # lfqp: previous-GOP base (tracker 31 C1)
                   + glob.glob(f"{RC}/{codec}_resh/{sub}/*/eval.pkl"))   # resh: residual on the history controller (C2)
    for p in paths:
        run = os.path.basename(os.path.dirname(p))
        m = re.match(r"([a-z_]+)_k(\d+)_fixed(?:_([^_]+))?_s(\d+)$", run)   # optional variant, e.g. lam0.17
        if not m:
            continue
        meth, k, seed = m.group(1) + (f"_{m.group(3)}" if m.group(3) else ""), int(m.group(2)), int(m.group(4))
        if f"/{codec}_lfqp/" in p:
            meth += "@prev"
        if f"/{codec}_resh/" in p:
            meth += "@hist"
        ev = pickle.load(open(p, "rb"))
        for (mode, kk, split), rs in ev["res"].items():
            for r in rs:
                g, b = r["gid"], int(r["budget"])
                if g not in infos:          # flat GOPs (not in the lfq/res infos anyway)
                    continue
                e = srch.get(g, {}).get(b)
                rows.append({"method": meth, "k": kk, "seed": seed, "split": split, "gid": g,
                             "clip": g.split("@")[0], "cls": label[g], "budget": b, "score": r["score"],
                             "dpsnr_b": r.get("dpsnr_b", np.nan), "use": r.get("use", np.nan), "over": r["over"],
                             "search": e["best_score"] if e else np.nan,
                             "start": e["static_score"] if e else np.nan,
                             "ctrl": ctrl.get((g, b, kk), np.nan)})
    return pd.DataFrame(rows)


def table(df, split):
    d = df[df.split == split]
    out = []
    for (meth, k), x in d.groupby(["method", "k"]):
        r = {"method": meth, "k": k, "n": len(x), "seeds": x.seed.nunique(), "score": x.score.mean(),
             "dpsnr_b": x.dpsnr_b.mean(), "use": x.use.mean(), "over_%": 100 * x.over.mean(),
             "seed_means": " / ".join(f"{v:.2f}" for v in x.groupby("seed").score.mean()),
             "search": x.search.mean(), "start": x.start.mean(), "ctrl": x.ctrl.mean()}
        y = x.dropna(subset=["ctrl"])
        if len(y):
            m, lo, hi = boot(y.score - y.ctrl, y["clip"])
            r["vs_ctrl"] = f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]"
            gap = (y.search - y.ctrl).mean()
            r["gap_closed_%"] = 100 * m / gap if gap > 0 else np.nan
        y = x.dropna(subset=["search"])
        if len(y):
            m, lo, hi = boot(y.score - y.search, y["clip"])
            r["vs_search"] = f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]"
        out.append(r)
    return pd.DataFrame(out)


def by_class(df, split):
    d = df[df.split == split]
    rows = []
    for (meth, k), x in d.groupby(["method", "k"]):
        r = {"method": meth, "k": k}
        for c in CLASSES:
            y = x[x.cls == c]
            r[f"{c}_n"] = len(y) // max(x.seed.nunique(), 1)
            r[c] = y.score.mean()
            r[f"{c}_ctrl"] = y.ctrl.mean()
            r[f"{c}_search"] = y.search.mean()
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codec", choices=("x264", "x265"))
    ap.add_argument("--ctrl-tag", default="")
    ap.add_argument("--ctrl-setting", default="")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    df = load(a.codec, a.quick, a.ctrl_tag, a.ctrl_setting)
    name = (f"{ROOT}/results_v1/lfq_compare_{a.codec}{'_quick' if a.quick else ''}"
            f"{'_' + a.ctrl_tag if a.ctrl_tag not in ('', 'final3') else ''}")
    df.to_csv(name + ".csv", index=False)
    lines = [f"# Learned rate control on the quality-at-budget metric, {a.codec} (scripts/lfq_compare.py)", "",
             "Score = dPSNR_B - 0.17 dB per 1% over (dB; 0 = a constant QP spending exactly the budget). Leak-free budgets "
             "(4 levels), P1 settings, flat GOPs excluded. bc / cql_ppo / lagr: causal base QP (budgets.csv "
             "base_qp_est_k) + ramp + learned offset (+-10); '@prev' = the same with the previous-GOP base (scripts/base_prev.py, tracker 31); res: residual offset (-3..+3) on the causal controller. "
             f"ctrl = controller run '{a.ctrl_tag or '-'}' {a.ctrl_setting}; search = lfq hindsight search best plan "
             "(ceiling); start = the search's start plan (ramp at the HINDSIGHT base q, not causal). Seeds pooled; "
             "CI = 95% bootstrap over clips. gap_closed_% = mean(method - ctrl) / mean(search - ctrl).", ""]
    for split in ("test", "val"):
        t = table(df, split)
        if t.empty:
            continue
        lines += [f"## {split}: method x k", "", t.round(3).to_markdown(index=False), "",
                  f"## {split}: score by GOP class", "", by_class(df, split).round(3).to_markdown(index=False), ""]
    open(name + ".md", "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
