"""test2 report (pre-registration exp_next/test2/PREREG.md, frozen 11-17).

  /scratch1/aayushso/envs/ee599/bin/python -I exp_next/test2/report.py            gate, then the test2 report
  ... report.py --gate-only                                                       parity gate only
Gate (PREREG section 2): every parity.py stage OK; R3 k5 and CQL->PPO parity rows equal the stored v1 test rows;
test2 cap_fix equals v1's on the parity GOPs. No test2 number is printed unless the gate passes.
Scoring as results_v1/final/report_test_cap.md: rclib.metrics.score (dPSNR_B - 0.17 x %over) on the test2 curves
and budgets (rcwork_t2/<enc>_resh infos; flat GOPs are not in them) with the 100 dB cap (results_v1/test2/
cap_fix_<enc>.pkl); hole = budget above the curve maximum; seeds averaged per episode; 95 % clip bootstrap
(exp_next/exp5/shift_report.boot, 2,000 resamples; one clip per uploader). Labels: data/t2/320x180/gops.csv
(after the cut review). Out: results_v1/test2/report_test2.md
"""
import argparse
import glob
import importlib.util
import os
import pickle
import re
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
ROOT = "/scratch1/aayushso/ee599"
sys.path.insert(0, f"{ROOT}/repo-pavneet")
sys.path.insert(0, f"{ROOT}/exp_next/exp5")
from rclib import metrics  # noqa: E402
from shift_report import RNG, boot, fmt  # noqa: E402

T2 = f"{ROOT}/data/t2/320x180"
RCT = "/scratch1/aayushso/rcwork_t2"
RCV = "/scratch1/aayushso/rcwork_v1"
OUT = f"{ROOT}/results_v1/test2"
ABR_M = {"x264": 0.90, "x265": 0.93}
KS = (0, 2, 5, 10, 29)
V1TEST = {"x264": "+0.067 [+0.023, +0.107]", "x265": "+0.163 [+0.086, +0.243]"}   # report_test_cap.md primary


def _mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- gate
def same_rows(t, ref):
    st = {(r["gid"], r["budget"]): r for r in ref}
    ok = sum((r["gid"], r["budget"]) in st and abs(r["score"] - st[(r["gid"], r["budget"])]["score"]) < 1e-9
             and list(r["qps"]) == list(st[(r["gid"], r["budget"])]["qps"]) for r in t)
    return ok, len(t)


def gate():
    PA = _mod("parity", f"{ROOT}/exp_next/test2/parity.py")
    L, ok_all = ["## Parity gate (PREREG section 2)", ""], True
    for s in PA.STAGES:
        r = PA.stage(s)
        n_cols = r.count("mismatched columns:")      # budgets / prev report "mismatched columns: none" per check
        ok = "MISMATCH" not in r and "not yet" not in r and (
            n_cols > 0 and n_cols == r.count("mismatched columns: none")
            or n_cols == 0 and all("OK" in p for p in re.split(r"; | \| ", r)))
        ok_all &= ok
        L.append(f"- {'OK  ' if ok else 'FAIL'} {s}: {r}")
    for enc in ("x264", "x265"):
        for model in ("r3k5", "cqlppo"):
            f = f"{OUT}/{model}_parity_{enc}.pkl"
            if not os.path.exists(f):
                L.append(f"- FAIL {model} {enc}: not yet")
                ok_all = False
                continue
            ok = tot = 0
            for (s, k), rows in pickle.load(open(f, "rb")).items():
                if model == "r3k5":
                    ref = pickle.load(open(f"{ROOT}/results_v1/final/r3_test_{enc}.pkl", "rb"))[(s, "180k")]
                else:
                    ref = pickle.load(open(f"{RCV}/{enc}_lfqp/results_rl/cql_ppo_k{k}_fixed_st540k_s{s}/eval.pkl",
                                           "rb"))["res"][("fixed", k, "test")]
                a, b = same_rows(rows, ref)
                ok, tot = ok + a, tot + b
            good = tot > 0 and ok == tot
            ok_all &= good
            L.append(f"- {'OK  ' if good else 'FAIL'} {model} {enc}: rows equal to the stored v1 test rows {ok}/{tot}")
        f = f"{OUT}/cap_fix_{enc}.pkl"
        if not os.path.exists(f):
            L.append(f"- FAIL cap_fix {enc}: not yet")
            ok_all = False
            continue
        t, v = pickle.load(open(f, "rb")), pickle.load(open(f"{ROOT}/results_v1/final/cap_fix_{enc}.pkl", "rb"))
        par = ("ed_s05@", "NewsClip_360P-1b1c@", "park_joy@")
        tc = {g: c for g, c in t["curves"].items() if g.startswith(par)}
        vc = {g: c for g, c in v["curves"].items() if g.startswith(par)}
        tf = {k: x["psnr"] for k, x in t["final4"].items() if x["split"] == "parity"}
        vf = {k: x["psnr"] for k, x in v["final4"].items() if k[0].startswith(par)}
        good = set(tc) == set(vc) and all(np.allclose(tc[g], vc[g], rtol=0, atol=1e-9) for g in tc) and \
            set(tf) == set(vf) and all(abs(tf[k] - vf[k]) < 1e-9 for k in tf)
        ok_all &= good
        L.append(f"- {'OK  ' if good else 'FAIL'} cap_fix {enc}: parity GOPs {len(tc)} curves, {len(tf)} final4 rows "
                 f"equal to v1's")
    L += ["", f"**Gate: {'PASSED' if ok_all else 'NOT PASSED'}**", ""]
    return ok_all, L


