"""D54 report: VMAF of the encoder rate-control rows vs the learned rows (reads experiments/encoder_vmaf.py output).

Encoder rows: stream VMAF = mean over the re-encoded frames; dVMAF_B and the penalty conversion exactly as D52
(tools/vmaf_rescore.py: the stream's constant-QP VMAF curve at the budget, penalties at the local VMAF/dB rate);
over-budget and stall percentages are the stored ones (bits re-checked equal). Learned rows: D52's lookups.

  RC_V1=1 RC_PRESET=medium RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 python tools/encoder_vmaf_report.py
Output: results/v1_vmaf/<codec>_encoder.md
"""
import glob
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vmaf_rescore as VR  # noqa: E402
from experiments import encoder_vmaf as EV, stream_rl as S  # noqa: E402
from rclib import bufenv as BE, clipenv as CE, config as C, metrics, yrd  # noqa: E402

W, Q = C.WORK, VR.Q


def enc_row(sc, gs, vm, B, over, stall, group):
    """vm: {scale: per-frame VMAF of the real encode}."""
    cb = np.sum([sc.bits[g][Q] for g in gs], 0)
    cp = CE.pooled([sc.psnr[g][Q] for g in gs], 0)
    pen_db = metrics.OVER_PENALTY_DB * over + BE.LAM_STALL * stall
    out, h = {"group": group}, 0.05
    for s, V in sc.V.items():
        c = {"bits": cb, "psnr": np.mean([V[g][Q] for g in gs], 0)}
        dv = float(np.mean(vm[s]) - metrics.psnr_at_bits(c, B))
        dvs = float(metrics.psnr_at_bits(c, B * np.exp(h)) - metrics.psnr_at_bits(c, B * np.exp(-h)))
        dps = float(metrics.psnr_at_bits({"bits": cb, "psnr": cp}, B * np.exp(h))
                    - metrics.psnr_at_bits({"bits": cb, "psnr": cp}, B * np.exp(-h)))
        slope = dvs / dps if dps > 1e-9 else 0.0
        out[f"dv_{s}"], out[f"sc_{s}"] = dv, dv - slope * pen_db
    return out


def load():
    R, bad = {}, 0
    for p in sorted(glob.glob(os.path.join(W, os.environ.get("RC_ENC_VMAF_DIR", "results_enc_vmaf"), "*of*.pkl"))):
        d = pickle.load(open(p, "rb"))
        R.update(d["rows"])
        bad += d["mismatch"]
    return R, bad


def main():
    infos = S.load_infos()
    sc = VR.Scorer(infos, yrd.load(infos))
    R, bad = load()
    meta = dict(EV.items())
    run = pickle.load(open(os.path.join(W, "results_own_rc_stream_v1_luma", "run.pkl"), "rb"))
    L = [f"# VMAF of the encoder rate-control rows, {C.CODEC} (D54)", "",
         f"{len(R)} re-encodes; per-GOP bits differing from the stored run: {bad}. VMAF score = dVMAF_B - penalties at "
         "the local VMAF/dB rate (as D52). 95 % cluster bootstrap over source groups; * = CI excludes 0.", "",
         "| comparison | n | VMAF score native | VMAF score 1080p | dVMAF_B native | dVMAF_B 1080p |", "|---|---|---|---|---|---|"]
    F = ("sc_native", "sc_1080", "dv_native", "dv_1080")

    def line(name, a, b):
        if not a or not b:
            return
        cells = [VR.ci(a, b, f) for f in F]
        L.append(f"| {name} | {cells[0][2]} | " + " | ".join(c[0] for c in cells) + " |")

    # stream level: learned rows from D52's lookups, encoder rows from the re-encodes
    M = {}
    for m in ("bc_ppo",):
        ps = sorted(glob.glob(os.path.join(W, "results_stream", f"{m}_L2_s*", "eval.pkl")))
        M[m] = VR.avg([{VR.key(r): sc.row(r, r["budget"]) for r in pickle.load(open(p, "rb"))["res"]["test"]} for p in ps])
    base = pickle.load(open(os.path.join(W, "results_stream", "baselines.pkl"), "rb"))["rows"]
    M["rule"] = {VR.key(r): sc.row(r, r["budget"]) for r in base[("rule", 2, "test")]}
    for cfg in EV.STREAM_CFGS:
        E = {}
        for it, r in R.items():
            if it[0] == "stream" and it[1] == cfg:
                st, q0, s = it[2], it[3], it[4]
                v = run[(st, q0, s)] if (st, q0, s) in run else run[(list(st), q0, s)]
                E[(st, q0, round(s, 4))] = enc_row(sc, list(st), {"native": r["vmaf_native"], "1080": r["vmaf_1080"]},
                                                   meta[it]["B"], v[cfg]["over_pct"], 0.0, v["group"])
        M[cfg] = E
    L.insert(-2, "## Stream level (on-demand, clip-level budgets), test, 8 GOPs, learned rows at L = 2\n")
    for a, b in (("bc_ppo", "abr_vbv"), ("bc_ppo", "2pass"), ("rule", "abr_vbv"), ("rule", "2pass")):
        line(f"{a} - encoder {b}", M[a], M[b])
    # live channel, ladder budget: il_ppo (3 seeds) vs E2
    for tag, ch in (("results_buffer_ladder", "AR(1)"), ("results_buffer_trace_ladder", "LTE")):
        d = os.path.join(W, tag)
        for split in ("test", "test16"):
            E = {}
            rows = {(tuple(r["stream"]), int(r["q0"]), round(float(r["s"]), 4)): r
                    for r in EV._real_rows(d, split).get(f"enc_vbv_f{EV.best_f(d):g}", [])} if os.path.isdir(d) else {}
            for it, r in R.items():
                if it[0] == "live" and it[1] == tag and it[2] == split:
                    k = (it[3], it[4], round(it[5], 4))
                    x = rows[k]
                    E[k] = enc_row(sc, list(it[3]), {"native": r["vmaf_native"], "1080": r["vmaf_1080"]},
                                   float(x["budget"]), float(x["over_pct"]), float(x["stall_pct"]), x["group"])
            if not E:
                continue
            il = VR.avg([{VR.key(r): sc.row(r, r["budget"], r["stall_pct"]) for r in pickle.load(open(p, "rb"))["res"][split]}
                         for p in sorted(glob.glob(os.path.join(d, "il_ppo_L2_s*", "eval.pkl")))])
            L.append(f"| live {ch} {split}: il_ppo - encoder ABR+VBV | " + "|".join("" for _ in range(0)) +
                     " | ".join([str(sum(k in il for k in E))] + [VR.ci(il, E, f)[0] for f in F]) + " |")
    out = os.path.join(VR.OUT, f"{C.CODEC}_encoder.md")
    os.makedirs(VR.OUT, exist_ok=True)
    open(out, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
