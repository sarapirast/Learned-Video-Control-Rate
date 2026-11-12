"""Phase B: non-learned baselines.

stages
  spend_curve     average cumulative STATIC spend share per frame on train (the causal rule's target curve)
  own_rc          the encoder's own rate control on val+test (ABR, 2-pass, ABR+VBV; each with/without AQ+cutree) [sharded]
  static_pattern  refit the fixed pattern (I, early P, late P, split) on a train subset by grid search [sharded]
  rules           tune rule / lookahead rule / scene rule on val (grid), evaluate the chosen ones on test at every k

  python experiments/baselines.py --stage spend_curve
  RC_NSHARDS=8 sbatch --array=0-7 ... baselines.py --stage own_rc ; then --stage gather_own_rc
  RC_NSHARDS=8 sbatch --array=0-7 ... baselines.py --stage static_pattern ; then --stage gather_static_pattern
  python experiments/baselines.py --stage rules
  python experiments/baselines.py --report
"""
import itertools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import codec, config as C, data, env as E, metrics, offrl, policies as P, runner  # noqa: E402
from rclib.runner import log  # noqa: E402

OWN_MODES = [(m, aq) for m in ("abr", "2pass", "abr_vbv") for aq in (False, True)]
PATTERN_GRID = {"I": (-9, -6, -4, -2), "early": (-4, -3, -2, -1, 0), "late": (0, 1, 2, 3, 4), "split": (5, 10, 15)}
N_PATTERN_GOPS = 120
RULE_GRID = {"rule": [{"gain": g} for g in (1, 2, 3, 4, 6, 8)],
             "la_rule": [{"gain": g, "sens": s} for g in (0.5, 0.75, 1.0) for s in (4.0, 5.0, 6.0)],
             "scene_rule": [{"gain": g, "sens": s, "cut_boost": c} for g in (0.75, 1.0) for s in (5.0,)
                            for c in (0.5, 1.0, 1.5)]}
LA_KS = (0, 1, 2, 3, 5, 7, 10, 15, 20, 29)


def ids_of(infos, splits):
    return sorted(g for g, x in infos.items() if x["gop"]["split"] in splits)


# ---------------------------------------------------------------- stages

def spend_curve(infos):
    cur = []
    for g in ids_of(infos, ["train"]):
        for b in C.BUDGET_QPS:
            bits = np.asarray(infos[g]["static"][b]["bits"], float)
            cur.append(np.r_[0.0, np.cumsum(bits)[:-1]] / bits.sum())
    return np.mean(cur, 0)


def _own(args):
    info = args
    p, src = data.gop_path(info["gop"]), data.gop_frames(info["gop"])
    out = {}
    for b in C.BUDGET_QPS:
        B = info["budget"][b] * (E.causal_scale(info["gop"]["id"], b) if C.CAUSAL else 1.0)   # D30: same budget as the learners
        for m, aq in OWN_MODES:
            try:
                r = codec.encode_own_rc(p, B, m, aq=aq, src=src)
            except RuntimeError:          # e.g. x264 2-pass at a ~3 kbps budget (near-black GOPs): left out, counted
                out[(b, m, aq)] = {"failed": True}
                continue
            sav = float(metrics.saving(r["total_bits"], r["mean_psnr"], info["curve"]))
            out[(b, m, aq)] = {"saving": sav, "over_pct": float(metrics.overshoot(r["total_bits"], B)),
                               "over": r["total_bits"] > B, "score": float(metrics.score(r["total_bits"], r["mean_psnr"],
                                                                                         info["curve"], B)),
                               "bits": r["total_bits"], "psnr": r["mean_psnr"]}
    return info["gop"]["id"], out


def _pattern(args):
    info, patterns = args
    p, src = data.gop_path(info["gop"]), data.gop_frames(info["gop"])
    out = {}
    for pat in patterns:
        offs = C.static_offsets(pat[:3], pat[3])
        for b in C.BUDGET_QPS:
            r = codec.encode(p, [b + o for o in offs], src=src)
            out[(pat, b)] = float(metrics.score(r["total_bits"], r["mean_psnr"], info["curve"], info["budget"][b]))
    return info["gop"]["id"], out


def tune_rules(infos, ipath, curve, quick):
    val, test = ids_of(infos, ["val"]), ids_of(infos, ["test"])
    out = {"val": {}, "test": {}}
    grid = {k: v[:2] for k, v in RULE_GRID.items()} if quick else RULE_GRID
    for kind, params in grid.items():
        k_tune = 0 if kind == "rule" else 5
        for prm in params:
            spec = {"kind": kind, **prm, **({"curve": curve} if kind == "rule" else {})}
            res = P.evaluate(spec, ipath, val, desc=f"val {kind} {prm}", k=k_tune)
            out["val"][(kind, tuple(sorted(prm.items())))] = res
            log(f"val {kind} {prm}: score {np.mean([r['score'] for r in res]):.3f}")
    best = {}
    for kind in grid:
        cands = [(np.mean([r["score"] for r in v]), key) for key, v in out["val"].items() if key[0] == kind]
        best[kind] = dict(max(cands)[1][1])
        log(f"chosen {kind}: {best[kind]}")
    # test: causal rule once; lookahead rules at every k (the rule's lookahead curve) and in scene modes
    out["test"][("rule", 0, "fixed")] = P.evaluate({"kind": "rule", **best["rule"], "curve": curve}, ipath, test,
                                                   desc="test rule", k=0)
    if C.CAUSAL:   # D30: STATIC around the model base QP; lookahead rules only at the k the causal study uses
        out["test"][("static", 0, "fixed")] = P.evaluate({"kind": "static"}, ipath, test, desc="test static", k=0)
        for k in (0, 1, 2, 3, 5):
            out["test"][("la_rule", k, "fixed")] = P.evaluate({"kind": "la_rule", **best["la_rule"]}, ipath, test,
                                                              desc=f"test la_rule k={k}", k=k)
        out["best"] = best
        return out
    for kind in ("la_rule", "scene_rule"):
        for k in ((0, 5) if quick else LA_KS):
            out["test"][(kind, k, "fixed")] = P.evaluate({"kind": kind, **best[kind]}, ipath, test,
                                                         desc=f"test {kind} k={k}", k=k)
        for mode in ("scene_trunc", "scene_ext", "cut_trig"):
            for k in ((5,) if quick else (5, 10, 29)):
                out["test"][(kind, k, mode)] = P.evaluate({"kind": kind, **best[kind]}, ipath, test,
                                                          desc=f"test {kind} {mode} k={k}", k=k, mode=mode)
    out["best"] = best
    return out


