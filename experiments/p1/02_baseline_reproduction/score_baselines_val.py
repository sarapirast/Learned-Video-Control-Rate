"""Score + check the val baselines (x264 re-run on the shim; x264 CQP / ABR and all x265 from stored rows).

Scoring = exp_next/final/report.py: rclib metrics.score (dPSNR_B - 0.17 x %over) on rcwork_v1/<enc>_resh infos.pkl
curves and budgets, level-24-hole episodes excluded in the primary, R3 seeds averaged per episode, paired against
final4 at the same k on (gid, level). CIs: rclib metrics.paired_ci (normal, episodes independent) and the team's
95 % clip bootstrap (exp5/shift_report.boot: 2000 resamples of clips; here re-seeded per comparison, so CI ends can
differ from the team's reports in the last digits; point estimates must match exactly).
--psnr-cap: one PSNR convention everywhere, as report.py --psnr-cap: Aayush's cap_fix_<enc>.pkl gives 100 dB-capped
constant-QP curves (all methods) and re-measured capped PSNR for the stored final4 rows; the x264 re-run and all
learner rows are already capped (rclib); ABR rows stay uncapped, as in the team's capped report. Checked against
results_v1/final/report_val_cap.md instead of report_val.md.
Run with Aayush's ee599 env (pyarrow):  python -I score_baselines_val.py [--psnr-cap]
  -> summary.md, rows_scored.parquet   (--psnr-cap: summary_cap.md, rows_scored_cap.parquet)
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/pavneet_pipeline")
from rclib import metrics  # noqa: E402

assert metrics.METRIC == "dpsnr"
HERE = "/scratch1/ahhanagu/ee599/results/baselines_val"
ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
R3RUN = "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s{s}"
ABR_M = {"x264": 0.90, "x265": 0.93}
KS = (0, 2, 5, 10, 29)
LEVELS = (24, 30, 36, 42)

# numbers as printed in the team's reports (hole excluded), for the check column
REP = {  # results_v1/final/report_val.md
    ("x264", "final4"): dict(zip(KS, (-0.357, -0.148, -0.113, -0.121, -0.140))),
    ("x265", "final4"): dict(zip(KS, (-0.472, -0.265, -0.256, -0.248, -0.237))),
    ("x264", "ABR m0.90"): {0: -1.525, 5: -1.260}, ("x265", "ABR m0.93"): {0: -1.401, 5: -1.017},
    ("x264", "R3 180k"): {5: -0.045}, ("x265", "R3 180k"): {5: -0.052},
}
REP_CAP = {  # results_v1/final/report_val_cap.md (same quantities, one PSNR cap everywhere)
    ("x264", "final4"): dict(zip(KS, (-0.358, -0.148, -0.115, -0.119, -0.142))),
    ("x265", "final4"): dict(zip(KS, (-0.470, -0.262, -0.254, -0.243, -0.237))),
    ("x264", "ABR m0.90"): {0: -1.518, 5: -1.253}, ("x265", "ABR m0.93"): {0: -1.395, 5: -1.010},
    ("x264", "R3 180k"): {5: -0.038}, ("x265", "R3 180k"): {5: -0.045},
}
REP_DIFF_CAP = {
    "x264": {"all": 0.077, "s3": 0.062, "s4": 0.071, "s5": 0.098, "stable": 0.078, "cut/gradual": 0.069},
    "x265": {"all": 0.209, "s3": 0.183, "s4": 0.212, "s5": 0.232, "stable": 0.224, "cut/gradual": 0.126},
}
CAP = "--psnr-cap" in sys.argv
if CAP:
    REP = REP_CAP
REP_DIFF = {  # R3 180k - final4 at k5: all, per seed, by class
    "x264": {"all": 0.068, "s3": 0.054, "s4": 0.063, "s5": 0.089, "stable": 0.078, "cut/gradual": 0.016},
    "x265": {"all": 0.204, "s3": 0.178, "s4": 0.207, "s5": 0.227, "stable": 0.224, "cut/gradual": 0.094},
}


def boot(d, clips, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([d[np.concatenate([idx[c] for c in rng.choice(u, len(u))])].mean() for _ in range(n)])
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def fmt(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" + (" *" if t[1] > 0 or t[2] < 0 else "")


class Scorer:
    def __init__(self, enc):
        self.inf = pickle.load(open(f"{RC}/{enc}_resh/results_infos/infos.pkl", "rb"))
        # --psnr-cap: Aayush's fix (exp_next/final/cap_fix.py): capped curves per GOP, capped final4 PSNR per episode
        self.fix = (pickle.load(open(f"{ROOT}/results_v1/final/cap_fix_{enc}.pkl", "rb")) if CAP
                    else {"curves": {}, "final4": {}})

    def curve(self, gid):            # = report.py Scorer.curve
        cv = self.inf[gid]["curve"]
        if gid in self.fix["curves"]:
            assert len(cv["psnr"]) == len(self.fix["curves"][gid])
            return {**cv, "psnr": self.fix["curves"][gid]}
        return cv

    def f4_psnr(self, gid, level, k, psnr):   # = report.py Scorer.f4_psnr (stored final4 rows only)
        f = self.fix["final4"].get((gid, int(level), int(k)))
        return psnr if f is None else f["psnr"]

    def row(self, enc, method, source, gid, level, k, bits, psnr, seed=-1):
        x = self.inf[gid]
        cv, B = self.curve(gid), x["budget"][level]
        return {"enc": enc, "method": method, "source": source, "gid": gid, "clip": x["gop"]["clip"],
                "level": int(level), "k": int(k), "seed": seed, "bits": float(bits), "psnr": float(psnr),
                "score": float(metrics.score(bits, psnr, cv, B)), "hole": bool(B > max(cv["bits"])),
                "cls": "cut/gradual" if x["gop"]["label"] in ("cut", "gradual") else "stable"}


def stored_final4(enc, S):
    d = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{ROOT}/results_v1/controller_real/final4_{enc}_val_*.parquet"))
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    d = d[d.gid.isin(S.inf)]
    return [S.row(enc, "final4", "stored", r.gid, r.level_q0, r.k, r.bits, S.f4_psnr(r.gid, r.level_q0, r.k, r.psnr_yuv))
            for r in d.itertuples()]


def stored_r3(enc, S):
    rows = []
    for s in (3, 4, 5):
        d = f"{RC}/{enc}_resh/results_rl/{R3RUN.format(s=s)}"
        for r in pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"][(180993, "fixed", 5, "val")]:
            row = S.row(enc, "R3 180k", "stored", r["gid"], r["budget"], 5, r["bits"], r["psnr"], s)
            row["qps"] = list(r["qps"])
            rows.append(row)
    return rows


def stored_abr(enc, S):
    fs = [f for f in glob.glob(f"{ROOT}/results_v1/next/exp10/rows_{enc}_val_*.parquet") if "_limit" not in f]
    d = pd.concat(pd.read_parquet(f) for f in fs)
    d = d[np.isclose(d.margin, ABR_M[enc])]
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    d = d[d.gid.isin(S.inf)]
    return [S.row(enc, f"ABR m{ABR_M[enc]:.2f}", "stored", r.gid, r.level_q0, r.k, r.bits, r.psnr_yuv) for r in d.itertuples()]


def stored_cqp(enc, S):
    d = pd.read_parquet(f"{ROOT}/results_v1/baselines_v1.parquet")
    d = d[(d.encoder == enc) & (d.split == "val") & d.method.isin(["cqp_est", "cqp_best"])].copy()
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    d = d[d.gid.isin(S.inf)]
    name = {"cqp_est": "CQP (causal estimate)", "cqp_best": "CQP best (hindsight)"}
    return [S.row(enc, name[r.method], "stored", r.gid, r.level_q0, r.k, r.bits, r.psnr_yuv) for r in d.itertuples()]


def rerun_x264(S):
    rows, checks = [], []
    for k in KS:
        rr = pickle.load(open(f"{HERE}/rows_final4_k{k}.pkl", "rb"))["rows"]
        same_b = same_s = 0
        for r in rr:
            row = S.row("x264", "final4", "re-run (shim)", r["gid"], r["budget"], k, r["bits"], r["psnr"])
            c = S.inf[r["gid"]]["ctrl"][(r["budget"], k)]
            same_b += int(r["bits"] == c["bits"])
            same_s += int(abs(row["score"] - c["score"]) < 1e-9 and abs(row["score"] - r["score"]) < 1e-9)
            # (with --psnr-cap the stored ctrl scores use the uncapped curves, so 'score' only matches off the fixed GOPs)
            rows.append(row)
        checks.append(("final4", f"k{k}", len(rr), f"total bits {same_b}/{len(rr)}, score {same_s}/{len(rr)}",
                       "info['ctrl'] (final4's own CLI run)"))
    st = {(r["gid"], r["level"], r["seed"]): r for r in stored_r3("x264", S)}
    for s in (3, 4, 5):
        rr = pickle.load(open(f"{HERE}/rows_r3_s{s}.pkl", "rb"))["rows"]
        sq = sb = ss = 0
        for r in rr:
            row = S.row("x264", "R3 180k", "re-run (shim)", r["gid"], r["budget"], 5, r["bits"], r["psnr"], s)
            o = st[(r["gid"], r["budget"], s)]
            sq += int(list(r["qps"]) == o["qps"])
            sb += int(r["bits"] == o["bits"])
            ss += int(abs(row["score"] - o["score"]) < 1e-9 or r["gid"] in S.fix["curves"])   # stored = old curves
            rows.append(row)
        checks.append(("R3 180k", f"seed {s}", len(rr), f"QPs {sq}/{len(rr)}, total bits {sb}/{len(rr)}, "
                       f"score {ss}/{len(rr)}", "eval_ckpt.pkl (180993, val)"))
    return rows, checks


def compare(d, enc):
    """Rows of the summary table: each method x k vs final4 at the same k, hole excluded."""
    d = d[(d.enc == enc) & ~d.hole]
    f4 = d[d.method == "final4"].set_index(["gid", "level", "k"]).score
    out = []
    for (m, src), g in d.groupby(["method", "source"], sort=False):
        for k, gk in g.groupby("k"):
            ep = gk.groupby(["gid", "level", "k", "clip", "cls"]).score.mean().reset_index()   # seeds averaged
            key = pd.MultiIndex.from_frame(ep[["gid", "level", "k"]])
            have = key.isin(f4.index)
            ep, key = ep[have], key[have]
            base = f4.loc[key].to_numpy()
            diff = ep.score.to_numpy() - base
            r = {"enc": enc, "method": m, "source": src, "k": k, "n": len(ep), "score": ep.score.mean()}
            if m != "final4":
                mu, hw = metrics.paired_ci(ep.score, base)
                r["d_ci"] = f"{mu:+.3f} ± {hw:.3f}"
                r["d_boot"] = fmt(boot(diff, ep["clip"].to_numpy()))
                for c in ("stable", "cut/gradual"):
                    msk = (ep.cls == c).to_numpy()
                    r[f"d_{c}"] = fmt(boot(diff[msk], ep["clip"].to_numpy()[msk])) + f" (n {msk.sum()})"
            else:
                r["d_ci"] = r["d_boot"] = r["d_stable"] = r["d_cut/gradual"] = "(reference)"
            rep = REP.get((enc, m), {}).get(k)
            r["reported"] = rep
            r["check"] = "" if rep is None else ("match" if round(r["score"], 3) == round(rep, 3) else "MISMATCH")
            out.append(r)
    return out


def r3_diff_checks(d, enc):
    d = d[(d.enc == enc) & ~d.hole & (d.k == 5)]
    f4 = d[d.method == "final4"].set_index(["gid", "level"]).score
    r3 = d[d.method == "R3 180k"]
    out = []
    for lab, sub in [("all", r3)] + [(f"s{s}", r3[r3.seed == s]) for s in (3, 4, 5)] + \
            [(c, r3[r3.cls == c]) for c in ("stable", "cut/gradual")]:
        ep = sub.groupby(["gid", "level"]).score.mean()
        v = (ep - f4.loc[ep.index]).mean()
        rep = (REP_DIFF_CAP if CAP else REP_DIFF)[enc][lab]
        out.append((enc, f"R3 - final4 k5, {lab}", f"{v:+.3f}", f"{rep:+.3f}",
                    "match" if round(v, 3) == round(rep, 3) else "MISMATCH"))
    return out


def main():
    rows, checks, dchecks, table = [], [], [], []
    for enc in ("x264", "x265"):
        S = Scorer(enc)
        if enc == "x264":
            rr, checks = rerun_x264(S)
            rows += rr
        else:
            rows += stored_final4(enc, S) + [{k: v for k, v in r.items() if k != "qps"} for r in stored_r3(enc, S)]
        rows += stored_cqp(enc, S) + stored_abr(enc, S)
        if enc == "x264":   # stored final4 rows too, to check the re-run against them episode by episode
            f4s = pd.DataFrame(stored_final4(enc, S)).set_index(["gid", "level", "k"])
            mine = pd.DataFrame([r for r in rows if r["method"] == "final4"]).set_index(["gid", "level", "k"])
            j = mine.join(f4s, how="inner", rsuffix="_st")
            checks.append(("final4", "k 0-29", len(j), f"bits {int((j.bits == j.bits_st).sum())}/{len(j)}, "
                           f"PSNR {int(np.isclose(j.psnr, j.psnr_st, atol=1e-6, rtol=0).sum())}/{len(j)}, "
                           f"score {int(np.isclose(j.score, j.score_st, atol=1e-9, rtol=0).sum())}/{len(j)}",
                           "controller_real/final4_x264_val_*.parquet"))
    d = pd.DataFrame(rows)
    tag = "_cap" if CAP else ""
    d.to_parquet(f"{HERE}/rows_scored{tag}.parquet")
    for enc in ("x264", "x265"):
        table += compare(d, enc)
        dchecks += r3_diff_checks(d, enc)
    t = pd.DataFrame(table)
    L = ["# Frame-level baselines, val (x264 re-run on the shim; x265 and x264 CQP / ABR stored)"
         + (", one PSNR cap everywhere" if CAP else ""), "",
         *(["100 dB per-plane PSNR cap everywhere (cap_fix_<enc>.pkl: curves + stored final4); ABR rows uncapped, as in "
            "the team's report_val_cap.md (at most 1 GOP x 4 levels per k).", ""] if CAP else []),
         "score = dPSNR_B - 0.17 dB x %over (rclib metrics.score), mean over episodes, level-24 hole excluded. "
         "Δ = method - final4 at the same k, paired on (GOP, level); R3 = seeds 3-5 averaged per episode. "
         "paired_ci = rclib metrics.paired_ci (mean ± 95 % half-width, episodes independent); boot = 95 % clip "
         "bootstrap as the team's reports ('*' excludes 0).", "",
         t.to_markdown(index=False, floatfmt="+.3f"), "",
         "## Episode-level checks (x264 re-run vs stored)", "",
         pd.DataFrame(checks, columns=["method", "which", "episodes", "identical", "stored source"]).to_markdown(index=False), "",
         "## Reported differences (results_v1/final/report_val" + ("_cap" if CAP else "") + ".md)", "",
         pd.DataFrame(dchecks, columns=["enc", "quantity", "this table", "reported", "check"]).to_markdown(index=False)]
    open(f"{HERE}/summary{tag}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
