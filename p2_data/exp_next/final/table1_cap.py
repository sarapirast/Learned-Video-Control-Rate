"""Table I of the final report (per-GOP test score by lookahead k) with the 100 dB per-plane PSNR cap.

Pavneet's report Table I takes its numbers from results_v1/w5/w5_numbers.md and abr_dpsnr.md (11-11): uncapped curves
and final4 PSNR, hole episodes included. This rescores the same rows with the cap (Ahhana's correction, 11-16, as in
results_v1/final/report_test_cap.md). No encodes.

score = PSNR - curve_PSNR(B) - 0.17 x %over, so with the cap:
  every method:  + [curve_uncapped(B) - curve_capped(B)]       (curves: results_v1/final/cap_fix_<enc>.pkl)
  final4 only:   + [psnr_capped - psnr_uncapped] of the episode (final4 rows re-encoded in cap_fix, bits identical)
The learners (rclib) and the search already scored capped episode PSNR. ABR+VBV episode PSNR is not re-measured
(no per-plane MSE stored), as in report_test_cap.md.
R3 (added 11-20, Pavneet's request): the final test pass rows (results_v1/final/r3_test_<enc>.pkl, 180k model, seeds
3-5 averaged per episode), k5 only (the only k R3 was run at on v1 test), scored by report.py's Scorer on the same
GOP x level rows.
Checks: uncapped + hole included reproduces w5_numbers / abr_dpsnr exactly; capped + hole excluded reproduces
final4's k-row of report_test_cap.md and the primary R3 - final4 at k5 (+0.067 / +0.163).

  python -I exp_next/final/table1_cap.py
Out: results_v1/final/table1_cap.md (+ .csv of the per-row deltas)
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import metrics  # noqa: E402

sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/final")
import report as REP  # noqa: E402  (Scorer / load_r3 of the final test pass)

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
OUT = f"{ROOT}/results_v1/final"
KS = (0, 2, 5, 10, 29)
METHODS = {"search": "Search (ceiling)", "final4": "Controller (final4)", "bc@prev": "BC (causal base)",
           "cql_ppo@prev": "CQL->PPO", "abr_vbv": "ABR+VBV"}
W5 = {"x264": {"final4": [-0.349, -0.164, -0.129, -0.119, -0.126], "bc@prev": [-1.493, -0.855, -0.563, -0.413, -0.205],
               "cql_ppo@prev": [-1.273, -0.764, -0.583, -0.425, -0.375], "search": [0.296] * 5},
      "x265": {"bc@prev": [-1.367, -0.882, -0.604, -0.397, -0.213], "cql_ppo@prev": [-1.117, -0.785, -0.535, -0.428, -0.409],
               "search": [0.281] * 5}}
LAB = {**METHODS, "r3_180k": "R3 (180k, seeds 3-5)"}
PRIMARY = {"x264": 0.067, "x265": 0.163}   # report_test_cap.md: R3 - final4 at k5, capped, hole excluded
CAPREP = {"x264": [-0.31, -0.143, -0.107, -0.097, -0.108], "x265": [-0.397, -0.26, -0.185, -0.174, -0.227]}  # report_test_cap.md final4 by k (hole excluded, capped)


def r3_k5(enc, d, cap):
    """R3 180k test rows at k5, seeds averaged per (gid, level), on Table I's GOP x level rows."""
    S = REP.Scorer(enc, cap=cap)
    r = pd.DataFrame(REP.load_r3(enc, "test", S)).query("method == 'R3 180k'")
    r = r.groupby(["gid", "level"]).agg(score=("score", "mean"), hole=("hole", "first"), ns=("seed", "nunique")).reset_index()
    assert (r.ns == 3).all()
    key = d.loc[d.k == 5, ["gid", "budget"]].rename(columns={"budget": "level"}).astype({"level": int})
    m = key.merge(r, on=["gid", "level"], how="left", validate="1:1")
    assert m.score.notna().all() and len(m) == len(r), (enc, len(m), len(r))
    return m


