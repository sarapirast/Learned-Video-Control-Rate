"""Phase I: x265 and x264 side by side (run after both pipelines finished).

Each method is scored twice on the test split: against its own encoder's constant-QP curve ("own") and against
x265's constant-QP curve on the same GOP ("common" yardstick, which includes the x264-vs-x265 codec gap).
Paired 95 % CIs: RL k=5 vs each encoder's best own rate control, search vs RL, RL gain in x264 vs x265, codec gap.

  python experiments/codecs.py --x265 /scratch1/pbanga/rcwork --x264 /scratch1/pbanga/rcwork_x264
"""
import argparse
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, metrics  # noqa: E402

KS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 29)


def _load(p):
    with open(p, "rb") as f:
        return pickle.load(f)


def collect(work, quick):
    q = "_quick" if quick else ""
    infos = _load(os.path.join(work, f"results_infos{q}", "infos.pkl"))
    test = sorted(g for g, x in infos.items() if x["gop"]["split"] == "test")
    items = {}       # method -> {(gid, budget): (bits, psnr)}  (seed-averaged where seeds exist: bits/psnr of each seed kept)

    def add(name, g, b, bits, psnr):
        items.setdefault(name, {}).setdefault((g, b), []).append((bits, psnr))
    for g in test:
        for b in C.BUDGET_QPS:
            cq = infos[g]["curve"]
            i = list(cq["qps"]).index(b)
            add("constant QP", g, b, cq["bits"][i], cq["psnr"][i])
            s = infos[g]["static"][b]
            add("STATIC", g, b, s["total_bits"], s["mean_psnr"])
    p = os.path.join(work, f"results_baselines{q}", "own_rc.pkl")
    if os.path.exists(p):
        own = _load(p)
        for g in test:
            for (b, m, aq), r in own.get(g, {}).items():
                if r.get("failed"):
                    continue
                add(f"own {m}{' +AQ' if aq else ''}", g, b, r["bits"], r["psnr"])
    p = os.path.join(work, f"results_search{q}", "search_test.pkl")
    if os.path.exists(p):
        for g, r in _load(p).items():
            for b, x in r.items():
                add("hindsight search", g, b, x["total_bits"], x["psnr"])
    p = os.path.join(work, f"results_baselines{q}", "rules.pkl")
    if os.path.exists(p):
        for (kind, k, mode), rows in _load(p)["test"].items():
            if mode == "fixed" and kind in ("rule", "la_rule") and k in (0, 5):
                for x in rows:
                    add(f"{kind} k={k}", x["gid"], x["budget"], x["bits"], x["psnr"])
    for p in glob.glob(os.path.join(work, f"results_rl{q}", "*", "eval.pkl")):
        r = _load(p)
        a = r["args"]
        if a["method"] != "cql_ppo" or a["mode"] != "fixed" or a["drop"] or a["prior"] or a["tag"] or a.get("train_family"):
            continue
        for (mode, k, split), rows in r["res"].items():
            if split == "test":
                for x in rows:
                    add(f"RL k={k}", x["gid"], x["budget"], x["bits"], x["psnr"])
    return infos, items


