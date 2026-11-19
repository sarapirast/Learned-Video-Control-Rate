"""TA feedback on the milestone (2026-11-17): report quality and budget violations separately, and count the scene
detector's own lookahead. No new encodes; reads the finished results of a work dir (same loader as breakdown.py).

Per method on the test split, per (GOP, budget) case (seeds averaged per case):
  quality    dPSNR_B  = PSNR - PSNR of constant QP at exactly the case's budget (dB, no penalty of any kind); a budget
             outside the measured curve (more than QP 18 or less than QP 50 spends) is clamped to the curve's end
             saving   = % bits saved vs constant QP at equal PSNR (unpenalised; the milestone's 'saving')
  spending   spend    = bits / budget (mean, %)
             unused   = mean % of the budget left unused (0 when over)
  violation  >1% over = share of cases more than 1 % over budget
             mean over = mean % over budget over all cases; p95 over = 95th percentile of % over
Paired differences (dPSNR_B and >1% over) vs k = 0 of the same learner and vs the feedback rule k = 0, 95 % cluster
bootstrap over source clips (a spliced GOP is its own cluster; reanalysis.cluster_of).

Detector lookahead (cut-triggered modes): the controller's 'frames seen' excludes the frames the scene detector reads
to decide whether a cut lies inside the window. To know whether a cut is within the next K frames, a causal detector
must have read min(K, frames left) frames ahead at every step, plus 2 more to reject flashes (features.detect_cuts
looks 1-2 frames past a candidate cut). So the encoding delay of cut-triggered lookahead with cap K is that number,
not 'frames seen'. Reported next to frames seen.

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork python experiments/quality_violations.py               # milestone
  RC_CAUSAL=1 RC_BUDGETS=26,30,34,38,42 RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_wide_causal \
      RC_REPORTS=results/x265_causal python experiments/quality_violations.py                           # D30 causal
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import breakdown as BD, reanalysis as RA  # noqa: E402
from rclib import config as C, metrics  # noqa: E402

FLASH = 2
GOP = C.GOP
# reference for the paired columns: the feedback rule (milestone, D30) or, in D44, the learning-free online controller
REF_RULE, REF_LAB = ("ctrl fixed:0", "controller k=0") if C.RESID else ("rule k=0", "feedback rule k=0")


def per_case(infos, items):
    out = {}
    for name, d in items.items():
        rec = []
        for (g, b), lst in d.items():
            cv, B = infos[g]["curve"], BD.case_budget(infos, g, b)
            bt = np.array([x for x, _ in lst], float)
            ps = np.array([p for _, p in lst], float)
            cb = np.asarray(cv["bits"], float)
            Bc = float(np.clip(B, cb.min(), cb.max()))   # reference inside the measured QP 18-50 curve (no extrapolation)
            rec.append((g, b, float(metrics.dpsnr_budget(ps, cv, Bc).mean()), float(ps.mean()),
                        float(np.mean(metrics.saving(bt, ps, cv))), float((bt / B).mean() * 100),
                        float(metrics.undershoot(bt, B).mean()), float((bt > 1.01 * B).mean()),
                        float(metrics.overshoot(bt, B).mean())))
        out[name] = pd.DataFrame(rec, columns=["gid", "b", "dpsnr", "psnr", "saving", "spend", "unused", "over1",
                                               "over"]).set_index(["gid", "b"]).sort_index()
    return out


def row(D, infos, name, refs):
    x = D[name]
    r = {"method": name, "cases": len(x), "dPSNR_B (dB)": x.dpsnr.mean(), "saving (%)": x.saving.mean(),
         "spend (%)": x.spend.mean(), "unused (%)": x.unused.mean(), ">1% over": f"{100 * x.over1.mean():.0f}%",
         "mean over (%)": x.over.mean(), "p95 over (%)": np.percentile(x.over, 95)}
    for lab, ref in refs:
        if ref is None or ref not in D or ref == name:
            r[f"dPSNR_B vs {lab}"] = r[f">1% over vs {lab} (pts)"] = ""
            continue
        j = x.index.intersection(D[ref].index)
        grp = [RA.cluster_of(infos[k[0]]) for k in j]
        r[f"dPSNR_B vs {lab}"] = RA.ci(RA.cboot(x.dpsnr[j].values - D[ref].dpsnr[j].values, grp)[:3])
        t = RA.cboot(100 * (x.over1[j].values - D[ref].over1[j].values), grp)
        r[f">1% over vs {lab} (pts)"] = f"{t[0]:+.0f} [{t[1]:+.0f}, {t[2]:+.0f}]"
    return r


def table(D, infos, names):
    rows = []
    for n in names:
        if n not in D:
            continue
        m = n.split()[0]
        k0 = f"{m} fixed:0" if " " in n and not n.startswith(("own", "hindsight", "constant", "best")) else None
        if n.startswith(("rule", "la_rule", "scene_rule")):
            k0 = None
        rows.append(row(D, infos, n, [("k=0 (same method)", k0), (REF_LAB, REF_RULE)]))
    return pd.DataFrame(rows).round(2).to_markdown(index=False) if rows else "(none)"


def detector_delay(K):
    """Mean over the frames of a GOP of the frames a causal detector must read ahead for a cap-K trigger."""
    return float(np.mean([min(K, GOP - 1 - t) + min(FLASH, max(0, GOP - 1 - t - K)) for t in range(GOP)])), \
        float(np.mean([min(K, GOP - 1 - t) for t in range(GOP)]))


def seen(items_rows, name):
    v = items_rows.get(name)
    return float(np.mean(v)) if v else float("nan")


def main():
    infos, test, items = BD.collect(C.WORK)
    D = per_case(infos, items)
    n_out = 0
    for g in test:
        for b in C.BUDGET_QPS:
            if b in infos[g]["static"]:
                cb, B = np.asarray(infos[g]["curve"]["bits"], float), BD.case_budget(infos, g, b)
                n_out += int(B < cb.min() or B > cb.max())
    # frames seen per learner (from eval rows; collect() keeps only bits/psnr)
    import glob
    import pickle
    fs = {}
    for p in sorted(glob.glob(os.path.join(C.WORK, "results_rl", "*", "eval.pkl"))):
        r = pickle.load(open(p, "rb"))
        a = r["args"]
        if a["method"] == "anyk" or a.get("drop") or a.get("prior") or a.get("tag") or a.get("extra"):
            continue
        for (mode, k, split), rows in r["res"].items():
            if split == "test":
                fs.setdefault(f"{a['method']} {mode}:{k}", []).extend(x["frames_seen"] for x in rows)
    setting = ("D44 setting: budget = a fixed bitrate ladder (train median constant-QP bits at each budget QP, the "
               "same for every GOP); action = residual on the causal online controller, which sees frame 0 and the "
               "visible frames only; scene flags from visible frames only; 'STATIC' = the controller's plan with the "
               "whole GOP visible (the search's start, not causal)" if C.LADDER else
               "D30 causal setting: budget = s x the GOP's own constant-QP bits at QP b, s in {0.85, 1, 1.18} hidden; "
               "base QP from a first-pass rate model; scene flags from visible frames only"
               if C.CAUSAL else
               "milestone setting: budget = the GOP's own constant-QP bits at QP b (reveals the GOP's cost); base QP = "
               "the QP that meets it; scene flags from the whole GOP")
    L = [f"# Quality and budget violations, reported separately ({C.CODEC}, test)", "",
         f"Setting: {setting}. Budget QPs {list(C.BUDGET_QPS)}; {len(test)} test GOPs. Cases whose budget lies outside "
         f"the constant-QP curve (QP 18-50; reference clamped to the curve's end): {n_out}.", "",
         "dPSNR_B = PSNR minus the PSNR of constant QP at exactly the budget (dB, no penalty). saving = % bits saved vs "
         "constant QP at equal PSNR. spend = bits / budget. >1% over = share of cases more than 1 % over budget; mean "
         "and p95 over = % over budget across all cases (0 when within). Paired columns: 95 % cluster bootstrap over "
         "source clips, seeds averaged per case.", ""]
    meth = [f"{m} fixed:{k}" for m in ("ctrl", "bc", "cql", "iql", "bc_ppo", "cql_ppo", "ppo", "a2c", "dqn", "lagr", "pid",
                                       "mpc", "bc_fb2") for k in (0, 5, 10)]
    ref = ["constant QP", "best constant QP (hindsight)", "STATIC", "rule k=0", "la_rule k=0", "la_rule k=5",
           "hindsight search"] + sorted(k for k in D if k.startswith("own"))
    L += ["## Reference points and the encoders' own rate control (same per-GOP budget)", "", table(D, infos, ref), "",
          "## Learners", "", table(D, infos, meth), "",
          "## Lookahead curve (CQL->PPO)", "",
          table(D, infos, [f"cql_ppo fixed:{k}" for k in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 29)]), ""]
    dyn = sorted(k for k in D if k.startswith(("cql_ppo ", "lagr ", "pid ")) and " fixed" not in k and len(k.split()) == 2)
    if dyn:
        L += ["## Dynamic lookahead with the detector's own scan counted", "",
              "frames seen = future frames the controller's features cover (the milestone's Table 2 number). detector "
              "reads = future frames a causal scene detector must have read at every step to raise or rule out the "
              "flag for a cap-K window (K, or fewer near the end of the GOP), with +2 for flash rejection in brackets. "
              "That is the encoding delay of the mode; for fixed k it equals frames seen.", ""]
        rows = []
        for n in ["ctrl fixed:0", "ctrl fixed:5", "cql_ppo fixed:0", "cql_ppo fixed:5", "cql_ppo fixed:10"] + dyn + sorted(
                k for k in D if k.startswith("ctrl ") and not k.startswith("ctrl fixed")):
            if n not in D:
                continue
            mode, K = n.split()[1].split(":")
            K = int(K)
            d2, d0 = detector_delay(K)
            r = row(D, infos, n, [("k=0", f"{n.split()[0]} fixed:0")])
            sn = seen(fs, n)
            dl = (f"{sn:.1f}" if mode == "fixed" else f"{d0:.1f} ({d2:.1f})")
            rows.append({"method": n, "frames seen": round(sn, 2), "delay incl. detector (frames)": dl,
                         "dPSNR_B (dB)": r["dPSNR_B (dB)"], "saving (%)": r["saving (%)"], ">1% over": r[">1% over"],
                         "dPSNR_B vs k=0": r["dPSNR_B vs k=0"]})
        L += [pd.DataFrame(rows).round(2).to_markdown(index=False), "",
              "Flags in this work dir: " + ("visible frames only (causal)." if C.CAUSAL else
                                            "computed on the whole GOP, so these runs also had the detector look up to "
                                            "29 frames ahead; a causal rerun is needed for the score."), ""]
    out = os.path.join(C.REPORTS, "quality_violations.md")
    os.makedirs(C.REPORTS, exist_ok=True)
    open(out, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
