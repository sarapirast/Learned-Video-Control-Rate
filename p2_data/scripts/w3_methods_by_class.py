"""Week 3: every method's score by GOP class, and the share of the hindsight search's score it captures.
(P2, docs/p2-plan.md "Week 3"; tracker item 22)

Part A, orig arm (Pavneet's budgets, which leak the GOP's cost; his settings): the learned methods (BC, CQL->PPO,
  Lagrangian PPO; 3 seeds pooled) at each k vs the search, test split, from rcwork_v1/<codec>_orig/results_rl/*/eval.pkl
  and results_search/search_test.pkl. Shaped runs (..._shape1_...) are listed separately when present.
Part B, leak-free arm (P2 budgets.csv, P1 settings): P2's baselines + controller v1 (results_v1/baselines_v1.parquet)
  vs the leak-free search (rcwork_v1/<codec>_lf/results_search/search_test.pkl). Skipped until that file exists.

"captured_%" = mean method score / mean search score on the same GOP x budget rows (paired), per class: the share of
the search's score, measured from best constant QP in hindsight (score 0), independent of any pattern.
"gain_share_%" = (method - start) / (search - start), Pavneet's "share of search gain" (experiments/analysis.py), where
start = the search's start plan (orig: STATIC at the budget QP; lf: the ramp at the hindsight base q). It depends on
the start pattern (STATIC scores about -8 on x264, which inflates it). Flat (grayscale) GOPs listed in
data/v1/320x180/rd/flat_gops.csv are excluded from both parts (scripts/flat_gops_v1.py); RC_KEEP_FLAT=1 keeps them. CIs are 95% bootstraps over clips. Score: % bits saved at equal PSNR vs the GOP's own constant-QP curve, minus 2 per 1% over.

  python -I scripts/w3_methods_by_class.py <x264|x265> [orig|lf|both]
Out: results_v1/w3/methods_by_class_<codec>_<arm>.md (+ .csv)
"""
import glob
import os
import pickle
import re
import sys

import numpy as np
import pandas as pd

RC = "/scratch1/aayushso/rcwork_v1"
ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/w3"
RNG = np.random.default_rng(0)
CLASSES = ("stable", "cut", "gradual")
FLAT_CSV = f"{ROOT}/data/v1/320x180/rd/flat_gops.csv"


def flat_table():
    f = pd.read_csv(FLAT_CSV)
    return f[f.flat] if os.environ.get("RC_KEEP_FLAT") != "1" else f.iloc[:0]