def scores(infos_own, infos_ref, items, budget_from):
    """Per (gid, budget) penalised score vs own curve and vs reference (x265) curve; seeds averaged."""
    out = {}
    for name, d in items.items():
        rows = {}
        for (g, b), lst in d.items():
            B = budget_from[g]["budget"][b]
            own = np.mean([metrics.score(bt, ps, infos_own[g]["curve"], infos_own[g]["budget"][b]) for bt, ps in lst])
            # outside the reference curve's PSNR range the log-bits extrapolation explodes: left out, counted
            rp = infos_ref[g]["curve"]["psnr"]
            ok = [(bt, ps) for bt, ps in lst if min(rp) <= ps <= max(rp)]
            com = np.mean([metrics.score(bt, ps, infos_ref[g]["curve"], infos_ref[g]["budget"][b]) for bt, ps in ok]) \
                if ok else np.nan
            sav_c = np.mean([metrics.saving(bt, ps, infos_ref[g]["curve"]) for bt, ps in ok]) if ok else np.nan
            over = np.mean([bt > B for bt, ps in lst])
            rows[(g, b)] = (own, com, sav_c, over)
        out[name] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--x265", default="/scratch1/pbanga/rcwork")
    ap.add_argument("--x264", default="/scratch1/pbanga/rcwork_x264")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    inf5, it5 = collect(a.x265, a.quick)
    inf4, it4 = collect(a.x264, a.quick)
    S = {"x265": scores(inf5, inf5, it5, inf5), "x264": scores(inf4, inf5, it4, inf4)}
    rows = []
    order = ["constant QP", "STATIC"] + sorted(k for k in set(it5) | set(it4) if k.startswith("own")) + \
        ["rule k=0", "la_rule k=0", "la_rule k=5"] + [f"RL k={k}" for k in KS] + ["hindsight search"]
    srch = {e: S[e].get("hindsight search", {}) for e in S}
    stat = {e: S[e].get("STATIC", {}) for e in S}
    for name in order:
        for enc in ("x265", "x264"):
            d = S[enc].get(name)
            if not d:
                continue
            v = np.array(list(d.values()))
            r = {"method": name, "encoder": enc, "n": len(v), "score own": v[:, 0].mean(), "score common": np.nanmean(v[:, 1]),
                 "saving common": np.nanmean(v[:, 2]), "out of ref range": int(np.isnan(v[:, 1]).sum()), "over %": 100 * v[:, 3].mean()}
            if srch[enc] and stat[enc]:
                keys = [k for k in d if k in srch[enc] and k in stat[enc]]
                num = sum(d[k][0] - stat[enc][k][0] for k in keys)
                den = sum(srch[enc][k][0] - stat[enc][k][0] for k in keys)
                r["share of search gain"] = num / den if den else np.nan
            rows.append(r)
    lines = ["# x265 vs x264", "", "score own = penalised saving vs the encoder's own constant QP; score common = the same "
             "bits/PSNR scored against x265's constant-QP curve on the same GOP (includes the codec gap).", "",
             pd.DataFrame(rows).round(3).to_markdown(index=False), "", "## Paired comparisons (test, 95 % CI)", ""]

    def pc(enc_a, name_a, enc_b, name_b, col=0, label=""):
        da, db = S[enc_a].get(name_a, {}), S[enc_b].get(name_b, {})
        keys = [k for k in sorted(set(da) & set(db)) if not (np.isnan(da[k][col]) or np.isnan(db[k][col]))]
        if len(keys) < 2:
            return
        d, ci = metrics.paired_ci([da[k][col] for k in keys], [db[k][col] for k in keys])
        lines.append(f"- {label or f'{enc_a} {name_a} − {enc_b} {name_b}'}: {d:+.3f} ± {ci:.3f} (n={len(keys)})")
    for enc in ("x265", "x264"):
        owns = [k for k in S[enc] if k.startswith("own")]
        if owns and "RL k=5" in S[enc]:
            best = max(owns, key=lambda k: np.mean([v[0] for v in S[enc][k].values()]))
            pc(enc, "RL k=5", enc, best, label=f"{enc}: RL k=5 − best own RC ({best})")
        pc(enc, "hindsight search", enc, "RL k=5", label=f"{enc}: search − RL k=5")
    # RL gain over STATIC, x264 vs x265 (own yardstick)
    g5 = {k: S["x265"]["RL k=5"][k][0] - S["x265"]["STATIC"][k][0] for k in S["x265"].get("RL k=5", {})}
    g4 = {k: S["x264"]["RL k=5"][k][0] - S["x264"]["STATIC"][k][0] for k in S["x264"].get("RL k=5", {})}
    keys = sorted(set(g5) & set(g4))
    if len(keys) > 1:
        d, ci = metrics.paired_ci([g4[k] for k in keys], [g5[k] for k in keys])
        lines.append(f"- RL k=5 gain over STATIC, x264 − x265: {d:+.3f} ± {ci:.3f} (n={len(keys)})")
    pc("x264", "constant QP", "x265", "constant QP", col=2, label="codec gap: x264 CQP saving vs x265 CQP (common)")
    out = os.path.join(C.REPORTS, f"codecs{'_quick' if a.quick else ''}_report.md")
    os.makedirs(C.REPORTS, exist_ok=True)
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