def table(enc):
    inf = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
    fix = pickle.load(open(f"{OUT}/cap_fix_{enc}.pkl", "rb"))
    w = pd.read_csv(f"{ROOT}/results_v1/w3/class_kcurves_{enc}.csv").query("split == 'test'")
    a = pd.read_csv(f"{ROOT}/results_v1/w5/abr_dpsnr.csv").query("codec == @enc")[["gid", "budget", "k", "abr_vbv"]]
    d = w.merge(a, on=["gid", "budget", "k"], how="left")
    dc, hole = [], []
    for g, lv in zip(d.gid, d.budget):
        cv, B = inf[g]["curve"], inf[g]["budget"][int(lv)]
        hole.append(B > max(cv["bits"]))
        if g in fix["curves"]:
            dc.append(float(metrics.psnr_at_bits(cv, B) - metrics.psnr_at_bits({**cv, "psnr": fix["curves"][g]}, B)))
        else:
            dc.append(0.0)
    d["d_curve"], d["hole"] = dc, hole
    d["d_f4"] = [(lambda f: 0.0 if f is None else f["psnr"] - f["psnr_uncapped"])(fix["final4"].get((g, int(lv), int(k))))
                 for g, lv, k in zip(d.gid, d.budget, d.k)]
    rows = []
    for m in METHODS:
        x = d.dropna(subset=[m])
        cap = x[m] + x.d_curve + (x.d_f4 if m == "final4" else 0.0)
        for k in KS:
            j = (x.k == k).to_numpy()
            nh = j & ~x.hole.to_numpy()
            rows.append({"enc": enc, "method": m, "k": k, "n": int(j.sum()), "uncap_hole_incl": x[m][j].mean(),
                         "cap_hole_incl": cap[j].mean(), "max_abs_row_change": float((cap - x[m])[j].abs().max()),
                         "cap_hole_excl": cap[nh].mean(), "n_hole_excl": int(nh.sum())})
    ru, rc = r3_k5(enc, d, False), r3_k5(enc, d, True)
    nh = ~rc.hole.to_numpy(bool)
    rows.append({"enc": enc, "method": "r3_180k", "k": 5, "n": len(rc), "uncap_hole_incl": ru.score.mean(),
                 "cap_hole_incl": rc.score.mean(), "max_abs_row_change": float((rc.score - ru.score).abs().max()),
                 "cap_hole_excl": rc.score[nh].mean(), "n_hole_excl": int(nh.sum())})
    t = pd.DataFrame(rows)
    for m, v in W5.get(enc, {}).items():   # reproduce the 11-11 numbers
        got = t.query("method == @m").uncap_hole_incl.round(3).tolist()
        assert np.allclose(got, v, atol=6e-4), (enc, m, got, v)
    if enc in CAPREP:
        got = t.query("method == 'final4'").cap_hole_excl.tolist()
        assert np.allclose(got, CAPREP[enc], atol=6e-3), (enc, got, CAPREP[enc])
    ex = t.set_index(["method", "k"]).cap_hole_excl
    assert abs(ex[("r3_180k", 5)] - ex[("final4", 5)] - PRIMARY[enc]) < 6e-4, (enc, ex[("r3_180k", 5)] - ex[("final4", 5)])
    return t, d