def main():
    a = runner.args()
    st = runner.Stages("baselines", a.quick)
    if a.report:
        return report(st)
    infos_st = runner.Stages("infos", a.quick)
    infos = infos_st.load("infos")
    s = a.stage
    if s in (None, "spend_curve"):
        st.run("spend_curve", lambda: spend_curve(infos))
    if s in (None, "own_rc"):
        mine = data.shard(ids_of(infos, ["val", "test"]), a.nshards, a.shard)
        st.run("own_rc", lambda: dict(runner.pmap(_own, [infos[g] for g in mine], desc="own_rc")), a.shard, a.nshards)
    if s in ("gather_own_rc",) or (s is None and a.nshards == 1):
        st.gather("own_rc", a.nshards)
    if s in (None, "static_pattern"):
        tr = ids_of(infos, ["train"])
        rng = np.random.default_rng(0)
        sub = sorted(rng.choice(tr, min(N_PATTERN_GOPS if not a.quick else 3, len(tr)), replace=False))
        pats = list(itertools.product(*PATTERN_GRID.values()))
        if a.quick:
            pats = pats[:4] + [(-6, -3, 3, 10)]
        mine = data.shard(sub, a.nshards, a.shard)
        st.run("static_pattern", lambda: dict(runner.pmap(_pattern, [(infos[g], pats) for g in mine],
                                                          desc="static_pattern")), a.shard, a.nshards)
    if s in ("gather_static_pattern",) or (s is None and a.nshards == 1):
        st.gather("static_pattern", a.nshards)
    if s == "rules" and not st.done("spend_curve"):
        st.run("spend_curve", lambda: spend_curve(infos))
    if s in (None, "rules"):
        slim = {g: offrl.slim(x) for g, x in infos.items()}
        ipath = P.save_infos_for_workers(slim, os.path.join(infos_st.dir, "infos_slim.pkl"))
        curve = st.load("spend_curve")
        st.run("rules", lambda: tune_rules(slim, ipath, curve, a.quick))
    if s is None:
        report(st)


def _row(name, rows):
    sm = metrics.summarize(rows)
    return {"method": name, "n": sm["n"], "score": sm["score"], "ci": sm["score_ci"], "saving": sm["saving"],
            "over %": sm["over_pct"]}


def report(st):
    import pandas as pd
    lines = [f"# Baselines ({C.CODEC})", ""]
    infos = runner.Stages("infos", st.quick).load("infos")
    test = ids_of(infos, ["test"])
    tab = []
    for b in C.BUDGET_QPS:
        tab.append(_row(f"STATIC @QP{b}", [infos[g]["static"][b] for g in test]))
    if st.done("own_rc"):
        own = st.load("own_rc")
        for b in C.BUDGET_QPS:
            for m, aq in OWN_MODES:
                rows = [own[g][(b, m, aq)] for g in test if g in own]
                ok = [r for r in rows if not r.get("failed")]
                tab.append(_row(f"own {m}{' +AQ' if aq else ''} @QP{b}", ok) | {"encoder failed": len(rows) - len(ok)})
    if st.done("rules"):
        ru = st.load("rules")
        lines += [f"Rules chosen on validation: {ru['best']}", ""]
        for key, rows in ru["test"].items():
            tab.append(_row(f"{key[0]} k={key[1]} {key[2]}", rows) | {"frames seen": np.mean([r['frames_seen'] for r in rows])})
    lines += [pd.DataFrame(tab).round(3).to_markdown(index=False), ""]
    if st.done("static_pattern"):
        sp = st.load("static_pattern")
        agg = {}
        for g, d in sp.items():
            for (pat, b), v in d.items():
                agg.setdefault(pat, []).append(v)
        ranked = sorted(((np.mean(v), p) for p, v in agg.items()), reverse=True)
        cur = (*C.STATIC, C.STATIC_SPLIT)
        lines += ["Fixed-pattern refit on train (mean penalised score over both budgets):", "",
                  "| rank | (I, early, late, split) | score |", "|---|---|---|"]
        lines += [f"| {i + 1} | {p} | {s:.3f} |" for i, (s, p) in enumerate(ranked[:10])]
        lines += [f"| used | {cur} | {np.mean(agg[cur]):.3f} |" if cur in agg else ""]
    if st.done("spend_curve"):
        lines += ["", "Average STATIC cumulative spend share at frames 1, 5, 10, 20: " +
                  ", ".join(f"{st.load('spend_curve')[t]:.3f}" for t in (1, 5, 10, 20))]
    out = os.path.join(C.REPORTS, f"baselines{'_quick' if st.quick else ''}_report.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
