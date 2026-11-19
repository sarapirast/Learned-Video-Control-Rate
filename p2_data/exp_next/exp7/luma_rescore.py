"""Exp 7 test rows rescored in luma PSNR of pooled MSE (the metric of Pavneet's stream / live rows, his D50).

The sealed Exp 7 test rows (results_v1/final/exp7_test_<enc>.pkl, exp_next/exp7/test_eval.py) were scored with the
6:1:1 YUV PSNR of his stream code. Each row stores its per-GOP QPs, so it is rescored without encodes exactly as his
own_rc_stream_v1.rescore_luma (D50): per GOP, bits = the stored curve bits (infos, as every budget and lookup) and
PSNR = 10 log10(255^2 / mean luma MSE over the GOP's frames) of the same constant-QP encode (our
data/v1/320x180/rd/rd_frames.parquet, kind cqp: the source of his results_yrd/frames.pkl); the stream PSNR = pooled
MSE over GOPs; score = SE.stream_score (dPSNR_B against the stream's luma constant-QP curve - 0.17 x %over).
Checks: summed table bits equal each row's stored bits; the YUV comparisons reproduce report_test_cap.md.
The 16 / 32-GOP film rows (ED / ToS segments of his fresh set) have no per-frame luma and stay YUV.

  /scratch1/aayushso/envs/ee599/bin/python -I exp_next/exp7/luma_rescore.py --mse   (pyarrow; per-GOP luma MSE table)
  /scratch1/aayushso/envs/rc/bin/python -I exp_next/exp7/luma_rescore.py           (gymnasium; rclib's stream scoring)
Out: results_v1/final/luma_gop_mse.pkl ({enc: {gid: mean luma MSE per QP 18..50}}), results_v1/final/exp7_luma.md
     (+ exp7_test_<enc>_luma.pkl, rows as the input with luma fields)
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

SRC = "/scratch1/aayushso/ee599/exp_next/exp7/src_pavneet/pavneet_handoff"
ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/final"
ENCS = ["x264", "x265"]
MSE = f"{OUT}/luma_gop_mse.pkl"
QPS = list(range(18, 51))
if sys.argv[1:] == ["--mse"]:
    out = {}
    f = pd.read_parquet(f"{ROOT}/data/v1/320x180/rd/rd_frames.parquet",
                        columns=["encoder", "clip_id", "gop", "kind", "qp", "mse_y"]).query("kind == 'cqp'")
    m = f.groupby(["encoder", "clip_id", "gop", "qp"]).mse_y.agg(["mean", "size"]).reset_index()
    assert (m["size"] == 30).all()
    m["gid"] = m.clip_id + "@" + (30 * m.gop).astype(str)
    for (e, g), x in m.groupby(["encoder", "gid"]):
        x = x.set_index("qp").reindex(QPS)
        assert x["mean"].notna().all(), (e, g)
        out.setdefault(e, {})[g] = x["mean"].to_numpy(float)
    pickle.dump(out, open(MSE, "wb"))
    print({e: len(v) for e, v in out.items()}, "->", MSE)
    sys.exit(0)
os.environ["RC_CODEC"] = ENCS[0]
os.environ["RC_WORK"] = f"{SRC}/artifacts/{ENCS[0]}/v1"
os.environ.setdefault("RC_V1", "1")
os.environ.setdefault("RC_BUDGETS", "24,30,36,42")
os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, f"{SRC}/repo")
sys.path.insert(0, f"{ROOT}/exp_next/exp5")
from rclib import clipenv as CE, config as C, streamenv as SE  # noqa: E402
from shift_report import boot, fmt  # noqa: E402

# report_test_cap.md, Exp 7 section (YUV): policy - retuned rule, N=8 same-clip / mixed
YUV_REF = {"x264": {"clip": -0.026, "mixed": None}, "x265": {"clip": 0.050, "mixed": None}}


def luma_tabs(enc, infos):
    assert list(C.QPS) == QPS
    mse = pickle.load(open(MSE, "rb"))[enc]
    tabs = {}
    for g, v in mse.items():
        if g not in infos:
            continue
        bits, psnr = np.full(C.QP_MAX + 1, np.nan), np.full(C.QP_MAX + 1, np.nan)
        bits[C.QPS] = infos[g]["curve"]["bits"]
        psnr[C.QPS] = 10 * np.log10(255.0 ** 2 / np.maximum(v, 1e-10))   # = rclib.yrd.psnr
        tabs[g] = {"bits": bits, "psnr": psnr}
    return tabs


def rescore(rows, tabs):
    out, dif = [], 0.0
    for x in rows:
        tb = [tabs[g] for g in x["stream"]]
        q = [int(v) for v in x["qps"]]
        tot = float(sum(t["bits"][v] for t, v in zip(tb, q)))
        mp = float(CE.pooled([t["psnr"][v] for t, v in zip(tb, q)]))
        dif = max(dif, abs(tot / x["bits"] - 1))
        dps, over, sc = SE.stream_score(tb, tot, mp, x["budget"])
        out.append({**x, "bits": tot, "psnr": mp, "dpsnr": dps, "over_pct": over, "over": tot > 1.01 * x["budget"],
                    "score": sc, "use": tot / x["budget"], "psnr_yuv": x["psnr"], "score_yuv": x["score"]})
    assert dif < 1e-6, f"luma tables disagree with stored bits: {dif}"
    return out


def compare(R, n, kind, rule, field):
    pol = [R[k] for k in R if k[0] == "policy" and k[1] == n]
    idx = [i for i, r in enumerate(pol[0]) if r["kind"] == kind]
    p = np.mean([[rr[i][field] for i in idx] for rr in pol], axis=0)
    q = np.array([R[(rule, n, 2)][i][field] for i in idx])
    o = np.mean([[rr[i]["bits"] > 1.01 * rr[i]["budget"] for i in idx] for rr in pol], axis=0)
    oq = np.array([R[(rule, n, 2)][i]["bits"] > 1.01 * R[(rule, n, 2)][i]["budget"] for i in idx])
    return boot(p - q, np.array([pol[0][i]["group"] for i in idx])), len(idx), 100 * o.mean(), 100 * oq.mean()


def main():
    L = ["# Exp 7 stream level in luma PSNR (exp_next/exp7/luma_rescore.py)", "",
         "The sealed Exp 7 test rows (results_v1/final/exp7_test_<enc>.pkl) rescored from their stored per-GOP QPs in "
         "luma PSNR of pooled MSE, the definition of Pavneet's D50 luma stream rows (own_rc_stream_v1.rescore_luma). "
         "No encodes. Policy = the selected stream policy (x264 bc_ppo L2, x265 ppo L2), 3 seeds averaged per stream; "
         "retuned rule = rule A (rule_8_<enc>_v2, L=2); rule as reported = Pavneet's D34 rule (rule_wide). "
         "95 % cluster bootstrap over source groups; * = CI excludes 0. Over = streams > 1 % over budget.", "",
         "| enc | streams | comparison | YUV 6:1:1 (as reported) | luma | n | over: policy / rule (%) |",
         "|---|---|---|---|---|---:|---|"]
    for enc in ENCS:
        os.environ["RC_CODEC"] = enc
        infos = pickle.load(open(f"{SRC}/artifacts/{enc}/v1/results_infos/infos_slim.pkl", "rb"))   # = stream_rl.load_infos()
        tabs = luma_tabs(enc, infos)
        R = pickle.load(open(f"{OUT}/exp7_test_{enc}.pkl", "rb"))
        Rl = {k: (rescore(v, tabs) if k[1] == 8 else v) for k, v in R.items()}
        dest = f"{OUT}/exp7_test_{enc}_luma.pkl"
        if not os.path.exists(dest):
            pickle.dump(Rl, open(dest, "wb"))
        for kind in ("clip", "mixed"):
            for lab, rule in (("policy - rule A (retuned)", "rule_retuned"), ("policy - rule as reported", "rule_reported")):
                by, n, o1, o2 = compare(R, 8, kind, rule, "score")
                bl, _, o1l, o2l = compare(Rl, 8, kind, rule, "score")
                ref = YUV_REF[enc][kind]
                if ref is not None and rule == "rule_retuned":
                    assert abs(by[0] - ref) < 6e-4, (enc, kind, by[0], ref)
                L.append(f"| {enc} | 8-GOP {'same-clip' if kind == 'clip' else 'mixed'} | {lab} | {fmt(by)} | {fmt(bl)} "
                         f"| {n} | {o1l:.0f} / {o2l:.0f} |")
        for nn in (16, 32):
            if ("policy", nn, 0) in R:
                by, n, o1, o2 = compare(R, nn, "clip", "rule_retuned", "score")
                L.append(f"| {enc} | film {nn}-GOP | policy - rule A (retuned) | {fmt(by)} | (no per-frame luma) | {n} "
                         f"| {o1:.0f} / {o2:.0f} (YUV) |")
    L += ["", "Checks passed: summed luma-table bits equal every row's stored bits (max rel. diff < 1e-6); the YUV "
          "primary (policy - rule A, 8-GOP same-clip) reproduces report_test_cap.md (x264 -0.026, x265 +0.050).",
          "Over-budget flags do not depend on the PSNR convention (bits only); the luma column's over rates equal YUV's."]
    open(f"{OUT}/exp7_luma.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
