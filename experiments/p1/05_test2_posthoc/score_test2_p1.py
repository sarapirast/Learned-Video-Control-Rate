"""score_test2_p1.py: score my R3 k0 / k29 test2 rows exactly as Aayush's p2_data/exp_next/test2/report.py scores
"secondary 10" (Scorer + paired + cmp):
  test2 GOPs = the test2 split of rcwork_t2/<enc>_resh infos.pkl (flat GOPs not in them); curves and final4 PSNR with
  the 100 dB cap from results_v1/test2/cap_fix_<enc>.pkl; final4 = results_v1/controller_real/t2final4_<enc>_test2_*;
  cut labels from data/t2/320x180/gops.csv; hole = budget above the curve maximum, excluded; seeds averaged per
  episode; R3 - final4 with a 95 % clip bootstrap. BC alone = my own BC start (each run's 20k checkpoint, evaluated
  by eval_test2_p1.py --ckpt 20000), i.e. the same BC network R3 started from: BC - final4 and R3 - BC.
x264 (PARITY): my test2 rows must equal his stored r3k{0,29}a_test2_x264.pkl rows (QPs, bits, PSNR, score), and R3 -
  final4 must reproduce his report: k0 +0.097, k29 +0.032 (point estimates exactly; CI ends can differ in the last
  digit because his bootstrap shares one random stream across all comparisons).
x265: labelled POST-HOC, NOT PRE-REGISTERED in every line it prints.
Run (Aayush's ee599 env; reads only): python -I score_test2_p1.py --enc x264|x265  -> results/test2_posthoc/summary_<enc>.md
"""
import argparse
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

os.environ["RC_METRIC"] = "dpsnr"
sys.path.insert(0, "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/pavneet_pipeline")
from rclib import metrics  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
T2, RCT, AOUT = f"{ROOT}/data/t2/320x180", "/scratch1/aayushso/rcwork_t2", f"{ROOT}/results_v1/test2"
OUT = "/scratch1/ahhanagu/ee599/results/test2_posthoc"
KEY = ["gid", "clip", "cat", "level", "cls", "capgop"]                 # = report.py
REPORTED = {("x264", 0): 0.097, ("x264", 29): 0.032}                   # report_test2.md, secondary 10


def boot(d, clips, n=2000, seed=0):                                    # = exp5/shift_report.boot, re-seeded per call
    rng = np.random.default_rng(seed)
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([d[np.concatenate([idx[c] for c in rng.choice(u, len(u))])].mean() for _ in range(n)])
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def fmt(t):
    return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" + (" *" if t[1] > 0 or t[2] < 0 else "")