def boot_ratio(m, s, clips, n=2000):
    """mean(m) / mean(s) with a clip bootstrap CI."""
    m, s, clips = np.asarray(m, float), np.asarray(s, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    rs = []
    for _ in range(n):
        ii = np.concatenate([idx[c] for c in RNG.choice(u, len(u))])
        rs.append(m[ii].mean() / s[ii].mean())
    return m.mean() / s.mean(), np.percentile(rs, 2.5), np.percentile(rs, 97.5)


def summarize(d, keys):
    rows = []
    for k, x in d.groupby(keys, observed=True):
        k = k if isinstance(k, tuple) else (k,)
        for cls in ("all",) + CLASSES:
            y = x if cls == "all" else x[x.cls == cls]
            if len(y) < 2:
                continue
            r, lo, hi = boot_ratio(y.score, y.search, y["clip"])
            g, glo, ghi = boot_ratio(y.score - y.start, y.search - y.start, y["clip"])
            rows.append({**dict(zip(keys, k)), "class": cls, "n": len(y), "score": y.score.mean(),
                         "search": y.search.mean(), "gap": (y.search - y.score).mean(),
                         "pct_over": 100 * y.over.mean(), "captured_%": 100 * r,
                         "ci": f"[{100 * lo:.0f}, {100 * hi:.0f}]", "gain_share_%": 100 * g,
                         "gain_ci": f"[{100 * glo:.0f}, {100 * ghi:.0f}]"})
    return pd.DataFrame(rows)


def md(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(out)


def pivot_captured(t, index, value="captured_%"):
    p = t.pivot_table(index=index, columns="class", values=value, observed=True)
    return p[[c for c in ("all",) + CLASSES if c in p.columns]].round(0).reset_index()


def part_a(codec):
    work = f"{RC}/{codec}_orig"
    infos = pickle.load(open(f"{work}/results_infos/infos.pkl", "rb"))
    srch = pickle.load(open(f"{work}/results_search/search_test.pkl", "rb"))
    rows, flat = [], set(flat_table().gid)
    for p in sorted(glob.glob(f"{work}/results_rl/*/eval.pkl")):
        run = os.path.basename(os.path.dirname(p))
        m = re.match(r"(bc|cql_ppo|lagr)_k(\d+)_fixed(_shape[\d.]+)?_s(\d)$", run)
        if not m:
            continue
        res = pickle.load(open(p, "rb"))["res"]
        k = int(m.group(2))
        for e in res.get(("fixed", k, "test"), []):
            g = infos[e["gid"]]["gop"]
            if e["gid"] in flat:
                continue
            rows.append({"method": m.group(1) + (m.group(3) or ""), "k": k, "seed": int(m.group(4)), "gid": e["gid"],
                         "clip": g["clip"], "cls": g["label"], "budget": e["budget"], "score": e["score"],
                         "over": e["over"], "search": srch[e["gid"]][e["budget"]]["best_score"],
                         "start": srch[e["gid"]][e["budget"]]["static_score"]})
    d = pd.DataFrame(rows)
    t = summarize(d, ["method", "k"])
    L = [f"## A. Learned methods vs the search, orig arm (leaky budgets, Pavneet's settings), {codec} test", "",
         "Seeds pooled (3 per method and k). captured_% = mean score / mean search score on the same GOP x budget rows.",
         "", "**Share of the search's score captured, by class (%)**", "", md(pivot_captured(t, ["method", "k"])), "",
         "**Share of the search's gain over STATIC (Pavneet's measure), by class (%)**", "",
         md(pivot_captured(t, ["method", "k"], "gain_share_%")), "", "**Full table**", "", md(t), ""]
    return L, d.assign(arm="orig")


def part_b(codec):
    p = f"{RC}/{codec}_lf/results_search/search_test.pkl"
    if not os.path.exists(p):
        return [f"## B. Leak-free arm ({codec}): skipped, {p} not there yet", ""], None
    infos = pickle.load(open(f"{RC}/{codec}_lf/results_infos/infos.pkl", "rb"))
    srch = pickle.load(open(p, "rb"))
    key = lambda g, b: (infos[g]["gop"]["clip"], int(infos[g]["gop"]["v1_gop"]), int(b))  # noqa: E731
    best = {key(g, b): x["best_score"] for g, r in srch.items() for b, x in r.items()}
    start = {key(g, b): x["static_score"] for g, r in srch.items() for b, x in r.items()}
    df = pd.read_parquet(f"{ROOT}/results_v1/baselines_v1.parquet").query("encoder == @codec and split == 'test'")
    df = df.rename(columns={"label": "cls", "clip_id": "clip"})
    ft = flat_table()
    n0, fk = len(df), set(zip(ft.clip_id, ft.gop))
    df = df[[(c, int(g)) not in fk for c, g in zip(df["clip"], df.gop)]]
    print(f"part B: dropped {n0 - len(df)} flat-GOP rows")
    df["search"] = [best[(c, int(g), int(lv))] for c, g, lv in zip(df["clip"], df.gop, df.level_q0)]
    df["start"] = [start[(c, int(g), int(lv))] for c, g, lv in zip(df["clip"], df.gop, df.level_q0)]
    t = summarize(df, ["method", "k"])
    L = [f"## B. P2 baselines + controller v1 vs the leak-free search, {codec} test", "",
         "Budgets: budgets.csv (4 levels); P1 settings. Hindsight methods are listed at k=29.", "",
         "**Share of the search's score captured, by class (%)**", "", md(pivot_captured(t, ["method", "k"])), "",
         "**Share of the search's gain over its ramp start, by class (%)**", "",
         md(pivot_captured(t, ["method", "k"], "gain_share_%")), "", "**Full table**", "", md(t), ""]
    return L, df[["method", "k", "clip", "gop", "level_q0", "cls", "score", "over", "search", "start"]].assign(arm="lf")


def main(codec, which="both"):
    os.makedirs(OUT, exist_ok=True)
    for arm, fn in (("orig", part_a), ("lf", part_b)):
        if which not in (arm, "both"):
            continue
        L, d = fn(codec)
        head = [f"# Week 3: methods by GOP class vs the hindsight search ({codec}, arm {arm})", "",
                "Generated by `scripts/w3_methods_by_class.py`. CIs: 95% bootstrap over clips.", ""]
        out = f"{OUT}/methods_by_class_{codec}_{arm}.md"
        open(out, "w").write("\n".join(head + L) + "\n")
        if d is not None:
            d.to_csv(out.replace(".md", ".csv"), index=False)
        print("\n".join(L[:12]))
        print(f"-> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