# ---------------------------------------------------------------- scoring
class Scorer:
    def __init__(self, enc):
        inf = pickle.load(open(f"{RCT}/{enc}_resh/results_infos/infos.pkl", "rb"))
        self.inf = {g: x for g, x in inf.items() if x["gop"]["split"] == "test2"}
        self.fix = pickle.load(open(f"{OUT}/cap_fix_{enc}.pkl", "rb"))
        gops = pd.read_csv(f"{T2}/gops.csv")
        self.label = {f"{r.clip_id}@{r.start_frame}": r.label for r in gops.itertuples()}
        self.n_fixed = 0

    def curve(self, gid):
        cv = self.inf[gid]["curve"]
        if gid in self.fix["curves"]:
            assert len(cv["psnr"]) == len(self.fix["curves"][gid])
            return {**cv, "psnr": self.fix["curves"][gid]}
        return cv

    def row(self, method, gid, level, k, bits, psnr, seed=-1, stored=None):
        x = self.inf[gid]
        cv, B = self.curve(gid), x["budget"][level]
        s = float(metrics.score(bits, psnr, cv, B))
        if stored is not None and gid not in self.fix["curves"]:
            assert abs(s - stored) < 1e-6, (method, gid, level, s, stored)
        return {"method": method, "gid": gid, "clip": x["gop"]["clip"], "cat": x["gop"]["category"], "level": level,
                "k": k, "seed": seed, "score": s, "A": float(psnr - metrics.psnr_at_bits(cv, bits)), "rho": bits / B,
                "hole": B > max(cv["bits"]), "capgop": gid in self.fix["curves"],
                "cls": "cut/gradual" if self.label[gid] in ("cut", "gradual") else "stable"}


def _pkl(p):
    return pickle.load(open(p, "rb")) if os.path.exists(p) else None


