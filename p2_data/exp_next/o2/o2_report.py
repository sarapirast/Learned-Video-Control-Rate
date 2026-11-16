"""o[2] ablation report (eval only). Masked (o[2] = 0) vs the stored val rows of the same policies; paired on
(GOP, level, k), seeds averaged per episode, 95% clip bootstrap, level-24-hole episodes excluded (also by level,
since o[2] only separates level 24 from the rest).

  python -I exp_next/o2/o2_report.py
In: results_v1/next/o2/o2_<group>_<enc>.pkl (o2_eval.py) + stored eval.pkl. Out: results_v1/next/o2/o2_report.md
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp5")
from shift_report import boot, fmt  # noqa: E402

RC = "/scratch1/aayushso/rcwork_v1"
OUT = "/scratch1/aayushso/ee599/results_v1/next/o2"
SUB = {"R2": "resh", "R1": "resh", "L540": "lfqp"}
TMPL = {"R2": "res_k{k}_fixed_f4_lam0.17_st180k_r6_s{s}", "R1": "res_k{k}_fixed_lam0.17_st180k_s{s}",
        "L540": "cql_ppo_k{k}_fixed_st540k_s{s}"}


def main():
    rows = []
    curves = {}
    for f in sorted(glob.glob(f"{OUT}/o2_*_*.pkl")):
        parts = os.path.basename(f)[3:-4].split("_")
        if parts[0] == "level0":
            continue
        grp, enc, arm = parts[0], parts[1], (parts[2] if len(parts) > 2 else "zero")
        if enc not in curves:
            inf = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
            curves[enc] = {g: (x["curve"], x["budget"], x["gop"]["clip"]) for g, x in inf.items()}
        for (k, s), masked in pickle.load(open(f, "rb")).items():
            ev = pickle.load(open(f"{RC}/{enc}_{SUB[grp]}/results_rl/{TMPL[grp].format(k=k, s=s)}/eval.pkl", "rb"))
            st = {(r["gid"], r["budget"]): r for r in ev["res"][("fixed", k, "val")]}
            for r in masked:
                o = st[(r["gid"], r["budget"])]
                cv, B, clip = curves[enc][r["gid"]][0], curves[enc][r["gid"]][1][r["budget"]], curves[enc][r["gid"]][2]
                rows.append({"group": grp, "arm": arm, "enc": enc, "k": k, "seed": s, "gid": r["gid"], "clip": clip,
                             "level": r["budget"], "hole": B > max(cv["bits"]), "masked": r["score"],
                             "stored": o["score"], "use_m": r["bits"] / B, "use_s": o["bits"] / B,
                             "same_qps": list(r["qps"]) == list(o["qps"])})
    d = pd.DataFrame(rows)
    key = ["group", "arm", "enc", "k", "gid", "clip", "level", "hole"]
    p = d.groupby(key)[["masked", "stored", "use_m", "use_s", "same_qps"]].mean().reset_index()
    y = p[~p.hole]
    L = ["# o[2] ablation, eval only (exp_next/o2/o2_report.py)", "",
         "o[2] = (budget level != 24): clip-level hindsight under clip-mean budgets. Masked = the same trained policy "
         "re-run on val with o[2] = 0 (unmasked re-run reproduced the stored rows 8/8 per group and encoder). "
         "Masked - stored, paired, seeds averaged, 95% clip bootstrap ('*' excludes 0), hole excluded. A drop means "
         "the policy uses o[2] at evaluation; it cannot show whether having o[2] in training changed what was learned "
         "(e.g. the critic's values) -- BC / R3 trained without o[2] answer that. Single cells with a CI just touching 0 "
         "are not read (3 groups x 2 arms x several breakdowns).", "",
         "Arms: zero = o[2] forced to 0 (tells the policy every GOP is level 24: measures reliance on the bit, not what "
         "a deployed policy sees); standin = o[2] = 1 if final4's frame-0 planning QP >= 27 else 0 (causal; agrees "
         "with the true bit on 88% of val episodes). Reading: zero drops and standin recovers most -> the bit can be "
         "approximated causally, a caveat suffices; both drop -> earlier learner numbers overstate a causal policy; "
         "zero unchanged -> no issue.", "",
         "| group | arm | enc | k | n | arm - stored | L24 | L30 | L36 | L42 | use masked / stored | episodes with identical QPs |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (g, arm, e, k), x in y.groupby(["group", "arm", "enc", "k"]):
        dd = x.masked - x.stored
        L.append(f"| {g} | {arm} | {e} | {k} | {len(x)} | {fmt(boot(dd, x['clip']))} | " +
                 " | ".join(f"{dd[x.level == lv].mean():+.3f}" for lv in (24, 30, 36, 42)) +
                 f" | {x.use_m.mean():.3f} / {x.use_s.mean():.3f} | {100 * (x.same_qps == 1).mean():.0f}% |")
    L += ["", "Pooled over k and encoders: " + "; ".join(
        f"{g} {arm} {fmt(boot(x.masked - x.stored, x['clip']))}" for (g, arm), x in y.groupby(["group", "arm"])), ""]
    open(f"{OUT}/o2_report.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
