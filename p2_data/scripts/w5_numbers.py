"""W5: numbers for the quality-vs-delay figure, the report section and the W4 hypothesis outcomes (docs/w4-hypotheses.md).

Reads results_v1/w3/class_kcurves_<codec>.csv (scripts/w4_class_kcurves.py: one row per split x GOP x budget x k,
one column per method, seeds averaged; score in dB = dPSNR_B - 0.17 per 1% over). No encodes.
Test split unless stated; CIs = 95% bootstrap over clips.

The hypotheses were written on 11-09 in old score points; their thresholds are converted at 1 dB = 12.5 points
(measured 11-10: 12-13 points per dB on the same episodes, tracker item 30), e.g. "1 point" = 0.08 dB.
Methods tested: controller = final4 (with history; final3 alongside), residual RL = res@hist (on final4; res on
final3 alongside).

  python -I scripts/w5_numbers.py
Out: results_v1/w5/w5_numbers.md and results_v1/w5/curve_points.csv (mean + CI per encoder x method x class x k)
"""
import os

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/w5"
KS = (0, 2, 5, 10, 29)
PTS = 12.5                      # old score points per dB
RNG = np.random.default_rng(0)
NB = 2000
METHODS = ("search", "final4", "final3", "res@hist", "res", "bc@prev", "cql_ppo@prev", "lagr_lam0.17@prev", "bc",
           "cql_ppo", "lagr")


