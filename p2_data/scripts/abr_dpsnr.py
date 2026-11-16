"""The encoders' own rate control (ABR+VBV) and the other week-2 causal baselines on the quality-at-budget metric,
against the frozen controller final4 and the learners. No encodes: rescoring of results_v1/baselines_v1.parquet.

Week 2 (scripts/baselines_v1.py) scored these on the old metric only. Here every stored row (bits = slice bits,
psnr_yuv = mean of per-frame YUV PSNR, the same conventions as every other result) is rescored with the dB metric
exactly as scripts/lfq_compare.py scores the controller: metrics.score(bits, psnr_yuv, infos[g]['curve'],
infos[g]['budget'][level]) under RC_METRIC=dpsnr. The rows are then paired with results_v1/w3/class_kcurves_<codec>.csv
(final4, final3, res@hist, bc@prev, search; seeds averaged) on GOP x level x k. Flat GOPs drop out (not in the infos).

abr_vbv = 1-pass ABR, --bitrate = --vbv-maxrate = budget rate, --vbv-bufsize = one GOP's budget, --rc-lookahead k.
cqp_est = constant QP from the causal estimator (budgets.csv base_qp_est_k); ramp_causal = fixed spend-early ramp at
that QP; online_controller_v1 = the 11-04 controller (before tuning on this metric).

  python -I scripts/abr_dpsnr.py
Out: results_v1/w5/abr_dpsnr.md (+ .csv)
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import metrics  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
RC = "/scratch1/aayushso/rcwork_v1"
OUT = f"{ROOT}/results_v1/w5"
KS = (0, 2, 5, 10, 29)
RNG = np.random.default_rng(0)
BASE = ("abr_vbv", "cqp_est", "ramp_causal", "online_controller_v1")
OURS = ("final4", "final3", "res@hist", "bc@prev", "search")


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def ci(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


def main():
    b = pd.read_parquet(f"{ROOT}/results_v1/baselines_v1.parquet")
    gops = pd.read_csv(f"{ROOT}/data/v1/320x180/gops.csv").set_index(["clip_id", "gop"]).start_frame
    L = ["# Encoder rate control (ABR+VBV) and week-2 baselines on the quality-at-budget metric (scripts/abr_dpsnr.py)",
         "", "Score in dB (dPSNR_B - 0.17 per 1% over; 0 = constant QP spending exactly the budget). Test split, flat "
         "GOPs excluded, 4 budget levels pooled; learners seeds-averaged. Rows paired on GOP x level x k. CIs: 95% "
         "bootstrap over clips. Rescored from results_v1/baselines_v1.parquet (no new encodes).", ""]
    allrows = []
    for e in ("x264", "x265"):
        infos = pickle.load(open(f"{RC}/{e}_lfq/results_infos/infos_learn.pkl", "rb"))
        x = b[(b.encoder == e) & (b.split == "test") & b.method.isin(BASE)].copy()
        x["gid"] = [f"{c}@{gops[(c, g)]}" for c, g in zip(x.clip_id, x.gop)]
        x = x[x.gid.isin(infos)]
        # budgets must agree with the infos used for every other result
        bi = np.array([infos[g]["budget"][int(lv)] for g, lv in zip(x.gid, x.level_q0)])
        assert np.allclose(bi, x.budget_bits.to_numpy(), rtol=1e-6), "budget mismatch vs lfq infos"
        x["score_db"] = [float(metrics.score(bt, p, infos[g]["curve"], infos[g]["budget"][int(lv)]))
                         for bt, p, g, lv in zip(x.bits, x.psnr_yuv, x.gid, x.level_q0)]
        x["use"] = x.bits / x.budget_bits
        piv = x.pivot_table(index=["gid", "level_q0", "k"], columns="method", values="score_db").reset_index()
        piv = piv.rename(columns={"level_q0": "budget"})
        w = pd.read_csv(f"{ROOT}/results_v1/w3/class_kcurves_{e}.csv")
        w = w[w.split == "test"][["gid", "clip", "cls", "budget", "k"] + list(OURS)]
        m = w.merge(piv, on=["gid", "budget", "k"], how="inner")
        assert len(m) == len(w), f"{e}: {len(w) - len(m)} rows without a baseline result"
        m["codec"] = e
        allrows.append(m)
        L += [f"## {e} (test, {m.gid.nunique()} GOPs, {m['clip'].nunique()} clips)", ""]
        t = []
        for meth in ("search",) + ("final4", "final3", "res@hist", "bc@prev") + BASE:
            r = {"method": meth}
            for k in KS:
                r[f"k{k}"] = m[m.k == k][meth].mean()
            t.append(r)
        L += ["Mean score by k:", "", pd.DataFrame(t).round(3).to_markdown(index=False), ""]
        u = x.groupby(["method", "k"]).agg(use=("use", "mean"), over_eps=("over", "mean"),
                                           mean_over_pct=("over_pct", "mean")).reset_index()
        u = u[u.method == "abr_vbv"].drop(columns="method")
        u["over_eps"] *= 100
        L += ["ABR+VBV budget use / % of episodes over / mean % over:", "", u.round(3).to_markdown(index=False), ""]
        t = []
        for meth in ("final4", "res@hist", "bc@prev"):
            r = {"method - abr_vbv": meth}
            for k in KS:
                z = m[m.k == k]
                r[f"k{k}"] = ci(boot(z[meth] - z.abr_vbv, z["clip"]))
            t.append(r)
        L += ["Paired difference vs ABR+VBV (positive = better than the encoder's own rate control):", "",
              pd.DataFrame(t).to_markdown(index=False), ""]
    pd.concat(allrows, ignore_index=True).to_csv(f"{OUT}/abr_dpsnr.csv", index=False)
    open(f"{OUT}/abr_dpsnr.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