class Scorer:                                                          # = report.py Scorer
    def __init__(self, enc):
        inf = pickle.load(open(f"{RCT}/{enc}_resh/results_infos/infos.pkl", "rb"))
        self.inf = {g: x for g, x in inf.items() if x["gop"]["split"] == "test2"}
        self.fix = pickle.load(open(f"{AOUT}/cap_fix_{enc}.pkl", "rb"))
        gops = pd.read_csv(f"{T2}/gops.csv")
        self.label = {f"{r.clip_id}@{r.start_frame}": r.label for r in gops.itertuples()}

    def curve(self, gid):
        cv = self.inf[gid]["curve"]
        if gid in self.fix["curves"]:
            assert len(cv["psnr"]) == len(self.fix["curves"][gid])
            return {**cv, "psnr": self.fix["curves"][gid]}
        return cv

    def row(self, method, gid, level, k, bits, psnr, seed=-1):
        x = self.inf[gid]
        cv, B = self.curve(gid), x["budget"][level]
        return {"method": method, "gid": gid, "clip": x["gop"]["clip"], "cat": x["gop"]["category"], "level": level,
                "k": k, "seed": seed, "score": float(metrics.score(bits, psnr, cv, B)), "hole": B > max(cv["bits"]),
                "capgop": gid in self.fix["curves"],
                "cls": "cut/gradual" if self.label[gid] in ("cut", "gradual") else "stable"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enc", choices=("x264", "x265"), required=True)
    enc = ap.parse_args().enc
    S, rows, L = Scorer(enc), [], []
    posthoc = enc == "x265"
    lab = "POST-HOC, NOT PRE-REGISTERED (agreed with Aayush 2026-11-19)" if posthoc else "PARITY with Aayush's secondary 10"
    d = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{ROOT}/results_v1/controller_real/t2final4_{enc}_test2_*.parquet"))
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    for r in d[d.gid.isin(S.inf)].itertuples():                       # final4 with capped PSNR, as report.py
        f = S.fix["final4"].get((r.gid, int(r.level_q0), int(r.k)))
        rows.append(S.row("final4", r.gid, int(r.level_q0), int(r.k), float(r.bits), f["psnr"] if f else float(r.psnr_yuv)))
    for k in (0, 29):                                                 # my BC start: each run's 20k checkpoint
        p = f"{OUT}/r3k{k}bc_test2_{enc}.pkl"
        if os.path.exists(p):
            for (s, kk), rr in pickle.load(open(p, "rb"))["rows"].items():
                rows += [S.row("BC start (mine)", r["gid"], r["budget"], kk, r["bits"], r["psnr"], s) for r in rr]
    for k in (0, 29):
        p = f"{OUT}/r3k{k}_test2_{enc}.pkl"
        if not os.path.exists(p):
            L.append(f"- k{k}: no test2 rows yet ({p})")
            continue
        mine = pickle.load(open(p, "rb"))["rows"]
        for (s, kk), rr in mine.items():
            rows += [S.row("R3 (mine)", r["gid"], r["budget"], kk, r["bits"], r["psnr"], s) for r in rr]
        if enc == "x264":                                              # row-level parity with his stored rows
            his = pickle.load(open(f"{AOUT}/r3k{k}a_test2_x264.pkl", "rb"))
            same = tot = 0
            for key, rr in mine.items():
                h = {(r["gid"], r["budget"]): r for r in his[key]}
                for r in rr:
                    o = h.get((r["gid"], r["budget"]))
                    tot += 1
                    same += int(o is not None and list(r["qps"]) == list(o["qps"]) and r["bits"] == o["bits"]
                                and abs(r["psnr"] - o["psnr"]) < 1e-9 and abs(r["score"] - o["score"]) < 1e-9)
            L.append(f"- PARITY rows k{k}: identical to Aayush's stored test2 rows {same}/{tot}")
    y = pd.DataFrame(rows)
    y = y[~y.hole]
    L.insert(0, f"# test2, my R3 at k0 / k29, {enc}: {lab}")
    for k in (0, 29):
        z = y[y.k == k]
        p = z.groupby(KEY + ["method"]).score.mean().unstack("method").reset_index()   # = report.py paired()
        if "R3 (mine)" not in p:
            continue
        for a_, b in (("R3 (mine)", "final4"), ("BC start (mine)", "final4"), ("R3 (mine)", "BC start (mine)")):
            if a_ not in p or b not in p:
                continue
            q = p.dropna(subset=[a_, b])
            v = boot(q[a_] - q[b], q["clip"])
            line = f"- {a_} - {b}, k{k}: {fmt(v)} (n {len(q)}, {q['clip'].nunique()} clips)"
            if a_ == "R3 (mine)" and b == "final4" and (enc, k) in REPORTED:
                line += f"   reported {REPORTED[(enc, k)]:+.3f} -> {'MATCH' if round(v[0], 3) == REPORTED[(enc, k)] else 'MISMATCH'}"
            if posthoc or a_ == "BC start (mine)" or b == "BC start (mine)":
                line += "   [post-hoc, not pre-registered]"
            L.append(line)
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/summary_{enc}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
