"""Phase J: breakdowns of finished results (no new encodes), for comparison with the external extend_report.md.

For every method on the test split, per (GOP, budget) case (seeds averaged):
  score      saving - 2 x % over budget (our headline, D13)
  saving     % bits saved vs the encoder's constant QP at equal PSNR (unclipped), and clipped to +-50 % (their headline)
  >1% over   share of cases more than 1 % over budget (their over-budget count)
by GOP group: all / scene cut (natural, spliced) / stable (no cut, no fade) / gradual (fade). Paired differences vs
the k=5 CQL->PPO policy and vs the causal rule use a 95 % bootstrap over cases.

Then "where the k=5 policy wins and loses": per test GOP, its saving and its difference from the lookahead rule at
k=5 (the non-learned counterpart), by terciles of cut strength / motion / spatial detail (Spearman), by GOP type, and
the largest losses.

  python experiments/breakdown.py            # uses RC_CODEC / RC_WORK; writes results/<codec>/breakdown_report.md
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, env as E, metrics  # noqa: E402

CLIP = 50.0
REF, RULE = "cql_ppo fixed:5", "rule k=0"
EXT_METHODS = ("cql_a2c", "cql_dqn", "ensemble", "gate", "lagr_ft", "pid_ft", "mb", "mb_ppo")
GROUPS = ("all", "scene cut", "natural cut", "spliced", "stable", "gradual")


def _load(p):
    with open(p, "rb") as f:
        return pickle.load(f)


def group_of(info):
    an, spliced = info["an"], info["gop"]["family"] == "splice"
    cut, fade = bool(an["cut"][1:].sum() > 0), bool(an["fade"].sum() > 0)
    g = {"all"}
    if cut or spliced:
        g |= {"scene cut", "spliced" if spliced else "natural cut"}
    if fade:
        g.add("gradual")
    if not (cut or spliced or fade):
        g.add("stable")
    return g


def collect(work):
    """method label -> {(gid, budget): [(bits, psnr), ...]} on test."""
    infos = _load(os.path.join(work, "results_infos", "infos.pkl"))
    test = sorted(g for g, x in infos.items() if x["gop"]["split"] == "test")
    items = {}

    def add(name, g, b, bits, psnr):
        items.setdefault(name, {}).setdefault((g, b), []).append((bits, psnr))
    for g in test:
        for b in C.BUDGET_QPS:
            if b not in infos[g]["static"]:     # a 2-budget work dir read from a 5-budget run (reanalysis.py)
                continue
            s = infos[g]["static"][b]
            add("STATIC", g, b, s["total_bits"], s["mean_psnr"])
            i = list(infos[g]["curve"]["qps"]).index(b)
            add("constant QP", g, b, infos[g]["curve"]["bits"][i], infos[g]["curve"]["psnr"][i])
            if C.CAUSAL:   # the best single constant QP within the scaled budget, chosen in hindsight (D30)
                cv, B = infos[g]["curve"], case_budget(infos, g, b)
                sc = [float(metrics.score(x, p, cv, B)) for x, p in zip(cv["bits"], cv["psnr"])]
                j = int(np.argmax(sc))
                add("best constant QP (hindsight)", g, b, cv["bits"][j], cv["psnr"][j])
    p = os.path.join(work, "results_baselines", "own_rc.pkl")
    if os.path.exists(p):
        for g, d in _load(p).items():
            for (b, m, aq), r in d.items():
                if g in infos and infos[g]["gop"]["split"] == "test" and not r.get("failed"):
                    add(f"own {m}{' +AQ' if aq else ''}", g, b, r["bits"], r["psnr"])
    p = os.path.join(work, "results_search", "search_test.pkl")
    if os.path.exists(p):
        for g, r in _load(p).items():
            for b, x in r.items():
                add("hindsight search", g, b, x["total_bits"], x["psnr"])
    p = os.path.join(work, "results_baselines", "rules.pkl")
    if os.path.exists(p):
        for (kind, k, mode), rows in _load(p)["test"].items():
            if mode == "fixed" and ((kind, k) in (("rule", 0), ("la_rule", 0), ("la_rule", 5), ("scene_rule", 5))
                                    or (C.CAUSAL and kind in ("static", "la_rule"))):
                for x in rows:
                    add(f"{kind} k={k}", x["gid"], x["budget"], x["bits"], x["psnr"])
    for p in sorted(glob.glob(os.path.join(work, "results_rl", "*", "eval.pkl"))):
        r = _load(p)
        base = os.path.basename(os.path.dirname(p)).rsplit("_s", 1)[0]
        a = r["args"]
        for (mode, k, split), rows in r["res"].items():
            if split != "test":
                continue
            if a["method"] == "anyk":
                label = f"{base} {mode}:{k}"
            else:
                extra = ["no-" + "-".join(sorted(a["drop"].split(",")))] if a["drop"] else []
                extra += ["prior"] * bool(a["prior"]) + [a["tag"]] * bool(a["tag"])
                extra += [f"train={a['train_family']}"] * bool(a.get("train_family"))
                extra += [a.get("extra", "")] * bool(a.get("extra")) + [f"lam={a.get('gate_lam', 0):g}"] * (a["method"] == "gate")
                label = " ".join([a["method"], f"{mode}:{k}"] + extra)
            for x in rows:
                add(label, x["gid"], x["budget"], x["bits"], x["psnr"])
    return infos, test, items


def case_budget(infos, g, b):
    """Budget of a (GOP, budget QP) case: the constant-QP bits at b, times the case's scale in causal mode (D30)."""
    return infos[g]["budget"][b] * (E.causal_scale(g, b) if C.CAUSAL else 1.0)