def load_all(enc, S):
    rows = []
    d = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{ROOT}/results_v1/controller_real/t2final4_{enc}_test2_*.parquet"))
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    for r in d[d.gid.isin(S.inf)].itertuples():
        f = S.fix["final4"].get((r.gid, int(r.level_q0), int(r.k)))
        S.n_fixed += f is not None
        rows.append(S.row("final4", r.gid, int(r.level_q0), int(r.k), float(r.bits),
                          f["psnr"] if f else float(r.psnr_yuv)))
    for model, name in (("r3k5", "R3"), ("r3k2", "R3"), ("cqlppo", "CQL->PPO 540k")):
        res = _pkl(f"{OUT}/{model}_test2_{enc}.pkl") or {}
        for (s, k), rr in res.items():
            rows += [S.row(name, r["gid"], r["budget"], k, r["bits"], r["psnr"], s, r["score"]) for r in rr]
    for model in ("r3k0a", "r3k29a"):   # PREREG secondary 10: Ahhana's R3 k0 / k29 (x264 only; eval_ahhana.py)
        res = _pkl(f"{OUT}/{model}_test2_{enc}.pkl") or {}
        for (s, k), rr in res.items():
            rows += [S.row("R3 (Ahhana)", r["gid"], r["budget"], k, r["bits"], r["psnr"], s, r["score"]) for r in rr]
    for tag in ("k25_s345", "k0_s012"):
        rows += [S.row("BC alone", r["gid"], r["level"], r["k"], r["bits"], r["psnr"], r["seed"], r["score"])
                 for r in _pkl(f"{OUT}/bc_rows_{enc}_test2_{tag}.pkl") or []]
    rows += [S.row("final4 + shift", r["gid"], r["level"], 5, r["bits"], r["psnr"], -1, r["score"])
             for r in _pkl(f"{OUT}/shift_rows_{enc}_test2_qbin_k5_0of1.pkl") or []]
    own = _pkl(f"{OUT}/seqhist_own_test2_{enc}.pkl") or {}
    rows += [S.row("R3 own history", r["gid"], r["budget"], 5, r["bits"], r["psnr"], s, r["score"])
             for s, rr in own.items() for r in rr]
    fs = glob.glob(f"{OUT}/abr/rows_{enc}_test2_*.parquet")
    if fs:
        a = pd.concat(pd.read_parquet(f) for f in fs)
        a = a[np.isclose(a.margin, ABR_M[enc])]
        a["gid"] = a.clip_id + "@" + (30 * a.gop).astype(str)
        rows += [S.row(f"ABR m{ABR_M[enc]:.2f}", r.gid, int(r.level_q0), int(r.k), float(r.bits), float(r.psnr_yuv))
                 for r in a[a.gid.isin(S.inf)].itertuples()]
    for gid, x in S.inf.items():        # constant QP from the curves (baselines_v1.offline_rows definitions)
        cv = S.curve(gid)
        qs, bits = list(cv["qps"]), np.asarray(cv["bits"])
        for lv, B in x["budget"].items():
            ok = np.flatnonzero(bits <= B)
            i = int(ok[0]) if len(ok) else qs.index(50)
            rows.append(S.row("cqp_best (hindsight)", gid, lv, 29, float(bits[i]), float(cv["psnr"][i])))
    bud = pd.read_csv(f"{T2}/budgets.csv").query("encoder == @enc and split == 'test2'")
    for r in bud.itertuples():
        gid = f"{r.clip_id}@{30 * r.gop}"
        if gid not in S.inf:
            continue
        cv = S.curve(gid)
        qs = list(cv["qps"])
        for k in KS:
            i = qs.index(int(np.clip(round(getattr(r, f"base_qp_est_k{k}")), 18, 50)))
            rows.append(S.row("cqp_est", gid, int(r.level_q0), k, float(cv["bits"][i]), float(cv["psnr"][i])))
    return pd.DataFrame(rows)


def dec(x):
    return {"n": len(x), "score": x.score.mean(), "A": x.A.mean(), "E-P": (x.score - x.A).mean(),
            "mean |err| %": 100 * (x.rho - 1).abs().mean(), "p90 |err| %": 100 * (x.rho - 1).abs().quantile(0.9),
            "signed err %": 100 * (x.rho - 1).mean(), "% over": 100 * (x.rho > 1).mean()}


KEY = ["gid", "clip", "cat", "level", "cls", "capgop"]


def paired(y, k):
    """(GOP, level) x method table at lookahead k, seeds averaged."""
    z = y[y.k == k]
    return z.groupby(KEY + ["method"]).score.mean().unstack("method").reset_index()


