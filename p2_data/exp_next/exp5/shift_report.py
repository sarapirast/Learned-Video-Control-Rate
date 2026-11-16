"""Experiment 5a report: final4 + fixed shift. Pre-registration: exp_next/exp5/PREREG_SHIFT.md.

  python -I exp_next/exp5/shift_report.py --split fold    selection per encoder -> shift_selected.json
  python -I exp_next/exp5/shift_report.py --split val     confirmation of the selected variant vs final4
Inputs: results_v1/next/exp5/shift_rows_<enc>_<split>_*of*.pkl; final4 = infos 'ctrl' rows (rcwork_v1/<enc>_resh).
Out: results_v1/next/exp5/shift_<split>.md (+ shift_selected.json for fold)
"""
import argparse
import glob
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import metrics  # noqa: E402

RC = "/scratch1/aayushso/rcwork_v1"
OUT = "/scratch1/aayushso/ee599/results_v1/next/exp5"
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)])
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def fmt(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" + (" *" if t[1] > 0 or t[2] < 0 else "")


def load(split):
    rows = []
    for enc in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
        files = sorted(glob.glob(f"{OUT}/shift_rows_{enc}_{split}_*of*.pkl"))
        files = [f for f in files if "_limit" not in f]
        assert files, (enc, split)
        for r in (x for f in files for x in pickle.load(open(f, "rb"))):
            g, lv, k = r["gid"], r["level"], r["k"]
            cv, B, c = infos[g]["curve"], infos[g]["budget"][lv], infos[g]["ctrl"][(lv, k)]
            assert abs(r["static_score"] - c["score"]) < 1e-9
            p4 = c["dpsnr"] + metrics.psnr_at_bits(cv, B)                       # final4's PSNR
            assert abs(metrics.score(c["bits"], p4, cv, B) - c["score"]) < 1e-6
            base = {"enc": enc, "gid": g, "clip": r["clip"], "level": lv, "k": k, "hole": B > max(cv["bits"]),
                    "recap": r["recap"], "score": r["score"], "rho": r["bits"] / B,
                    "A": float(r["psnr"] - metrics.psnr_at_bits(cv, r["bits"])), "final4": c["score"],
                    "rho_f4": c["bits"] / B, "A_f4": float(p4 - metrics.psnr_at_bits(cv, c["bits"])),
                    "mean_off": float(np.mean(np.array(r["qps"]) - np.array(r["ctrl_qps"]))),
                    "qbin": r.get("qbin"), "f4_level0": r.get("f4_level0"),
                    "cls": "cut/gradual" if infos[g]["gop"]["label"] in ("cut", "gradual") else "stable"}
            for v in r["variants"]:
                rows.append(dict(base, variant=v))
    return pd.DataFrame(rows)


def decomp(x, pre=""):
    s = x[pre + "score"] if pre == "" else x["final4"]
    A, rho = (x.A, x.rho) if pre == "" else (x.A_f4, x.rho_f4)
    return {"score": s.mean(), "A": A.mean(), "E-P": (s - A).mean(), "mean |err| %": 100 * (rho - 1).abs().mean(),
            "signed err %": 100 * (rho - 1).mean(), "% over": 100 * (rho > 1).mean(),
            "p90 |err| %": 100 * (rho - 1).abs().quantile(0.9)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="fold", choices=("fold", "val"))
    ap.add_argument("--rev4", action="store_true", help="REVISION 4 (post-hoc): per-qbin:bit, k5 only, val")
    a = ap.parse_args()
    d = load(a.split)
    y = d[~d.hole]
    L = [f"# Exp 5a: final4 + fixed shift, {a.split} (exp_next/exp5/shift_report.py)", "",
         "Score in dB, real encodes, deterministic. Level-24-hole episodes excluded unless stated. Pre-registration: "
         "exp_next/exp5/PREREG_SHIFT.md. The shift is a schedule distilled from the search by weighted averaging, "
         "not RL.", ""]
    if a.split == "fold":
        L += ["Caveat: final4's rate model was fitted on all train clips including the fold.", ""]
        sel = {}
        for enc, x in y.groupby("enc"):
            t = x.groupby("variant").apply(lambda z: pd.Series(dict(
                n=len(z), **decomp(z), minus_final4=(z.score - z.final4).mean())), include_groups=False)
            f4 = decomp(x[x.variant == x.variant.iloc[0]], "f4")
            ok = [v for v in t.index if v != "pooled:full"]            # pooled:full = reference arm only
            best = t.score[ok].max()
            cand = [v for v in ok if t.score[v] >= best - 0.005]
            key = lambda v: (v.split(":")[0] == "pooled", v.split(":")[1] == "bit")  # noqa: E731
            sel[enc] = max(cand, key=key)
            L += [f"## {enc}", "", t.sort_values("score", ascending=False).round(3).to_markdown(), "",
                  "final4 on the same episodes: " + ", ".join(f"{k} {v:.3f}" for k, v in f4.items()), "",
                  f"Within 0.005 dB of the best selectable arm: {', '.join(cand)}. **Selected ({enc}): {sel[enc]}** "
                  "(shift:cap rule; pooled:full is a reference arm, not selectable)", ""]
            z = x[x.variant == sel[enc]]
            L += ["Selected variant by k (minus final4, fold clip bootstrap): " + "; ".join(
                f"k{k} {fmt(boot(q.score - q.final4, q['clip']))}" for k, q in z.groupby("k")), ""]
        L += ["## Selection under REVISION 2 (superseded by REVISION 3 below)", "", json.dumps(sel), ""]
        # REVISION 3: the budget level is clip-level hindsight; the causal per-qbin arm decides what goes to val
        sel = {}
        if "perqbin:bit" in set(y.variant):
            L += ["## REVISION 3: per-qbin:bit (causal) vs perlevel:bit", "",
                  "Rule per encoder: per-qbin:bit >= perlevel:bit - 0.01 dB (mean of shift - final4, pooled over k "
                  "0/5 and levels, hole excluded) -> per-qbin:bit goes to val; otherwise no shift arm goes to val.", ""]
            for enc, x in y.groupby("enc"):
                q = x[x.variant == "perqbin:bit"].set_index(["gid", "level", "k"])
                lv = x[x.variant == "perlevel:bit"].set_index(["gid", "level", "k"])
                assert len(q) == len(lv) and q.index.sort_values().equals(lv.index.sort_values())
                lv = lv.loc[q.index]
                gq, gl = (q.score - q.final4).mean(), (lv.score - lv.final4).mean()
                ok = gq >= gl - 0.01
                sel[enc] = "perqbin:bit" if ok else None
                L += [f"- {enc}: per-qbin:bit {gq:+.3f} vs perlevel:bit {gl:+.3f} (kept {100 * gq / gl:.0f}% of the "
                      f"gain; per-qbin - perlevel {fmt(boot(q.score - lv.score, q['clip']))}); bin = level on "
                      f"{100 * np.mean(q.qbin == q.index.get_level_values('level')):.0f}% of episodes -> "
                      f"**{'per-qbin:bit goes to val' if ok else 'FAILS: the gain depends on budget-level hindsight; no val run'}**",
                      "  - per-qbin:bit by k (minus final4): " + "; ".join(
                          f"k{k} {fmt(boot(z.score - z.final4, z['clip']))}" for k, z in q.reset_index().groupby("k")),
                      "  - per-qbin:bit spend vs final4: " + ", ".join(
                          f"{c} {decomp(q)[c]:.3f} vs {decomp(q, 'f4')[c]:.3f}" for c in
                          ("A", "E-P", "mean |err| %", "p90 |err| %", "signed err %", "% over"))]
            L += [""]
        json.dump(sel, open(f"{OUT}/shift_selected.json", "w"))
        L += ["## Selection (REVISION 3; null = no val run)", "", json.dumps(sel), ""]
    else:
        sel = json.load(open(f"{OUT}/shift_selected.json"))
        if a.rev4:
            sel = {"x264": "perqbin:bit", "x265": "perqbin:bit"}
            y, d = y[y.k == 5], d[d.k == 5]
            assert len(y) and set(y.enc) == {"x264", "x265"}
            L += ["**REVISION 4 (POST-HOC): per-qbin:bit at k5 only, chosen on the fold after its REVISION 3 result.**",
                  ""]
        y = y[[v == sel.get(e) for v, e in zip(y.variant, y.enc)]]
        d = d[[v == sel.get(e) for v, e in zip(d.variant, d.enc)]]
        diff = y.score - y.final4
        L += [f"Variants: {json.dumps(sel)}", "",
              "## PRIMARY (REVISION 4): (final4 + shift) - final4 per encoder, k5" if a.rev4 else
              "## PRIMARY (REVISION 3): (final4 + shift) - final4 per encoder, k 0/5 pooled", ""]
        for e, x in y.groupby("enc"):
            dx = x.score - x.final4
            pe = boot(dx, x["clip"])
            L += [f"- **{e}: {fmt(pe)} (n {len(x)}) -> {'HELPS' if pe[1] > 0 else 'DOES NOT HELP'}** (CI above 0)",
                  "  - by k: " + "; ".join(f"k{k} {fmt(boot(dx[x.k == k], x.loc[x.k == k, 'clip']))}" for k in sorted(x.k.unique())),
                  "  - cut/gradual vs stable: " + "; ".join(
                      f"{c} {fmt(boot(dx[x.cls == c], x.loc[x.cls == c, 'clip']))} (n {int((x.cls == c).sum())})"
                      for c in ("cut/gradual", "stable")),
                  "  - by level (budget, reported only): " + "; ".join(
                      f"L{lv} {dx[x.level == lv].mean():+.3f}" for lv in sorted(x.level.unique()))]
        if y.enc.nunique() == 2:
            L += [f"- pooled over encoders (reported): {fmt(boot(diff, y['clip']))}"]
        L += [""]
        rows = []
        for (e, k), x in y.groupby(["enc", "k"]):
            rows.append({"enc": e, "k": k, "method": "final4 + shift", **decomp(x)})
            rows.append({"enc": e, "k": k, "method": "final4", **decomp(x, "f4")})
        for (e, c), x in y.groupby(["enc", "cls"]):
            rows.append({"enc": e, "k": c, "method": "final4 + shift", **decomp(x)})
            rows.append({"enc": e, "k": c, "method": "final4", **decomp(x, "f4")})
        t = pd.DataFrame(rows)
        L += ["## Decomposition (A = quality for the bits, E-P = landing)", "", t.round(3).to_markdown(index=False), ""]
        flags = []
        for (e, k), x in y.groupby(["enc", "k"]):
            s, f = decomp(x), decomp(x, "f4")
            ds, do = s["signed err %"] - f["signed err %"], s["% over"] - f["% over"]
            if ds > 1 or do > 10:
                flags.append(f"{e} k{k}: signed error {ds:+.2f} pp, % over {do:+.1f} pts")
        L += ["## Level-effect check (signed spend error +1 pp or % over +10 pts vs final4)", "",
              "; ".join(flags) if flags else "none", "",
              "With the hole included: " + "; ".join(f"{e} {fmt(boot(x.score - x.final4, x['clip']))}"
                                                     for e, x in d.groupby("enc")),
              ""]
    open(f"{OUT}/shift_{a.split}{'_rev4' if a.rev4 else ''}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
