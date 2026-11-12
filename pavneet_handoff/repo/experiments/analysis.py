"""Aggregate every RL run into the study's reports (no encodes, except none). Seeds are averaged per (GOP, budget)
before CIs; CIs are paired over (GOP, budget) items. Model/threshold choices use validation; tables show test.

Reports (results/):
  lookahead_report.md   the k curve (CQL->PPO and the lookahead rule), share of the search's gain, neighbour diffs
  methods_report.md     RL approaches at k = 0, 5, 10 (+ MPC if present)
  features_report.md    feature-group ablations at k = 5
  scene_report.md       lookahead modes (dedicated + any-k policy), frames seen, per-GOP k gate, cut specialist, switch
  overshoot_report.md   where/why GOPs go over budget
  expand2_report.md     the runbook's headline report: k = 0..10 + full GOP, share of gain, encoder's own RC
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, metrics, runner  # noqa: E402

KS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 29)


def load_runs(quick):
    runs = []
    for p in glob.glob(os.path.join(C.WORK, f"results_rl{'_quick' if quick else ''}", "*", "eval.pkl")):
        with open(p, "rb") as f:
            r = pickle.load(f)
        a = r["args"]
        cfg = (a["method"], a["k"] if a["method"] != "anyk" else a["kmax"], a["mode"], a["drop"], a["prior"],
               a["tag"], a.get("train_family", ""))
        for (mode, k, split), rows in r["res"].items():
            for x in rows:
                runs.append({"method": a["method"], "train_k": cfg[1], "train_mode": a["mode"], "drop": a["drop"],
                             "prior": a["prior"], "tag": a["tag"], "family_train": cfg[6], "extra": a.get("extra") or "",
                             "seed": a["seed"],
                             "mode": mode, "k": k, "split": split, **{f: x[f] for f in
                             ("gid", "budget", "score", "saving", "over", "over_pct", "static_score", "frames_seen",
                              "bits", "psnr")}})
    return pd.DataFrame(runs)


CFG_COLS = ["method", "train_k", "train_mode", "drop", "prior", "tag", "family_train", "extra", "mode", "k"]


def seed_avg(df):
    """One row per (config, split, gid, budget): scores averaged over seeds."""
    g = df.groupby(CFG_COLS + ["split", "gid", "budget"], dropna=False)
    out = g.agg(score=("score", "mean"), saving=("saving", "mean"), over=("over", "mean"),
                over_pct=("over_pct", "mean"), static=("static_score", "first"), seen=("frames_seen", "mean"),
                seeds=("seed", "nunique")).reset_index()
    return out


def ceiling(quick, split="test"):
    st = runner.Stages("search", quick)
    if not st.done(f"search_{split}"):
        return {}
    return {(g, b): x["best_score"] for g, r in st.load(f"search_{split}").items() for b, x in r.items()}


def summarize(sub, ceil):
    s = sub["score"].to_numpy()
    n = len(s)
    out = {"n": n, "score": s.mean(), "ci": 1.96 * s.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan,
           "median": float(np.median(s)),
           "saving": sub["saving"].mean(), "over %": 100 * sub["over"].mean(), "seen": sub["seen"].mean(),
           "seeds": int(sub["seeds"].max())}
    if ceil:
        best = np.array([ceil.get((g, b), np.nan) for g, b in zip(sub["gid"], sub["budget"])])
        gain_s = best - sub["static"].to_numpy()
        out["share of search gain"] = np.nansum(s - sub["static"].to_numpy()) / np.nansum(gain_s)
    return out


def pick(sa, split="test", **kw):
    """Rows of one configuration. Runs with extra observation features (D23) are kept apart unless asked for: without
    this, k=5 and k=29 CQL->PPO averaged in the fb/sum runs (9 'seeds')."""
    kw.setdefault("extra", "")
    m = sa["split"] == split
    for k, v in kw.items():
        m &= sa[k] == v
    return sa[m]


def paired(a, b):
    j = a.merge(b, on=["gid", "budget"], suffixes=("_a", "_b"))
    if len(j) < 2:
        return np.nan, np.nan
    return metrics.paired_ci(j["score_a"], j["score_b"])


def write(name, lines, quick):
    out = os.path.join(C.REPORTS, f"{name}{'_quick' if quick else ''}_report.md")
    os.makedirs(C.REPORTS, exist_ok=True)
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"wrote {out}")


def table(rows):
    return pd.DataFrame(rows).round(3).to_markdown(index=False)


# ---------------------------------------------------------------- reports

def lookahead_report(sa, ceil, quick, rules):
    rows, prev = [], None
    for k in KS:
        for split in ("val", "test"):
            sub = pick(sa, split, method="cql_ppo", train_mode="fixed", mode="fixed", k=k, drop="", prior=False,
                       tag="", family_train="")
            if not len(sub):
                continue
            r = {"policy": "CQL->PPO", "k": k, "split": split, **summarize(sub, ceil if split == "test" else {})}
            if split == "test":
                if prev is not None:
                    d, ci = paired(sub, prev)
                    r["vs prev k"] = f"{d:+.3f} ± {ci:.3f}"
                prev = sub
            rows.append(r)
    if rules is not None:
        for (kind, k, mode), res in rules.items():
            if kind == "la_rule" and mode == "fixed":
                rows.append({"policy": "lookahead rule", "k": k, "split": "test",
                             **{kk: v for kk, v in metrics.summarize(res).items()},
                             "seen": np.mean([x["frames_seen"] for x in res])})
    write("lookahead", [f"# Lookahead curve ({C.CODEC})", "",
                        "Penalised score = % bits saved at equal PSNR vs own constant QP − 2 × % over budget. "
                        "'share of search gain' = (policy − STATIC) / (hindsight search − STATIC), summed over test "
                        "items. 'vs prev k' = paired difference to the previous k in the list (95 % CI).", "",
                        table(rows)], quick)
    return rows


def methods_report(sa, ceil, quick):
    rows = []
    for k in (0, 5, 10):
        base = pick(sa, method="cql_ppo", train_mode="fixed", mode="fixed", k=k, drop="", prior=False, tag="")
        for m in ("static_ref", "bc", "cql", "iql", "bc_ppo", "cql_ppo", "ppo", "a2c", "dqn", "lagr", "pid", "mpc"):
            sub = pick(sa, method=m, train_mode="fixed", mode="fixed", k=k, drop="", prior=False, tag="")
            if not len(sub):
                continue
            r = {"k": k, "method": m, **summarize(sub, ceil)}
            if m != "cql_ppo" and len(base):
                d, ci = paired(sub, base)
                r["vs CQL->PPO"] = f"{d:+.3f} ± {ci:.3f}"
            rows.append(r)
    write("methods", [f"# RL approaches ({C.CODEC})", "", "All trained on the same data / env steps; test split; "
                      "seed-averaged per GOP and budget.", "", table(rows)], quick)


def features_report(sa, ceil, quick):
    rows = []
    full = pick(sa, method="cql_ppo", train_mode="fixed", mode="fixed", k=5, drop="", prior=False, tag="")
    for drop in sorted(sa["drop"].unique(), key=lambda s: (s.count(","), s)):
        sub = pick(sa, method="cql_ppo", train_mode="fixed", mode="fixed", k=5, drop=drop, prior=False, tag="")
        if not len(sub):
            continue
        r = {"dropped groups": drop or "(none: all features)", **summarize(sub, ceil)}
        if drop:
            d, ci = paired(sub, full)
            r["vs all"] = f"{d:+.3f} ± {ci:.3f}"
        rows.append(r)
    sub = pick(sa, method="cql_ppo", train_mode="fixed", mode="fixed", k=5, drop="", prior=True, tag="")
    if len(sub):
        d, ci = paired(sub, full)
        rows.append({"dropped groups": "(all) + scene budget prior", **summarize(sub, ceil), "vs all": f"{d:+.3f} ± {ci:.3f}"})
    write("features", [f"# Feature ablations at k = 5 ({C.CODEC})", "",
                       "Groups: history (last bits/QP, bits vs first-pass estimate), fp (first-pass cost), pixel "
                       "(spatial/temporal complexity, histogram change), scene (cut/flash/fade flags, same-scene flag, "
                       "distance to cut, scene cost share). Budget state and position are always on.", "",
                       table(rows)], quick)


def gop_feats(infos, gid, budget):
    x = infos[gid]
    fp = np.asarray(x["fp_bits"], float)
    an = x["an"]
    return [float(an["cut"].sum()), float(np.std(fp[1:]) / max(fp[1:].mean(), 1)),
            float(np.log2(x["budget"][budget] / fp.sum())), float(np.mean(an["msad"])), float(np.mean(an["spatial"])),
            C.budget_level(budget), float(an["fade"].sum() + an["flash"].sum())]


def scene_report(sa, ceil, quick, rules):
    lines = [f"# Scene intelligence and dynamic lookahead ({C.CODEC})", ""]
    rows = []
    for (tm, m) in sorted(set(zip(sa["train_mode"], sa["mode"]))):
        for k in sorted(sa["k"].unique()):
            for meth in ("cql_ppo", "anyk"):
                sub = pick(sa, method=meth, train_mode=tm, mode=m, k=k, drop="", prior=False, tag="")
                if len(sub) and (m != "fixed" or meth == "anyk" or k in (5, 10, 29)):
                    rows.append({"policy": "dedicated CQL->PPO" if meth == "cql_ppo" else "any-k CQL->PPO",
                                 "mode": m, "k cap": k, **summarize(sub, ceil)})
    if rules is not None:
        for (kind, k, mode), res in rules.items():
            if mode != "fixed" or kind == "scene_rule":
                rows.append({"policy": kind, "mode": mode, "k cap": k, **metrics.summarize(res),
                             "seen": np.mean([x["frames_seen"] for x in res])})
    lines += ["## Lookahead modes", "", "'seen' = mean future frames visible per decision (the cost of lookahead).",
              "", table(rows), ""]
    # per-GOP k gate: classifier on cheap whole-GOP analysis features picks the k whose fixed-k policy did best
    infos = runner.Stages("infos", quick).load("infos")
    ks = [k for k in (0, 2, 5, 10, 29) if len(pick(sa, "val", method="cql_ppo", train_mode="fixed", mode="fixed", k=k,
                                                     drop="", prior=False, tag=""))]
    if len(ks) >= 2:
        from sklearn.ensemble import GradientBoostingClassifier
        tabs = {}
        for split in ("val", "test"):
            piv = []
            for k in ks:
                s = pick(sa, split, method="cql_ppo", train_mode="fixed", mode="fixed", k=k, drop="", prior=False,
                         tag="")[["gid", "budget", "score", "saving", "over", "static", "seen"]]
                piv.append(s.assign(k=k))
            tabs[split] = pd.concat(piv)
        val = tabs["val"].pivot_table(index=["gid", "budget"], columns="k", values="score").dropna()
        X = np.array([gop_feats(infos, g, b) for g, b in val.index])
        y = val.to_numpy().argmax(1)
        clf = GradientBoostingClassifier(n_estimators=100, max_depth=2, random_state=0).fit(X, y)
        te = tabs["test"].pivot_table(index=["gid", "budget"], columns="k", values="score").dropna()
        Xt = np.array([gop_feats(infos, g, b) for g, b in te.index])
        choice = clf.predict(Xt)
        gate = te.to_numpy()[np.arange(len(te)), choice]
        oracle = te.to_numpy().max(1)
        grows = [{"policy": f"fixed k={k}", "score": te[k].mean()} for k in ks]
        grows += [{"policy": "per-GOP k gate (val-trained)", "score": gate.mean(),
                   "mean k": float(np.mean(np.array(ks)[choice]))},
                  {"policy": "oracle per-GOP k (upper bound)", "score": oracle.mean()}]
        lines += ["## Per-GOP lookahead gate", "",
                  f"Gradient-boosted classifier on whole-GOP analysis features (cut count, cost variability, budget vs "
                  f"cost, motion, texture, budget level, fades/flashes) picks k from {ks}; trained on validation "
                  f"outcomes, applied to test. The features need the GOP's pixel/first-pass analysis (not encodes).",
                  "", table(grows), ""]
    # cut specialist routed by the detector
    spec = pick(sa, method="cql_ppo", family_train="cut", mode="fixed", k=5)
    gen = pick(sa, method="cql_ppo", train_mode="fixed", mode="fixed", k=5, drop="", prior=False, tag="",
               family_train="")
    if len(spec) and len(gen):
        has_cut = {g for g in gen["gid"] if infos[g]["an"]["cut"].sum() > 0}
        routed = pd.concat([spec[spec["gid"].isin(has_cut)], gen[~gen["gid"].isin(has_cut)]])
        r = [{"policy": "general k=5", **summarize(gen, ceil)},
             {"policy": "general k=5, GOPs with cut", **summarize(gen[gen["gid"].isin(has_cut)], ceil)},
             {"policy": "cut specialist, GOPs with cut", **summarize(spec[spec["gid"].isin(has_cut)], ceil)},
             {"policy": "routed (specialist on cut GOPs)", **summarize(routed, ceil)}]
        lines += ["## Cut specialist (cutspec)", "", table(r), ""]
    # switch: GOP-level choice between the lookahead rule and RL at k=5
    if rules is not None and ("la_rule", 5, "fixed") in rules and len(gen):
        rr = pd.DataFrame(rules[("la_rule", 5, "fixed")])[["gid", "budget", "score"]]
        j = gen.merge(rr, on=["gid", "budget"], suffixes=("_rl", "_rule"))
        lines += ["## Switch (rule vs RL per GOP, k = 5)", "",
                  f"RL {j['score_rl'].mean():.3f}, rule {j['score_rule'].mean():.3f}, oracle switch "
                  f"{np.maximum(j['score_rl'], j['score_rule']).mean():.3f}; RL better on "
                  f"{100 * (j['score_rl'] > j['score_rule']).mean():.1f}% of GOPs.", ""]
    write("scene", lines, quick)


def overshoot_report(df, quick):
    infos = runner.Stages("infos", quick).load("infos")
    sub = df[(df["split"] == "test") & (df["method"] == "cql_ppo") & (df["mode"] == "fixed") & (df["drop"] == "")
             & (~df["prior"]) & (df["tag"] == "") & (df["family_train"] == "")]
    if not len(sub):
        return
    sub = sub.assign(family=[infos[g]["gop"]["family"] for g in sub["gid"]],
                     has_cut=[infos[g]["an"]["cut"].sum() > 0 for g in sub["gid"]])
    t1 = sub.groupby(["k", "budget"]).agg(over=("over", "mean"), mean_over_pct=("over_pct", "mean"),
                                          p95_over_pct=("over_pct", lambda v: np.percentile(v, 95))).round(3)
    t2 = sub.groupby(["family"]).agg(over=("over", "mean"), score=("score", "mean")).round(3)
    t3 = sub.groupby(["has_cut"]).agg(over=("over", "mean"), score=("score", "mean")).round(3)
    write("overshoot", [f"# Overshoot ({C.CODEC}, CQL->PPO, test)", "", "By k and budget:", "", t1.to_markdown(), "",
                        "By family:", "", t2.to_markdown(), "", "GOPs with/without a detected cut:", "",
                        t3.to_markdown()], quick)


def expand2_report(lk_rows, quick):
    """The runbook's headline report: lookahead curve k=0..10 + full GOP, share of gain, own rate control."""
    lines = [f"# Lookahead curve and the encoder's own rate control ({C.CODEC})", ""]
    rows = [r for r in lk_rows if r["policy"] == "CQL->PPO" and r["split"] == "test" and (r["k"] <= 10 or r["k"] == 29)]
    lines += [table(rows), ""]
    bst = runner.Stages("baselines", quick)
    if bst.done("own_rc"):
        own = bst.load("own_rc")
        infos = runner.Stages("infos", quick).load("infos")
        test = [g for g, x in infos.items() if x["gop"]["split"] == "test" and g in own]
        orows = []
        for b in C.BUDGET_QPS:
            for key in sorted({k for g in test for k in own[g] if k[0] == b}):
                rr = [own[g][key] for g in test]
                ok = [r for r in rr if not r.get("failed")]
                orows.append({"rate control": f"{key[1]}{' +AQ/cutree' if key[2] else ''}", "budget QP": b,
                              **metrics.summarize(ok), "encoder failed": len(rr) - len(ok)})
        lines += ["Encoder's own rate control on the same budgets (test):", "", table(orows)]
    write("expand2", lines, quick)


def main():
    a = runner.args()
    df = load_runs(a.quick)
    if not len(df):
        print("no RL runs found")
        return
    sa = seed_avg(df)
    ceil = ceiling(a.quick)
    bst = runner.Stages("baselines", a.quick)
    rules = bst.load("rules")["test"] if bst.done("rules") else None
    lk = lookahead_report(sa, ceil, a.quick, rules)
    methods_report(sa, ceil, a.quick)
    features_report(sa, ceil, a.quick)
    scene_report(sa, ceil, a.quick, rules)
    overshoot_report(df, a.quick)
    expand2_report(lk, a.quick)


if __name__ == "__main__":
    main()
