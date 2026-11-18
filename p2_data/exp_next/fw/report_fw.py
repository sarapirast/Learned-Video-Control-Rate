"""Final-week items 1, 3, 4 (EXPLORATORY, val; rules in exp_next/fw/PLAN.md). Stored rows only, 100 dB PSNR cap,
level-24 hole excluded, seeds averaged per episode, 95 % clip bootstrap ('*' excludes 0).

Item 1: R3 / BC alone / final4 across k (0, 2, 5). R3 k5 = the F models (seeds 3-5, 180k checkpoint); R3 k2 = the new
        k2 runs (seeds 3-5, 180k); R3 k0 is Ahhana's (not here). BC alone = R3's initial actor deployed on final4 +
        mean[t] + bit cap (exp_next/exp5/bc_eval.py): k0 seeds 0-2 (existing classifiers), k2 / k5 seeds 3-5.
Item 3: learning curve at k5: BC alone (step 0), the seed-3 re-run's checkpoints (20608 = end of warm-up, 40k, 60k,
        90k, 120k, 180,992), and the F runs' 60k / 180,993 / 360k for seeds 3-5; no-warm-up runs at 60k / 120k / 180k.
        Determinism: the re-run's 60k and 180,992 rows vs the F seed-3 60k and 180,993 rows.
Item 4: R3 - no-warm-up (seeds 3-5, 180k, same encodes), per encoder and pooled.

  python -I exp_next/fw/report_fw.py      -> results_v1/next/fw/report_fw_val.md, fig_kcurve.png, fig_curve.png
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/final")
import report as R  # noqa: E402  (RC_METRIC=dpsnr, Scorer, load_final4_k, dec)
from shift_report import boot, fmt  # noqa: E402

RC = "/scratch1/aayushso/rcwork_v1"
EXP5 = "/scratch1/aayushso/ee599/results_v1/next/exp5"
OUT = "/scratch1/aayushso/ee599/results_v1/next/fw"
KEY = ["gid", "clip", "level", "cls"]


def rdir(enc, k, st, wu, s):
    return (f"{RC}/{enc}_resh/results_rl/res_k{k}_fixed_no-level_f4_lam0.17_st{st}k_r6_capbit_meanpooled_bcinit"
            f"{'_wu20k' if wu else ''}_s{s}")


def load(path, key):
    if not os.path.exists(path):
        return None
    return pickle.load(open(path, "rb"))["res"].get(key)


def to_rows(S, method, rr, k, seed, step=None):
    out = []
    for r in rr or []:
        x = S.row(method, r["gid"], r["budget"], k, r["bits"], r["psnr"], seed)
        x["step"] = step
        out.append(x)
    return out


def paired(d, a, b):
    p = d[d.method.isin([a, b])].groupby(KEY + ["method"]).score.mean().unstack("method").dropna().reset_index()
    return p, (p[a] - p[b])


def collect(enc):
    S = R.Scorer(enc, cap=True)
    rows = [r for r in R.load_final4_k(enc, "val", S) if r["k"] in (0, 2, 5)]
    for tag in ("k0_s012", "k25_s345"):
        f = f"{EXP5}/bc_rows_{enc}_val_{tag}.pkl"
        if os.path.exists(f):
            for r in pickle.load(open(f, "rb")):
                x = S.row("BC alone", r["gid"], r["level"], r["k"], r["bits"], r["psnr"], r["seed"])
                x["step"] = 0
                rows.append(x)
    for s in (3, 4, 5):
        d5 = rdir(enc, 5, 360, True, s)
        rows += to_rows(S, "R3", load(f"{d5}/eval_ckpt.pkl", (180993, "fixed", 5, "val")), 5, s, 180993)
        rows += to_rows(S, "R3 60k", load(f"{d5}/eval_ckpt.pkl", (60000, "fixed", 5, "val")), 5, s, 60000)
        rows += to_rows(S, "R3 360k", load(f"{d5}/eval.pkl", ("fixed", 5, "val")), 5, s, 360000)
        d2 = rdir(enc, 2, 180, True, s)
        rows += to_rows(S, "R3", load(f"{d2}/eval.pkl", ("fixed", 2, "val")), 2, s, 180992)
        rows += to_rows(S, "R3 60k", load(f"{d2}/eval_ckpt.pkl", (60000, "fixed", 2, "val")), 2, s, 60000)
        dn = rdir(enc, 5, 180, False, s)
        rows += to_rows(S, "no warm-up", load(f"{dn}/eval.pkl", ("fixed", 5, "val")), 5, s, 180992)
        for st in (60000, 120000):
            rows += to_rows(S, f"no warm-up {st // 1000}k", load(f"{dn}/eval_ckpt.pkl", (st, "fixed", 5, "val")), 5, s, st)
    dc = rdir(enc, 5, 180, True, 3)
    for st in (20608, 40000, 60000, 90000, 120000):
        rows += to_rows(S, f"re-run {st}", load(f"{dc}/eval_ckpt.pkl", (st, "fixed", 5, "val")), 5, 3, st)
    rows += to_rows(S, "re-run 180992", load(f"{dc}/eval.pkl", ("fixed", 5, "val")), 5, 3, 180992)
    d = pd.DataFrame(rows)
    return d[~d.hole]


def item1(enc, d, L, fig):
    L += [f"### Item 1, {enc}: R3 and BC alone across k (val)", "",
          "| k | R3 - final4 | BC alone - final4 | R3 - BC alone | final4 | n |", "|---|---|---|---|---|---|"]
    for k in (0, 2, 5):
        x = d[d.k == k]
        cell = {}
        for a, b in (("R3", "final4"), ("BC alone", "final4"), ("R3", "BC alone")):
            if {a, b} <= set(x.method):
                p, df = paired(x, a, b)
                cell[(a, b)] = fmt(boot(df, p["clip"]))
                if a == "R3" and b == "final4":
                    fig.append((enc, k, "R3 - final4", df.mean()))
                if a == "BC alone" and b == "final4":
                    fig.append((enc, k, "BC alone - final4", df.mean()))
        f4 = x[x.method == "final4"].score.mean()
        L.append(f"| {k} | {cell.get(('R3', 'final4'), 'not run here' if k == 0 else 'n/a')} | "
                 f"{cell.get(('BC alone', 'final4'), 'n/a')} | {cell.get(('R3', 'BC alone'), 'n/a')} | {f4:+.3f} | "
                 f"{(x.method == 'final4').sum()} |")
    L += ["", "By class (R3 - final4 / R3 - BC alone):", ""]
    for k in (2, 5):
        x = d[d.k == k]
        if not {"R3", "final4", "BC alone"} <= set(x.method):
            continue
        parts = []
        for c in ("stable", "cut/gradual"):
            y = x[x.cls == c]
            p1, d1 = paired(y, "R3", "final4")
            p2, d2 = paired(y, "R3", "BC alone")
            parts.append(f"{c} {fmt(boot(d1, p1['clip']))} / {fmt(boot(d2, p2['clip']))}")
        L.append(f"- k{k}: " + "; ".join(parts))
    L += ["", "Breakdown (per seed-episode):", "",
          pd.DataFrame([{"k": k, "method": m, **R.dec(y)} for (k, m), y in d[d.method.isin(["R3", "BC alone", "final4"])]
                        .groupby(["k", "method"])]).round(3).to_markdown(index=False), ""]


def item34(enc, d, L, curve):
    x = d[d.k == 5]
    f4 = x[x.method == "final4"].set_index(KEY).score
    L += [f"### Items 3 and 4, {enc}: learning curve and warm-up (k5, val)", ""]
    tab = []
    for m in (["BC alone"] + [f"re-run {s}" for s in (20608, 40000, 60000, 90000, 120000, 180992)]
              + ["R3 60k", "R3", "R3 360k", "no warm-up 60k", "no warm-up 120k", "no warm-up"]):
        y = x[x.method == m]
        if m == "BC alone":
            y = y[y.seed.isin([3, 4, 5])]
        if not len(y):
            continue
        p = y.groupby(KEY).score.mean()
        diff = p - f4.reindex(p.index)
        st = int(y.step.iloc[0])
        tab.append({"policy": m, "seeds": ",".join(str(s) for s in sorted(y.seed.unique())), "step": st,
                    "vs final4": fmt(boot(diff.to_numpy(), p.reset_index()["clip"])), **R.dec(y)})
        arm = "no warm-up" if m.startswith("no warm-up") else ("seed-3 re-run" if m.startswith("re-run") else
                                                               ("BC start" if m == "BC alone" else "R3 s3-5"))
        curve.append((enc, arm, st, diff.mean(), R.dec(y)["A"], R.dec(y)["mean |err| %"]))
    L += [pd.DataFrame(tab).round(3).to_markdown(index=False), ""]
    for a, b, lab in (("re-run 60000", "R3 60k", "60k"), ("re-run 180992", "R3", "180k")):
        ya = x[(x.method == a)].set_index(KEY).score
        yb = x[(x.method == b) & (x.seed == 3)].set_index(KEY).score
        if len(ya) and len(yb):
            j = ya.index.intersection(yb.index)
            L.append(f"- determinism, seed 3 at {lab}: re-run equals the F run on {(np.abs(ya[j] - yb[j]) < 1e-9).sum()}/"
                     f"{len(j)} episodes (mean diff {(ya[j] - yb[j]).mean():+.4f})")
    if {"R3", "no warm-up"} <= set(x.method):
        p, df = paired(x, "R3", "no warm-up")
        L += [f"- **Item 4: R3 - no warm-up (180k, seeds 3-5): {fmt(boot(df, p['clip']))}** (n {len(p)})",
              "- per seed: " + "; ".join(
                  f"s{s} {(x[(x.method == 'R3') & (x.seed == s)].set_index(KEY).score - x[(x.method == 'no warm-up') & (x.seed == s)].set_index(KEY).score).mean():+.3f}"
                  for s in (3, 4, 5))]
        for c in ("stable", "cut/gradual"):
            q = p[p.cls == c]
            L.append(f"- {c}: {fmt(boot(q['R3'] - q['no warm-up'], q['clip']))}")
    L.append("")


def main():
    L = ["# Final week, items 1 / 3 / 4 (EXPLORATORY, val; exp_next/fw/report_fw.py)", "",
         "Rules: exp_next/fw/PLAN.md. 100 dB cap, hole excluded, seeds averaged per episode, 95 % clip bootstrap. "
         "R3 k0 is Ahhana's sweep (not in this report).", ""]
    fig, curve, pool4 = [], [], []
    for enc in ("x264", "x265"):
        d = collect(enc)
        L += [f"## {enc}", ""]
        item1(enc, d, L, fig)
        item34(enc, d, L, curve)
        x = d[d.k == 5]
        if {"R3", "no warm-up"} <= set(x.method):
            p, df = paired(x, "R3", "no warm-up")
            p["c2"] = enc + ":" + p["clip"]
            p["diff"] = df
            pool4.append(p)
    if len(pool4) == 2:
        p = pd.concat(pool4)
        L += [f"## Item 4 pooled (both encoders): R3 - no warm-up {fmt(boot(p['diff'], p.c2))} "
              "(rule: 'the warm-up matters' only if the CI excludes 0)", ""]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report_fw_val.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        f = pd.DataFrame(fig, columns=["enc", "k", "what", "v"])
        fg, ax = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
        for i, enc in enumerate(("x264", "x265")):
            for w, mk in (("R3 - final4", "o-"), ("BC alone - final4", "s--")):
                y = f[(f.enc == enc) & (f.what == w)].sort_values("k")
                ax[i].plot(y.k, y.v, mk, label=w)
            ax[i].axhline(0, color="grey", lw=0.8)
            ax[i].set_title(f"{enc} (val, exploratory)")
            ax[i].set_xlabel("lookahead k")
        ax[0].set_ylabel("dB vs final4")
        ax[0].legend(fontsize=8)
        fg.tight_layout()
        fg.savefig(f"{OUT}/fig_kcurve.png", dpi=150)
        c = pd.DataFrame(curve, columns=["enc", "arm", "step", "v", "A", "err"])
        fg, ax = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
        for i, enc in enumerate(("x264", "x265")):
            for arm, mk in (("seed-3 re-run", "o-"), ("R3 s3-5", "s-"), ("no warm-up", "^--"), ("BC start", "kD")):
                y = c[(c.enc == enc) & (c.arm == arm)].sort_values("step")
                if arm in ("seed-3 re-run", "no warm-up"):
                    b = c[(c.enc == enc) & (c.arm == "BC start")]
                    y = pd.concat([b, y])
                ax[i].plot(y.step / 1000, y.v, mk, label=arm)
            ax[i].axhline(0, color="grey", lw=0.8)
            ax[i].axvline(20.6, color="grey", ls=":", lw=0.8)
            ax[i].set_title(f"{enc}, k5 (val, exploratory)")
            ax[i].set_xlabel("PPO steps (thousands of frame encodes)")
        ax[0].set_ylabel("dB vs final4")
        ax[0].legend(fontsize=8)
        fg.tight_layout()
        fg.savefig(f"{OUT}/fig_curve.png", dpi=150)
    except Exception as ex:  # figures are a convenience; the tables are the record
        print(f"(figures skipped: {ex})")


if __name__ == "__main__":
    main()
