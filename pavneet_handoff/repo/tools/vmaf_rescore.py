"""D52: VMAF rescoring of every row that codes each GOP at one constant QP (no new encodes, nothing retrained).

Rows store their per-GOP QPs, and the D49 VMAF curves hold the per-frame VMAF of exactly those constant-QP encodes
(bits checked equal to the PSNR curves), so a row's VMAF is a lookup:
  stream VMAF  = mean over all frames (= mean of the GOPs' mean VMAF, equal frame counts)
  dVMAF_B      = stream VMAF - VMAF of the stream's constant-QP curve at exactly the budget B (same construction as
                 dPSNR_B: GOPs share one QP, bits summed, curve interpolated in log bits)
  VMAF score   = dVMAF_B - slope x (0.17 x % over + 0.5 x % stalled), slope = dVMAF / dPSNR(luma) of the same stream
                 curve at B, i.e. the dB penalties converted at the local exchange rate of that stream.
Bits, overshoot and stalls are identical to the PSNR tables. The oracle maximises the PSNR score, so in VMAF it is a
"PSNR oracle", not a VMAF ceiling. Encoder rows (ABR, ABR+VBV, two-pass, E2) are real encodes without stored output and
are not covered; neither are per-GOP (per-frame QP) rows.

  RC_V1=1 RC_PRESET=medium RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 python tools/vmaf_rescore.py
Output: results/v1_vmaf/<codec>.md
"""
import glob
import os
import pickle
import sys

import numpy as np

os.environ.setdefault("RC_V1", "1")
os.environ["RC_BUF_LADDER"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import stream_rl as S  # noqa: E402
from rclib import bufenv as BE, clipenv as CE, config as C, metrics, yrd  # noqa: E402

W = C.WORK
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "v1_vmaf")
Q = np.array(C.QPS)
key = lambda r: (tuple(r["stream"]), int(r["q0"]), round(float(r["s"]), 4))  # noqa: E731


def load_vmaf(scale):
    V = {}
    for p in sorted(glob.glob(os.path.join(W, "results_vmaf", scale, "*of*.pkl"))):
        d = pickle.load(open(p, "rb"))
        assert d["bits_mismatch"] == 0, p
        for g, r in d["rows"].items():
            v = np.full(C.QP_MAX + 1, np.nan)
            v[Q] = r["vmaf"].mean(1)
            V[g] = v
    return V


class Scorer:
    def __init__(self, infos, Y):
        self.infos, self.bits, self.psnr = infos, {}, {}
        for g, x in infos.items():
            if x["gop"]["split"] in ("val", "test"):
                b = np.full(C.QP_MAX + 1, np.nan)
                b[Q] = x["curve"]["bits"]
                p = np.full(C.QP_MAX + 1, np.nan)
                p[yrd.QLO:yrd.QHI + 1] = Y[g]["cq_psnr"]
                self.bits[g], self.psnr[g] = b, p
        self.V = {s: load_vmaf(s) for s in ("native", "1080")}

    def row(self, x, B, stall=0.0):
        gs, qs = list(x["stream"]), [int(q) for q in x["qps"]]
        tot = float(sum(self.bits[g][q] for g, q in zip(gs, qs)))
        if "bits" in x:
            assert abs(tot / x["bits"] - 1) < 1e-6, (tot, x["bits"])
        over = float(metrics.overshoot(tot, B))
        cb = np.sum([self.bits[g][Q] for g in gs], 0)
        cp = CE.pooled([self.psnr[g][Q] for g in gs], 0)
        pen_db = metrics.OVER_PENALTY_DB * over + BE.LAM_STALL * stall
        dp = float(CE.pooled([self.psnr[g][q] for g, q in zip(gs, qs)]) - metrics.psnr_at_bits({"bits": cb, "psnr": cp}, B))
        out = {"group": x["group"], "dps": dp, "sc_db": dp - pen_db}
        h = 0.05
        for s, V in self.V.items():
            cv = np.mean([V[g][Q] for g in gs], 0)
            c = {"bits": cb, "psnr": cv}
            dv = float(np.mean([V[g][q] for g, q in zip(gs, qs)]) - metrics.psnr_at_bits(c, B))
            dvs = float(metrics.psnr_at_bits(c, B * np.exp(h)) - metrics.psnr_at_bits(c, B * np.exp(-h)))
            dps = float(metrics.psnr_at_bits({"bits": cb, "psnr": cp}, B * np.exp(h))
                        - metrics.psnr_at_bits({"bits": cb, "psnr": cp}, B * np.exp(-h)))
            slope = dvs / dps if dps > 1e-9 else 0.0
            out[f"dv_{s}"], out[f"sc_{s}"], out[f"slope_{s}"] = dv, dv - slope * pen_db, slope
        return out


