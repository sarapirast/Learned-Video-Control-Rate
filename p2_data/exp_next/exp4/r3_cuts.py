"""Exp 4 R3 cut-GOP breakdown (no encodes; descriptive, not a gate). Val, k5, hole excluded, seeds averaged.

For cut/gradual GOPs: R3 - final4 (and R2 - final4) by the position of the first cut after frame 0 (early 1-9 /
mid 10-19 / late 20-29); R3's QP offset vs final4 (QP - final4's QP, includes mean[t]) by frame relative to the cut
(-3..+3) vs the same frames of stable GOPs; A / E-P split for cut vs stable.

  python -I exp_next/exp4/r3_cuts.py [--encs x264]
Out: results_v1/next/exp4/r3_cuts_<encs>.md
"""
import argparse
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp5")
from rclib import metrics  # noqa: E402
from shift_report import boot, fmt  # noqa: E402

RC = "/scratch1/aayushso/rcwork_v1"
OUT = "/scratch1/aayushso/ee599/results_v1/next/exp4"
RUNS = {"R3": "res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s{s}",
        "R2": "res_k5_fixed_f4_lam0.17_st180k_r6_s{s}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encs", default="x264,x265")
    a = ap.parse_args()
    encs = a.encs.split(",")
    rows, offs = [], []
    for enc in encs:
        inf = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
        for m, tmpl in RUNS.items():
            for s in (0, 1, 2):
                for r in pickle.load(open(f"{RC}/{enc}_resh/results_rl/{tmpl.format(s=s)}/eval.pkl", "rb"))["res"][("fixed", 5, "val")]:
                    g, b = r["gid"], r["budget"]
                    cv, B, c = inf[g]["curve"], inf[g]["budget"][b], inf[g]["ctrl"][(b, 5)]
                    if B > max(cv["bits"]):
                        continue
                    cut = np.flatnonzero(np.asarray(inf[g]["an"]["cut"])[1:]) + 1
                    lab = inf[g]["gop"]["label"]
                    c0 = int(cut[0]) if len(cut) else -1
                    pos = "stable" if lab == "stable" else ("no detected cut" if c0 < 0 else
                                                           "early 1-9" if c0 < 10 else "mid 10-19" if c0 < 20 else "late 20-29")
                    p4 = c["dpsnr"] + metrics.psnr_at_bits(cv, B)
                    rows.append({"enc": enc, "m": m, "seed": s, "gid": g, "clip": inf[g]["gop"]["clip"], "level": b,
                                 "label": lab, "pos": pos, "d": r["score"] - r["static_score"],
                                 "dA": float(r["psnr"] - metrics.psnr_at_bits(cv, r["bits"]))
                                 - float(p4 - metrics.psnr_at_bits(cv, c["bits"]))})
                    if m == "R3":
                        o = np.array(r["qps"]) - np.array(r["ctrl_qps"])
                        if c0 > 0:
                            for rel in range(-3, 4):
                                if 0 <= c0 + rel < 30:
                                    offs.append({"enc": enc, "kind": "cut", "rel": rel, "off": o[c0 + rel]})
                        elif lab == "stable":
                            offs += [{"enc": enc, "kind": "stable", "rel": t, "off": o[t]} for t in range(30)]
    d = pd.DataFrame(rows)
    p = d.groupby(["enc", "m", "gid", "clip", "level", "label", "pos"])[["d", "dA"]].mean().reset_index()
    L = [f"# Exp 4 R3: cut-GOP breakdown, val k5 ({', '.join(encs)}; exp_next/exp4/r3_cuts.py)", "",
         "Descriptive, not a gate. vs final4, seeds averaged, hole excluded; dA = change in quality for the bits "
         "(A) vs final4; position = first detected cut after frame 0 (label cut/gradual).", "",
         "| enc | method | GOP group | n | vs final4 | dA |", "|---|---|---|---|---|---|"]
    for (e, m, pos), x in p.groupby(["enc", "m", "pos"]):
        L.append(f"| {e} | {m} | {pos} | {len(x)} | {fmt(boot(x.d, x['clip']))} | {x.dA.mean():+.3f} |")
    o = pd.DataFrame(offs)
    if len(o):
        cutp = o[o.kind == "cut"].groupby(["enc", "rel"]).off.mean().unstack("rel")
        st = o[o.kind == "stable"].groupby("enc").off.mean()
        L += ["", "R3 mean QP offset vs final4 by frame relative to the first cut (0 = cut frame; includes mean[t]); "
              "stable GOPs' mean offset for reference:", "", cutp.round(2).to_markdown(), "",
              "stable GOPs, all frames: " + "; ".join(f"{e} {v:+.2f}" for e, v in st.items()), ""]
    dest = f"{OUT}/r3_cuts_{'_'.join(encs)}.md"
    open(dest, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