def cmp(p, a, b, extra=""):
    q = p.dropna(subset=[a, b])
    if not len(q):
        return f"- {a} - {b}{extra}: no rows"
    return f"- {a} - {b}{extra}: {fmt(boot(q[a] - q[b], q['clip']))} (n {len(q)}, {q['clip'].nunique()} clips)"


def class_gap(q, a, b, n=2000):
    """(a - b) on cut/gradual minus (a - b) on stable, clip bootstrap."""
    d = (q[a] - q[b]).to_numpy()
    cut = (q.cls == "cut/gradual").to_numpy()
    cl = q["clip"].to_numpy()
    u = np.unique(cl)
    idx = {c: np.flatnonzero(cl == c) for c in u}
    stat = lambda ii: d[ii][cut[ii]].mean() - d[ii][~cut[ii]].mean()
    ms = []
    for _ in range(n):
        ii = np.concatenate([idx[c] for c in RNG.choice(u, len(u))])
        if cut[ii].any() and (~cut[ii]).any():
            ms.append(stat(ii))
    return fmt((stat(np.arange(len(d))), np.percentile(ms, 2.5), np.percentile(ms, 97.5)))


def section(enc):
    S = Scorer(enc)
    d = load_all(enc, S)
    y = d[~d.hole]
    L = [f"## {enc}", "",
         f"Scored test2 GOPs {len(S.inf)} ({len({x['gop']['clip'] for x in S.inf.values()})} clips); hole episodes "
         f"{int(d[d.method == 'final4'].hole.sum())} of {int((d.method == 'final4').sum())} final4 rows; cap-affected "
         f"GOPs {sum(g in S.fix['curves'] for g in S.inf)} (final4 rows with capped PSNR {S.n_fixed}).", ""]
    p5 = paired(y, 5)
    if "R3" in p5 and "final4" in p5:
        prim = p5.dropna(subset=["R3", "final4"])
        L.append(f"- **PRIMARY R3 (180k, s3-5) - final4, k5: {fmt(boot(prim.R3 - prim.final4, prim['clip']))}** "
                 f"(n {len(prim)}, {prim['clip'].nunique()} clips)   [v1 test: {V1TEST[enc]}]")
        ph = paired(d, 5).dropna(subset=["R3", "final4"])
        L.append(f"- R3 - final4, k5, hole included: {fmt(boot(ph.R3 - ph.final4, ph['clip']))} (n {len(ph)})")
        z = y[(y.k == 5) & (y.method == "R3")].merge(prim[KEY + ["final4"]], on=KEY)
        L.append("- per seed: " + "; ".join(f"s{s} {(x.score - x.final4).mean():+.3f}" for s, x in z.groupby("seed")))
        L += ["", "Secondary 1, by class (R3 - final4, k5): " + "; ".join(
            f"{c} {fmt(boot(x.R3 - x.final4, x['clip']))} (n {len(x)}, {x['clip'].nunique()} clips)"
            for c, x in prim.groupby("cls")),
            f"- cut/gradual minus stable: {class_gap(prim, 'R3', 'final4')}",
            "- by level: " + "; ".join(f"L{lv} {(x.R3 - x.final4).mean():+.3f}" for lv, x in prim.groupby("level")), "",
            "Secondary 2, by category (R3 - final4, k5; descriptive):", "",
            pd.DataFrame([{"category": c, "clips": x['clip'].nunique(), "n": len(x), "R3 - final4": fmt(boot(x.R3 - x.final4, x["clip"]))}
                          for c, x in prim.groupby("cat")]).to_markdown(index=False), ""]
    L += ["Secondary 3, k-curve (mean score, hole excluded, seeds averaged; cqp_best is hindsight, k not applicable):", "",
          y.groupby(["method", "k", "gid", "level"]).score.mean().reset_index()
          .pivot_table(index="method", columns="k", values="score", aggfunc="mean").round(3).to_markdown(), ""]
    L.append("Secondaries 4-6 (paired, hole excluded):")
    for k in (0, 2, 5):
        p = paired(y, k)
        for a, b in (("R3", "final4"), ("R3", "BC alone"), ("BC alone", "final4"), ("R3", "final4 + shift"),
                     ("R3", "CQL->PPO 540k"), ("CQL->PPO 540k", "final4"), ("R3", f"ABR m{ABR_M[enc]:.2f}"),
                     ("R3", "cqp_est")):
            if a in p and b in p and not (k == 5 and (a, b) == ("R3", "final4")):
                L.append(cmp(p, a, b, f", k{k}"))
        abr = f"ABR m{ABR_M[enc]:.2f}"
        if k == 5 and "R3" in p and abr in p:
            L.append(cmp(p[~p.capgop], "R3", abr, ", k5, cap-affected GOPs excluded (ABR rows are uncapped)"))
    L += ["", "Secondary 7, decomposition at k5 (hole excluded):", "",
          pd.DataFrame([{"method": m, **dec(x)} for m, x in y[y.k == 5].groupby("method")]).round(3)
          .to_markdown(index=False), ""]
    if "R3 own history" in p5:
        L += ["Secondary 8, R3 with its own previous-GOP history (k5):",
              cmp(p5, "R3 own history", "final4"), cmp(p5, "R3 own history", "R3", " (history effect)"), ""]
    if "R3 (Ahhana)" in set(y.method):
        L.append("Secondary 10, Ahhana's R3 at k0 / k29 (s3-5, 180k; descriptive; val parity 1680/1680 per model):")
        for k in (0, 29):
            p = paired(y, k)
            if "R3 (Ahhana)" in p:
                L += [cmp(p, "R3 (Ahhana)", b, f", k{k}") for b in ("final4", "BC alone", "CQL->PPO 540k") if b in p]
        L.append("")
    return L, p5