def boot(vals, clips, n=NB):
    vals, clips = np.asarray(vals, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = np.array([np.concatenate([vals[idx[c]] for c in RNG.choice(u, len(u))]).mean() for _ in range(n)])
    return vals.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def boot_ratio(num, den, clips, n=NB):
    """mean(num) / mean(den), clips resampled."""
    num, den, clips = np.asarray(num, float), np.asarray(den, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    rs = []
    for _ in range(n):
        j = np.concatenate([idx[c] for c in RNG.choice(u, len(u))])
        rs.append(num[j].mean() / den[j].mean())
    return num.mean() / den.mean(), np.percentile(rs, 2.5), np.percentile(rs, 97.5)


def ci(t, f="+.3f"):
    m, lo, hi = t
    return f"{m:{f}} [{lo:{f}}, {hi:{f}}]"


def wide(w, m):
    """GOP x budget rows with one column per k for method m."""
    return w.pivot_table(index=["gid", "clip", "cls", "budget"], columns="k", values=m).reset_index()


def main():
    os.makedirs(OUT, exist_ok=True)
    W = {e: pd.read_csv(f"{ROOT}/results_v1/w3/class_kcurves_{e}.csv") for e in ("x264", "x265")}
    L = ["# W5 numbers: quality vs delay, and the W4 hypothesis outcomes (scripts/w5_numbers.py)", "",
         "Score in dB (dPSNR_B - 0.17 per 1% over; 0 = constant QP spending exactly the budget). Test split, flat GOPs "
         "excluded, 4 budget levels pooled, seeds averaged. CIs: 95% bootstrap over clips. Delay = k frames of "
         f"lookahead (k/30 s at 30 fps). Old-point thresholds converted at {PTS} points per dB.", ""]

    # 1. curve points (figure data)
    pts = []
    for e, w in W.items():
        for split in ("test", "val"):
            x = w[w.split == split]
            for m in [m for m in METHODS if m in x.columns]:
                for cls in ("all", "stable", "cut"):
                    y = x if cls == "all" else x[x.cls == cls]
                    for k in KS:
                        z = y[y.k == k]
                        mu, lo, hi = boot(z[m], z["clip"], n=1000)
                        pts.append({"codec": e, "split": split, "method": m, "cls": cls, "k": k, "n": len(z),
                                    "score": mu, "lo": lo, "hi": hi})
    P = pd.DataFrame(pts)
    P.to_csv(f"{OUT}/curve_points.csv", index=False)
    t = P[(P.split == "test") & (P.cls == "all")].pivot_table(index=["codec", "method"], columns="k",
                                                               values="score").round(3)
    L += ["## 1. Quality vs delay (test, all GOPs): mean score by k", "", t.reset_index().to_markdown(index=False), ""]

    # 2. hypothesis tests
    L += ["## 2. W4 hypothesis outcomes (docs/w4-hypotheses.md)", ""]
    for e, w0 in W.items():
        w = w0[w0.split == "test"]
        L += [f"### {e}", ""]
        rows = []
        for m in ("final4", "final3", "res@hist", "res"):
            p = wide(w, m)
            s = p[[0, 2, 5, 10, 29]]
            r = {"method": m,
                 "k2-k0": ci(boot(s[2] - s[0], p["clip"])), "k5-k2": ci(boot(s[5] - s[2], p["clip"])),
                 "k10-k5": ci(boot(s[10] - s[5], p["clip"])), "k29-k5": ci(boot(s[29] - s[5], p["clip"]))}
            rows.append(r)
        L += ["H1 (steep then flat; falsified if any k5 -> k10/k29 gain >= 1 point = 0.08 dB with CI excluding 0):", "",
              pd.DataFrame(rows).to_markdown(index=False), ""]
        rows = []
        for m in ("final4", "final3", "res@hist", "res"):
            p = wide(w, m)
            g = (p[5] - p[0]).to_numpy()
            cl, cs = p["clip"].to_numpy(), p.cls.to_numpy()
            u = np.unique(cl)
            idx = {c: np.flatnonzero(cl == c) for c in u}
            ds = []
            for _ in range(NB):
                j = np.concatenate([idx[c] for c in RNG.choice(u, len(u))])
                a, b = g[j][cs[j] == "cut"], g[j][cs[j] == "stable"]
                if len(a) and len(b):
                    ds.append(a.mean() - b.mean())
            d = g[cs == "cut"].mean() - g[cs == "stable"].mean()
            st, cu = p.cls == "stable", p.cls == "cut"
            rows.append({"method": m, "k5-k0 stable": ci(boot(g[st], p["clip"][st])),
                         "k5-k0 cut": ci(boot(g[cu], p["clip"][cu])),
                         "cut - stable": f"{d:+.3f} [{np.percentile(ds, 2.5):+.3f}, {np.percentile(ds, 97.5):+.3f}]",
                         "k5-k2 stable": ci(boot((p[5] - p[2])[st], p["clip"][st])),
                         "k5-k2 cut": ci(boot((p[5] - p[2])[cu], p["clip"][cu]))})
        L += ["H2 (cut GOPs gain more; predicted cut - stable k5-k0 = +1..+3 points = +0.08..+0.24 dB; stable k5-k2 "
              "within +-0.7 points = +-0.056 dB; cut k5-k2 > +0.056 dB; falsified if cut - stable CI includes 0 for "
              "the residual on both encoders):", "", pd.DataFrame(rows).to_markdown(index=False), ""]
        rows = []
        for m in ("final4", "final3", "res@hist", "res", "bc@prev", "cql_ppo@prev"):
            means = {k: w[w.k == k][m].mean() for k in KS}
            kb = max((k for k in KS if k > 0), key=lambda k: means[k])
            a = w[w.k == 0].set_index(["gid", "budget"])
            b = w[w.k == kb].set_index(["gid", "budget"]).reindex(a.index)
            rows.append({"method": m, "best k": kb, "k0": means[0], "best": means[kb], "search": a.search.mean(),
                         "gap closed (best k vs k0)": ci(boot_ratio(b[m].to_numpy() - a[m].to_numpy(),
                                                                   a.search.to_numpy() - a[m].to_numpy(),
                                                                   a["clip"].to_numpy()), ".2f")})
        L += ["H3 (gap closed = (best-k - k0) / (search - k0); predicted <= 0.2 residual, <= 0.3 controller; "
              "falsified if > 0.3):", "", pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
        rows = []
        for m in ("final4", "final3", "res@hist", "res"):
            p = wide(w, m)
            dlt = p[29] - p[5]
            tot = dlt.sum()
            share = dlt[p.cls != "stable"].sum() / tot if tot < 0 else np.nan
            rows.append({"method": m, "k29 - k5": ci(boot(dlt, p["clip"])),
                         "share of drop in cut+gradual rows": share,
                         "cut+gradual share of rows": (p.cls != "stable").mean()})
        L += ["H4 (k29 < k5, >= 60% of the drop in cut/gradual rows; falsified if residual k29 >= k5 with CI "
              "excluding negative values):", "", pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
        rows = []
        for m, base in (("res@hist", "final4"), ("res", "final3")):
            r = {"residual": m, "base": base}
            for k in KS:
                z = w[w.k == k]
                r[f"k{k}"] = ci(boot(z[m] - z[base], z["clip"]), "+.2f")
            rows.append(r)
        L += ["H5 (residual beats its controller at every k, CI > 0 at k0):", "",
              pd.DataFrame(rows).to_markdown(index=False), ""]
        rows = []
        for m in ("res@hist", "res"):
            means = {k: w[w.k == k][m].mean() for k in KS}
            kb = max((k for k in KS if k > 0), key=lambda k: means[k])
            p = wide(w, m)
            rows.append({"method": m, "best k": kb, "best k - k0": ci(boot(p[kb] - p[0], p["clip"]))})
        L += ["H6 (residual best k - k0 > 0 with CI excluding 0; predicted +0.5..+2.5 points = +0.04..+0.20 dB):",
              "", pd.DataFrame(rows).to_markdown(index=False), ""]
        rows = []
        for lv in sorted(w.budget.unique()):
            z = w[w.budget == lv]
            r = {"level": lv}
            for m, base in (("res@hist", "final4"), ("res", "final3")):
                r[f"{m} - {base}"] = ci(boot(z[m] - z[base], z["clip"]), "+.2f")
            rows.append(r)
        z = w
        rows.append({"level": "all", **{f"{m} - {base}": ci(boot(z[m] - z[base], z["clip"]), "+.2f")
                                       for m, base in (("res@hist", "final4"), ("res", "final3"))}})
        L += ["H8 (level 24 has the smallest residual - controller; falsified if 24 is the largest), all k pooled:", "",
              pd.DataFrame(rows).to_markdown(index=False), ""]

    # H7: encoder comparison of k5-k0
    rows = []
    for m in ("final4", "final3", "res@hist", "res"):
        r = {"method": m}
        for e, w0 in W.items():
            p = wide(w0[w0.split == "test"], m)
            r[f"{e} k5-k0"] = ci(boot(p[5] - p[0], p["clip"]))
        rows.append(r)
    L += ["### H7 (x265 k5-k0 larger than x264; falsified if the order flips for the residual with CIs not "
          "overlapping)", "", pd.DataFrame(rows).to_markdown(index=False), ""]

    # 3. adaptive lookahead gate (W4 plan): k2 on stable GOPs, k5 on cut/gradual GOPs (class known in hindsight)
    L += ["## 3. Adaptive-lookahead gate, hindsight bound (the W4 plan: k2 on stable stretches, k5 when a cut is "
          "visible)", "",
          "Per GOP: the stored k2 result if the GOP is stable, else the k5 result. The class is a hindsight label, "
          "so this is an upper bound for a gate that switches on a detected cut; a real gate changes the trajectory "
          "mid-GOP and needs new encodes. Mean delay = row-weighted mean k.", ""]
    rows = []
    for e, w0 in W.items():
        w = w0[w0.split == "test"]
        for m in ("final4", "res@hist"):
            p = wide(w, m)
            g = np.where(p.cls == "stable", p[2], p[5])
            rows.append({"codec": e, "method": m, "fixed k2": p[2].mean(), "fixed k5": p[5].mean(),
                         "gate": g.mean(), "gate - k5": ci(boot(g - p[5], p["clip"])),
                         "gate - k2": ci(boot(g - p[2], p["clip"])),
                         "mean delay (frames)": float(np.where(p.cls == "stable", 2, 5).mean())})
    L += [pd.DataFrame(rows).round(3).to_markdown(index=False), ""]

    # 4. value of the previous-GOP history for the controller, paired final4 - final3 by k
    rows = []
    for e, w0 in W.items():
        w = w0[w0.split == "test"]
        r = {"codec": e, "pooled": ci(boot(w.final4 - w.final3, w["clip"]))}
        for k in KS:
            z = w[w.k == k]
            r[f"k{k}"] = ci(boot(z.final4 - z.final3, z["clip"]))
        rows.append(r)
    L += ["## 4. Controller with vs without history: final4 - final3, paired (test)", "",
          pd.DataFrame(rows).to_markdown(index=False), "",
          "Test clips / GOPs after flat exclusion: " + ", ".join(
              f"{e} {w0[w0.split == 'test']['clip'].nunique()} clips / {w0[w0.split == 'test'].gid.nunique()} GOPs"
              for e, w0 in W.items()), ""]
    open(f"{OUT}/w5_numbers.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
