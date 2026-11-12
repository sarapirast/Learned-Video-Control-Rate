"""D34 follow-up: does the stream RL gain depend on how much the GOPs of a stream differ? And the gain in % bitrate.

Variation of a stream = std of log2(first-pass bits) over its 8 GOPs (how unequal the GOPs' costs are; computed from
the first pass only, which every method sees). Cuts = number of GOPs with a detected scene cut after the IDR, and the
v1 label mix (stable / cut / gradual). Gain = method score - tuned rule score at the same lookahead (test, seeds
averaged). Bitrate: the constant-QP bits the stream's own curve needs to reach each method's pooled PSNR; 'bits for
equal quality' = how many % more bits the rule would need to match the method's PSNR (over penalty not included; the
over rates are reported separately in the stream reports).

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 python tools/stream_analysis.py
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import stream_rl as S  # noqa: E402
from rclib import clipenv as CE, config as C, metrics  # noqa: E402

METHODS = ("bc_ppo", "bc_ppo_lag", "ppo")


def main():
    infos = S.load_infos()
    base = pickle.load(open(os.path.join(C.WORK, "results_stream", "baselines.pkl"), "rb"))
    tabs = {}

    def tab(g):
        if g not in tabs:
            tabs[g] = CE.gop_table(infos[g])
        return tabs[g]

    def stream_stats(st):
        fp = np.array([tab(g)["fp"] for g in st])
        cuts = sum(int(infos[g]["an"]["cut"][1:].sum() > 0) for g in st)
        labels = [infos[g]["gop"].get("label", "?") for g in st]
        return np.std(np.log2(fp)), cuts, sum(l != "stable" for l in labels)

    def eqbits(rows):
        out = []
        for r in rows:
            cur = CE.stream_curve([tab(g) for g in r["stream"]])
            out.append(float(np.exp(metrics._interp_logbits(cur, r["psnr"]))))
        return np.array(out)

    lines = [f"# Stream RL gain vs stream variation ({C.CODEC}, test)", ""]
    for L in (0, 2):
        rule_rows = base["rows"][("rule", L, "test")]
        ref = S.frame([rule_rows])
        st = {r["stream"]: stream_stats(r["stream"]) for r in rule_rows}
        ref_eq = pd.Series(eqbits(rule_rows), index=ref.index)
        for m in METHODS:
            seeds = [pickle.load(open(p, "rb"))["res"]["test"]
                     for p in sorted(glob.glob(os.path.join(C.WORK, "results_stream", f"{m}_L{L}_s*", "eval.pkl")))]
            if not seeds:
                continue
            df = S.frame(seeds)
            df["gain"] = df.score.values - ref.loc[df.index].score.values
            df["var"] = [st[k[0]][0] for k in df.index]
            df["cuts"] = [st[k[0]][1] for k in df.index]
            df["nonstable"] = [st[k[0]][2] for k in df.index]
            eq = np.mean([eqbits(s) for s in seeds], 0)
            df["bitrate"] = 100 * (eq / ref_eq.loc[df.index].values - 1)
            lines += [f"## {m}, L={L}", ""]
            # gain by variation quartile (quartiles over all test streams), split by stream kind
            q = np.quantile(df["var"], [0.25, 0.5, 0.75])
            df["vbin"] = np.digitize(df["var"], q)
            rows = []
            for b in range(4):
                for kind in ("clip", "mixed", "all"):
                    k = (df.vbin == b) & ((df.kind == kind) if kind != "all" else True)
                    if k.sum() < 12:
                        continue
                    t = S.cboot(df.gain[k].values, df.group[k].values)
                    rows.append({"variation quartile": b + 1, "range (std log2 fp)": f"{df['var'][k].min():.2f}-{df['var'][k].max():.2f}",
                                 "kind": kind, "cases": int(k.sum()), "groups": df.group[k].nunique(),
                                 "gain (dB)": f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"})
            lines += [pd.DataFrame(rows).to_markdown(index=False), ""]
            # slope of gain on variation, per kind (cluster bootstrap of the OLS slope)
            sl = []
            for kind in ("clip", "mixed"):
                d = df[df.kind == kind]
                x, y, g = d["var"].values, d.gain.values, d.group.values
                u = np.unique(g)
                rng = np.random.default_rng(0)
                bs = []
                for _ in range(2000):
                    pick = np.concatenate([np.flatnonzero(g == c) for c in rng.choice(u, len(u))])
                    bs.append(np.polyfit(x[pick], y[pick], 1)[0])
                sl.append(f"{kind}: {np.polyfit(x, y, 1)[0]:+.3f} dB per unit [{np.percentile(bs, 2.5):+.3f}, "
                          f"{np.percentile(bs, 97.5):+.3f}]")
            lines += ["Slope of gain on variation: " + "; ".join(sl), ""]
            cl = df[df.kind == "clip"]
            by_cut = cl.groupby(cl.nonstable.clip(upper=2)).gain.agg(["mean", "size"])
            lines += ["Same-clip streams by number of non-stable GOPs (0 / 1 / 2+): " + "; ".join(
                f"{int(i)}: {r['mean']:+.3f} dB (n={int(r['size'])})" for i, r in by_cut.iterrows()), ""]
            bt = S.cboot(df.bitrate.values, df.group.values)
            lines += [f"Bits the rule would need for the method's PSNR: {bt[0]:+.2f} % [{bt[1]:+.2f}, {bt[2]:+.2f}] "
                      f"(same-clip {df[df.kind == 'clip'].bitrate.mean():+.2f} %, mixed {df[df.kind == 'mixed'].bitrate.mean():+.2f} %)", ""]
            print(f"{m} L={L} done", flush=True)
    rep = os.path.join(S.REPORTS, "stream_variation_test.md")
    open(rep, "w").write("\n".join(lines))
    print("\n".join(lines))
    print("wrote", rep)


if __name__ == "__main__":
    main()