def avg(rows_by_seed):
    """per-case mean over seeds of every numeric field."""
    acc = {}
    for rows in rows_by_seed:
        for k, r in rows.items():
            acc.setdefault(k, []).append(r)
    return {k: {f: (v[0][f] if f == "group" else float(np.mean([x[f] for x in v]))) for f in v[0]} for k, v in acc.items()}


def ci(a, b, f):
    ks = [k for k in a if k in b]
    d = np.array([a[k][f] - b[k][f] for k in ks])
    t = S.cboot(d, np.array([a[k]["group"] for k in ks]))
    star = "*" if t[1] > 0 or t[2] < 0 else ""
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]{star}", t[0], len(ks)


def live(sc):
    L = ["## Live stream (ladder budget, D45)", "",
         "Per setting: paired differences on identical cases, seeds averaged per case. Columns: luma PSNR score (dB, "
         "the paper's metric, recomputed here as a check; vbv2 / mpc re-tuned on the wide grid as in the paper), VMAF score at native 320x180 and at 1080p (VMAF points, "
         "penalties converted at the local VMAF/dB rate), and raw dVMAF_B without penalties.", ""]
    for ch, tag in (("AR(1)", "results_buffer_ladder"), ("LTE", "results_buffer_trace_ladder")):
        d = os.path.join(W, tag)
        b2 = pickle.load(open(os.path.join(d, "baselines2_wide.pkl"), "rb"))["rows"]   # vbv2 / mpc on the wide grid (D44)
        for split, nm in (("test", "8-GOP streams"), ("test16", "16-GOP playlists")):
            M = {}
            for m in ("vbv2", "mpc"):
                M[m] = {key(r): sc.row(r, r["budget"], r["stall_pct"]) for r in b2[(m + "w", 2, split)]}
            for m in ("ppo_v2", "il_ppo"):
                M[m] = avg([{key(r): sc.row(r, r["budget"], r["stall_pct"]) for r in pickle.load(open(p, "rb"))["res"][split]}
                            for p in sorted(glob.glob(os.path.join(d, f"{m}_L2_s*", "eval.pkl")))])
            orc = {}
            for p in sorted(glob.glob(os.path.join(d, "oracle", f"{split}_*of*.pkl"))):
                for r in pickle.load(open(p, "rb")):
                    B = float(r["s"]) * len(r["stream"]) * float(BE.ladder_bits(sc.infos)[int(r["q0"])])
                    orc[key(r)] = sc.row(r, B, r["stall_pct"])
            if orc:
                M["oracle"] = orc
            L += [f"### {C.CODEC}, {ch}, {nm}", "",
                  "| comparison | n | PSNR score (dB) | VMAF score native | VMAF score 1080p | dVMAF_B native | dVMAF_B 1080p |",
                  "|---|---|---|---|---|---|---|"]
            pairs = [("il_ppo", "vbv2"), ("il_ppo", "mpc"), ("il_ppo", "ppo_v2"), ("ppo_v2", "vbv2"), ("oracle", "vbv2"),
                     ("oracle", "il_ppo")]
            share = {}
            for a, b in pairs:
                if a not in M or b not in M:
                    continue
                cells, n = [], 0
                for f in ("sc_db", "sc_native", "sc_1080", "dv_native", "dv_1080"):
                    s, mu, n = ci(M[a], M[b], f)
                    cells.append(s)
                    share[(a, b, f)] = mu
                L.append(f"| {a} - {b} | {n} | " + " | ".join(cells) + " |")
            if "oracle" in M:
                sh = [f"{100 * share[('il_ppo', 'vbv2', f)] / share[('oracle', 'vbv2', f)]:.0f}%"
                      if share[("oracle", "vbv2", f)] > 0 else "--" for f in ("sc_db", "sc_native", "sc_1080")]
                L.append(f"\nShare of the PSNR-oracle's gain over vbv2 closed by il_ppo: PSNR {sh[0]}, VMAF native {sh[1]}, "
                         f"VMAF 1080p {sh[2]}.")
            sl = np.array([r["slope_native"] for r in M["vbv2"].values()]), np.array([r["slope_1080"] for r in M["vbv2"].values()])
            L += ["", f"Local exchange rate (median over cases): {np.median(sl[0]):.1f} VMAF native / dB, "
                  f"{np.median(sl[1]):.1f} VMAF 1080p / dB.", ""]
    return L