def pooled(p5s):
    R1 = _mod("final_report", f"{ROOT}/exp_next/final/report.py")
    L = ["## Secondary 9, pooled v1 test + test2 (R3 - final4, k5, per encoder; descriptive)", ""]
    for enc, p in p5s.items():
        if "R3" not in p:
            continue
        S = R1.Scorer(enc, cap=True)
        v = pd.DataFrame(R1.load_r3(enc, "test", S))
        v = v[(~v.hole) & (v.k == 5) & v.method.isin(["R3 180k", "final4"])]
        v = v.groupby(["gid", "clip", "level", "method"]).score.mean().unstack("method").reset_index().dropna()
        dv = pd.DataFrame({"d": v["R3 180k"] - v.final4, "clip": "v1:" + v["clip"]})
        q = p.dropna(subset=["R3", "final4"])
        dt = pd.DataFrame({"d": q.R3 - q.final4, "clip": "t2:" + q["clip"]})
        u = pd.concat([dv, dt])
        L.append(f"- {enc}: {fmt(boot(u.d, u['clip']))} (n {len(u)}: v1 test {len(dv)}, test2 {len(dt)})")
    return L + [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="debug only: print test2 numbers with a failed gate")
    a = ap.parse_args()
    ok, L = gate()
    print("\n".join(L))
    if a.gate_only or not (ok or a.force):
        if not ok:
            print("gate not passed: no test2 numbers")
        return
    H = ["# test2 results (exp_next/test2/report.py)", "",
         "Pre-registration exp_next/test2/PREREG.md (frozen 11-17). Frozen v1 models, evaluation only. Score dPSNR_B - "
         "0.17 x %over, 100 dB cap; flat GOPs out; hole excluded unless stated; seeds averaged per episode; 95 % clip "
         "bootstrap, one clip per uploader ('*' = CI excludes 0). Labels after the cut review.", ""]
    if not ok:
        H += ["**GATE NOT PASSED (--force): not a result.**", ""]
    p5s = {}
    for enc in ("x264", "x265"):
        s, p5s[enc] = section(enc)
        H += s
    H += pooled(p5s)
    H += L
    os.makedirs(OUT, exist_ok=True)
    dest = f"{OUT}/report_test2{'_FORCED' if not ok else ''}.md"
    open(dest, "w").write("\n".join(H) + "\n")
    print("\n".join(H[:-len(L)]))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