def main():
    L = ["# Table I with the 100 dB PSNR cap (exp_next/final/table1_cap.py)", "",
         "Per-GOP v1 test score (dB) by lookahead k, the rows of results_v1/w5/w5_numbers.md and abr_dpsnr.md (11-11, "
         "uncapped) rescored with the 100 dB per-plane PSNR cap. Same rows, same convention as the 11-11 table "
         "(hole episodes included, flat GOPs excluded, learners 3 seeds averaged). R3 added 11-20 (k5 only). No encodes. ABR+VBV: curve "
         "corrected, episode PSNR not re-measured (as report_test_cap.md).", ""]
    allt, alld = [], []
    for enc in ("x264", "x265"):
        t, d = table(enc)
        allt.append(t)
        alld.append(d.assign(enc=enc))
        L += [f"## {enc}", "", "Capped, hole included (Table I convention):", "",
              "| method | " + " | ".join(f"k{k}" for k in KS) + " |", "|---|" + "---:|" * len(KS)]
        for m, lab in LAB.items():
            v = t.query("method == @m").set_index("k")
            L.append(f"| {lab} | " + " | ".join(f"{v.cap_hole_incl[k]:+.3f}" if k in v.index else "-" for k in KS) + " |")
        L += ["", "Change vs the 11-11 (uncapped) numbers, capped - uncapped (mean; max |row change|):", "",
              "| method | " + " | ".join(f"k{k}" for k in KS) + " |", "|---|" + "---:|" * len(KS)]
        for m, lab in LAB.items():
            v = t.query("method == @m").set_index("k")
            L.append(f"| {lab} | " + " | ".join(f"{v.cap_hole_incl[k] - v.uncap_hole_incl[k]:+.4f} ({v.max_abs_row_change[k]:.2f})"
                                               if k in v.index else "-" for k in KS) + " |")
        L += ["", "Capped, hole excluded (the convention of report_test_cap.md and the R3 tables; for reference):", "",
              "| method | " + " | ".join(f"k{k}" for k in KS) + " |", "|---|" + "---:|" * len(KS)]
        for m, lab in LAB.items():
            v = t.query("method == @m").set_index("k")
            L.append(f"| {lab} | " + " | ".join(f"{v.cap_hole_excl[k]:+.3f}" if k in v.index else "-" for k in KS) + " |")
        a = t.query("method == 'abr_vbv'")
        s_abr = (a.cap_hole_incl.min() + a.cap_hole_incl.max()) / 2
        s_se = t.query("method == 'search'").cap_hole_incl.mean()
        L += ["", f"Share of the search's gain over ABR+VBV, (S - S_ABR) / (S_search - S_ABR), capped, hole included, "
              f"S_ABR = middle of its capped range ({a.cap_hole_incl.min():+.3f} to {a.cap_hole_incl.max():+.3f} -> "
              f"{s_abr:+.3f}); %:", "", "| method | " + " | ".join(f"k{k}" for k in KS) + " |", "|---|" + "---:|" * len(KS)]
        for m in ("final4", "bc@prev", "cql_ppo@prev", "r3_180k"):
            v = t.query("method == @m").set_index("k")
            L.append(f"| {LAB[m]} | " + " | ".join(f"{100 * (v.cap_hole_incl[k] - s_abr) / (s_se - s_abr):.0f}" if k in v.index else "-"
                                                for k in KS) + " |")
        r3 = t.query("method == 'r3_180k'").iloc[0]
        L += ["", f"R3 at k5 (180k, seeds 3-5 averaged, final test pass rows): capped, hole included {r3.cap_hole_incl:+.3f} dB "
              f"-> share {100 * (r3.cap_hole_incl - s_abr) / (s_se - s_abr):.1f} % (S_search {s_se:+.3f}, S_ABR {s_abr:+.3f}); "
              f"capped, hole excluded {r3.cap_hole_excl:+.3f}. R3 was run on v1 test at k5 only."]
        L += ["", f"Rows per cell: {int(t.n.max())} (GOP x level, hole included), {int(t.n_hole_excl.max())} hole excluded; "
              f"GOPs with a changed curve in these rows: {int(d.loc[d.d_curve != 0, 'gid'].nunique())}.", ""]
    L += ["Checks passed: uncapped + hole included reproduces w5_numbers.md (search, BC, CQL->PPO; final4 x264) to "
          "3 decimals; capped + hole excluded reproduces final4's k-row of report_test_cap.md (both encoders) and the "
          "primary R3 - final4 at k5 (x264 +0.067, x265 +0.163). R3 rows: results_v1/final/r3_test_<enc>.pkl, scored "
          "by exp_next/final/report.py's Scorer (added 11-20)."]
    pd.concat(allt).to_csv(f"{OUT}/table1_cap.csv", index=False)
    open(f"{OUT}/table1_cap.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