def stream(sc):
    base = pickle.load(open(os.path.join(W, "results_stream", "baselines.pkl"), "rb"))["rows"]
    M = {f"rule L{L}": {key(r): sc.row(r, r["budget"]) for r in base[("rule", L, "test")]} for L in (0, 2)}
    rw = pickle.load(open(os.path.join(W, "results_stream", "rule_wide.pkl"), "rb"))   # rule re-tuned beyond its grid
    M.update({f"rule_wide L{L}": {key(r): sc.row(r, r["budget"]) for r in rw[L]["rows"]["test"]} for L in (0, 2)})
    for m in ("bc_ppo", "bc_ppo_lag"):
        for L in (0, 2):
            ps = sorted(glob.glob(os.path.join(W, "results_stream", f"{m}_L{L}_s*", "eval.pkl")))
            if ps:
                M[f"{m} L{L}"] = avg([{key(r): sc.row(r, r["budget"]) for r in pickle.load(open(p, "rb"))["res"]["test"]}
                                      for p in ps])
    L = ["## Stream level (clip-level budgets, D46), test", "", "rule = original grid; rule_wide = re-tuned beyond it (the paper's main comparison).", "",
         "| comparison | n | PSNR score (dB) | VMAF score native | VMAF score 1080p | dVMAF_B native | dVMAF_B 1080p |",
         "|---|---|---|---|---|---|---|"]
    for a, b in (("bc_ppo L2", "rule L2"), ("bc_ppo L0", "rule L0"), ("rule L2", "rule L0"), ("bc_ppo L2", "bc_ppo L0"),
                 ("bc_ppo_lag L2", "rule L2"), ("bc_ppo L2", "rule_wide L2"), ("bc_ppo L0", "rule_wide L0"),
                 ("rule_wide L2", "rule_wide L0"), ("rule_wide L2", "rule L2")):
        if a in M and b in M:
            cells = [ci(M[a], M[b], f) for f in ("sc_db", "sc_native", "sc_1080", "dv_native", "dv_1080")]
            L.append(f"| {a} - {b} | {cells[0][2]} | " + " | ".join(c[0] for c in cells) + " |")
    return L + [""]


def main():
    infos = S.load_infos()
    sc = Scorer(infos, yrd.load(infos))
    L = [f"# VMAF rescoring, {C.CODEC} (D52)", "", __doc__.split("\n\n")[1], "",
         "95 % cluster bootstrap over source groups (mixed streams own cluster); * = CI excludes 0.", ""]
    L += live(sc) + stream(sc)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, f"{C.CODEC}.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
