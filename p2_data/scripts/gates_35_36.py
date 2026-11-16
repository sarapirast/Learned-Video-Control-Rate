"""Pre-written gates for tracker items 35 (targeted residual) and 36 day 2 (BC with a shared per-frame encoder).

Input: results_v1/lfq_compare_<codec>_final4.csv (scripts/lfq_compare.py <codec> --ctrl-tag final4; one row per
episode; 'ctrl' = the frozen controller final4 on the same GOP x level x k). Seeds averaged per GOP x level x k.
Differences are paired on GOP x level x k; CIs = 95% bootstrap over clips.

Item 35: the combined rule = res_lv36-42@hist (residual RL on final4 trained on budget levels 36/42 only) at levels
36/42, final4 at levels 24/30. GATE (written before results): on VAL the combined rule beats final4 pooled over k and
levels, CI excluding 0, on at least one encoder. Also vs res@hist (residual trained on all levels) on all levels.
Item 36 gate 2: on VAL, bc_attn-kall@prev (set_attn, one BC net on k 0/2/5/10/29 pooled) beats bc@prev (per-k mlp)
pooled over k with a CI excluding 0 on BOTH encoders; bc_mlp-kall@prev is the control (pooling without the new net).

  python -I scripts/gates_35_36.py
Out: results_v1/w5/gates_35_36.md
"""
import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
KS = (0, 2, 5, 10, 29)
RNG = np.random.default_rng(0)


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    lo, hi = np.percentile(ms, 2.5), np.percentile(ms, 97.5)
    return f"{d.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]" + (" *" if lo > 0 or hi < 0 else "")


def wide(d, methods):
    g = d[d.method.isin(methods)].groupby(["method", "split", "k", "gid", "clip", "cls", "budget"], as_index=False)[
        ["score", "ctrl"]].mean()
    w = g.pivot_table(index=["split", "k", "gid", "clip", "cls", "budget"], columns="method", values="score")
    c = g.groupby(["split", "k", "gid", "clip", "cls", "budget"]).ctrl.first()
    return w.assign(final4=c).reset_index()


def main():
    L = ["# Gates for tracker 35 (targeted residual) and 36 day 2 (shared-encoder BC) (scripts/gates_35_36.py)", "",
         "Score in dB (dPSNR_B - 0.17 per 1% over). Seeds averaged per GOP x level x k; diffs paired on GOP x level "
         "x k; 95% bootstrap over clips ('*' = CI excludes 0). Source: results_v1/lfq_compare_<codec>_final4.csv.", ""]
    for e in ("x264", "x265"):
        d = pd.read_csv(f"{ROOT}/results_v1/lfq_compare_{e}_final4.csv",
                        usecols=["method", "k", "seed", "split", "gid", "clip", "cls", "budget", "score", "ctrl"])
        seeds = d.groupby("method").seed.nunique()
        L += [f"## {e}", ""]

        # ---- item 35
        w = wide(d, ["res_lv36-42@hist", "res@hist"])
        hi = w.budget.isin([36, 42])
        w["combined"] = np.where(hi, w["res_lv36-42@hist"], w.final4)
        t = []
        for split in ("val", "test"):
            x = w[w.split == split]
            for lab, a, b, m in (("combined - final4 (all levels)", "combined", "final4", None),
                                 ("combined - res@hist (all levels)", "combined", "res@hist", None),
                                 ("res_lv - final4 (levels 36/42)", "res_lv36-42@hist", "final4", (36, 42)),
                                 ("res_lv - res@hist (levels 36/42)", "res_lv36-42@hist", "res@hist", (36, 42)),
                                 ("res_lv - final4 (level 42)", "res_lv36-42@hist", "final4", (42,)),
                                 ("res_lv - final4 (levels 24/30, not trained)", "res_lv36-42@hist", "final4", (24, 30))):
                y = x if m is None else x[x.budget.isin(m)]
                r = {"split": split, "comparison": lab, "pooled k": boot(y[a] - y[b], y["clip"])}
                for k in KS:
                    z = y[y.k == k]
                    r[f"k{k}"] = f"{(z[a] - z[b]).mean():+.3f}"
                t.append(r)
        L += [f"### Item 35: targeted residual (seeds: res_lv {seeds.get('res_lv36-42@hist', 0)}, "
              f"res@hist {seeds.get('res@hist', 0)})", "", pd.DataFrame(t).to_markdown(index=False), ""]

        # ---- item 36 gate 2
        M = ["bc@prev", "bc_attn-kall@prev", "bc_mlp-kall@prev"]
        w = wide(d, M)
        t, s = [], []
        for split in ("val", "test"):
            x = w[w.split == split]
            for m in M + ["final4"]:
                r = {"split": split, "method": m, "pooled k": x[m].mean()}
                for k in KS:
                    r[f"k{k}"] = x[x.k == k][m].mean()
                s.append(r)
            for a, b in (("bc_attn-kall@prev", "bc@prev"), ("bc_mlp-kall@prev", "bc@prev"),
                         ("bc_attn-kall@prev", "bc_mlp-kall@prev"), ("bc_attn-kall@prev", "final4")):
                r = {"split": split, "comparison": f"{a} - {b}", "pooled k": boot(x[a] - x[b], x["clip"])}
                for c in ("stable", "cut"):
                    z = x[x.cls == c]
                    r[c] = boot(z[a] - z[b], z["clip"])
                for k in KS:
                    z = x[x.k == k]
                    r[f"k{k}"] = f"{(z[a] - z[b]).mean():+.3f}"
                t.append(r)
        L += [f"### Item 36 gate 2: shared-encoder BC (seeds: " +
              ", ".join(f"{m} {seeds.get(m, 0)}" for m in M) + ")", "",
              "Mean score:", "", pd.DataFrame(s).round(3).to_markdown(index=False), "",
              "Paired differences:", "", pd.DataFrame(t).to_markdown(index=False), ""]
    open(f"{ROOT}/results_v1/w5/gates_35_36.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