def per_case(infos, items):
    """method -> DataFrame indexed by (gid, budget): score, saving, saving_clip, over1 (seed means)."""
    out = {}
    for name, d in items.items():
        rec = []
        for (g, b), lst in d.items():
            cv, B = infos[g]["curve"], case_budget(infos, g, b)
            sv = np.array([float(metrics.saving(bt, ps, cv)) for bt, ps in lst])
            sc = np.array([float(metrics.score(bt, ps, cv, B)) for bt, ps in lst])
            o1 = np.array([bt > 1.01 * B for bt, _ in lst], float)
            rec.append((g, b, sc.mean(), sv.mean(), np.clip(sv, -CLIP, CLIP).mean(), o1.mean()))
        out[name] = pd.DataFrame(rec, columns=["gid", "b", "score", "saving", "saving_clip", "over1"]).set_index(
            ["gid", "b"]).sort_index()
    return out


def boot(d, n=2000, seed=0):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return d.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)


def fmt_ci(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


def table(D, names, gmap):
    rows = []
    for nm in names:
        if nm not in D:
            continue
        df = D[nm]
        r = {"method": nm, "n": len(df), "score": df.score.mean(), "saving": df.saving.mean(),
             "saving ±50": df.saving_clip.mean(), ">1% over": f"{100 * df.over1.mean():.0f}%"}
        for grp in GROUPS[1:]:
            idx = [k for k in df.index if grp in gmap[k[0]]]
            r[f"{grp} (saving ±50)"] = df.loc[idx].saving_clip.mean() if idx else np.nan
        for ref in (RULE, REF):
            if ref in D and nm != ref:
                j = df.index.intersection(D[ref].index)
                r[f"score vs {ref}"] = fmt_ci(boot(df.loc[j].score.values - D[ref].loc[j].score.values))
                r[f"saving ±50 vs {ref}"] = fmt_ci(boot(df.loc[j].saving_clip.values - D[ref].loc[j].saving_clip.values))
        rows.append(r)
    return pd.DataFrame(rows).round(2).to_markdown(index=False)


def winloss(infos, D, gmap, ref_rule="la_rule k=5"):
    if REF not in D or ref_rule not in D:
        return ["(k=5 policy or lookahead rule missing)"]
    pol = D[REF].saving_clip.groupby(level=0).mean()
    diff = (D[REF].saving_clip - D[ref_rule].saving_clip.reindex(D[REF].index)).groupby(level=0).mean()
    g = pol.index
    stats = {"max cut strength (hist_d)": [float(infos[x]["an"]["hist_d"][1:].max()) for x in g],
             "mean motion (msad)": [float(infos[x]["an"]["msad"][1:].mean()) for x in g],
             "mean spatial detail": [float(infos[x]["an"]["spatial"].mean()) for x in g]}
    L = [f"{len(g)} test GOPs; per GOP the k=5 CQL->PPO saving (±50 clipped, 3 seeds, both budgets) and its difference "
         f"from the {ref_rule} (non-learned lookahead counterpart).", "",
         "| statistic | low third: policy / vs rule | middle third | high third | Spearman (difference) |", "|---|---|---|---|---|"]
    for nm, v in stats.items():
        v = np.asarray(v)
        q = np.quantile(v, [1 / 3, 2 / 3])
        bins = np.digitize(v, q)
        cells = [f"{pol.values[bins == i].mean():.2f} / {diff.values[bins == i].mean():+.2f}" for i in range(3)]
        L.append(f"| {nm} | " + " | ".join(cells) + f" | {spearmanr(v, diff.values)[0]:+.2f} |")
    cut_s = np.asarray(stats["max cut strength (hist_d)"])
    mot = np.asarray(stats["mean motion (msad)"])
    hard = np.array(["scene cut" in gmap[x] for x in g])
    grad = np.array(["gradual" in gmap[x] for x in g])
    medm = np.median(mot[~hard & ~grad])
    types = {"gradual transition (fade)": grad,
             "hard cut, moderate (strength < 0.6)": hard & ~grad & (cut_s < 0.6),
             "hard cut, strong (>= 0.6)": hard & ~grad & (cut_s >= 0.6),
             "no cut, high motion": ~hard & ~grad & (mot > medm),
             "no cut, low motion": ~hard & ~grad & (mot <= medm)}
    rule = D[ref_rule].saving_clip.groupby(level=0).mean().reindex(g)
    L += ["", "| GOP type | GOPs | k=5 policy | rule | difference |", "|---|---|---|---|---|"]
    for nm, m in types.items():
        L.append(f"| {nm} | {m.sum()} | {pol.values[m].mean():.2f} | {rule.values[m].mean():.2f} | "
                 f"{diff.values[m].mean():+.2f} |")
    worst = diff.sort_values()[:6]
    L += ["", "Largest losses vs the rule: " + "; ".join(
        f"{x} {v:+.1f} (cut {infos[x]['an']['hist_d'][1:].max():.2f}, fade {int(infos[x]['an']['fade'].sum() > 0)})"
        for x, v in worst.items())]
    return L


def main():
    infos, test, items = collect(C.WORK)
    D = per_case(infos, items)
    gmap = {g: group_of(infos[g]) for g in test}
    cnt = {grp: sum(grp in v for v in gmap.values()) for grp in GROUPS}
    own = sorted(k for k in D if k.startswith("own"))
    meth = [f"{m} fixed:{k}" for k in (0, 5, 10) for m in ("bc", "cql", "iql", "bc_ppo", "cql_ppo", "ppo", "a2c", "dqn",
                                                             "lagr", "pid", "mpc")]
    kcurve = [f"cql_ppo fixed:{k}" for k in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 29)]
    feats = sorted(k for k in D if k.startswith("cql_ppo fixed:5 ") and ("no-" in k or "prior" in k))
    scene = sorted(k for k in D if k.startswith("anyk") or (k.startswith("cql_ppo ") and not k.startswith("cql_ppo fixed")))
    L = [f"# Breakdowns ({C.CODEC}, test)", "",
         f"Cases = (GOP, budget) pairs, seeds averaged. GOPs: " + ", ".join(f"{k} {v}" for k, v in cnt.items()) + ".",
         "score = saving − 2 × % over budget (ours). saving ±50 = saving clipped per case to ±50 % (the external "
         "report's headline). >1% over = share of cases more than 1 % over budget. Paired differences: 95 % bootstrap "
         "over cases.", "",
         "## Reference points and the encoder's own rate control", "",
         table(D, ["constant QP", "STATIC", "rule k=0", "la_rule k=0", "la_rule k=5", "scene_rule k=5", REF,
                   "hindsight search"] + own, gmap), "",
         "## RL approaches", "", table(D, meth, gmap), "",
         "## Lookahead curve (CQL->PPO)", "", table(D, kcurve, gmap), "",
         "## Feature ablations (k=5)", "", table(D, [REF] + feats, gmap), "",
         "## Scene-aware lookahead and any-k", "", table(D, [REF] + scene, gmap), "",
         "## Extensions (warm-started learners, ensemble, per-frame gate, fb/sum features, constraint fine-tuning)", "",
         table(D, [REF] + sorted(k for k in D if k.split()[0] in EXT_METHODS or
                                 (k.startswith("cql_ppo") and (" fb" in k or " sum" in k))), gmap), "",
         "## Where the k=5 policy wins and loses", ""] + winloss(infos, D, gmap)
    out = os.path.join(C.REPORTS, "breakdown_report.md")
    os.makedirs(C.REPORTS, exist_ok=True)
    open(out, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
