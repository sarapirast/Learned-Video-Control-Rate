"""Build report_pack/figures/*.png and report_pack/tables/*.csv from the copied source reports only.

Every plotted number is parsed from a markdown report under report_pack/source_reports/ (a verbatim copy of the
workspace's results_v1/ reports), so the pack can be checked without the workspace. Each parsed number is also
written to tables/key_numbers.csv with the file and the exact source line it came from.

    python report_pack/scripts/make_figures.py          (env: numpy, pandas, matplotlib)
"""
import csv
import os
import re
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PACK, "source_reports")
FIG = os.path.join(PACK, "figures")
TAB = os.path.join(PACK, "tables")
os.makedirs(FIG, exist_ok=True)
os.makedirs(TAB, exist_ok=True)

# palette (validated reference palette, light mode): categorical slots 1-3 + neutral ink for baselines
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
ENC_C = {"x264": C1, "x265": C2}
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "axes.edgecolor": INK2,
    "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "font.size": 9.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "axes.titlesize": 10.5,
    "axes.titleweight": "bold", "lines.linewidth": 2})

TRIPLE = re.compile(r"([+-]\d+\.\d+) \[([+-]\d+\.\d+), ([+-]\d+\.\d+)\]")
LEDGER = []   # (id, value, lo, hi, file, line)


def read(rel):
    """Lines of a source report; '|err|' inside table headers is renamed 'abs err' so cells split on '|'."""
    return open(os.path.join(SRC, rel)).read().replace("|err|", "abs err").splitlines()


def block(rel, section=None):
    """Lines of one '## <section>' block (whole file if section is None)."""
    lines = read(rel)
    if section is None:
        return lines
    i = next(j for j, l in enumerate(lines) if l.strip() == f"## {section}")
    out = []
    for l in lines[i + 1:]:
        if l.startswith("## "):
            break
        out.append(l)
    return out


def tri(rel, needle, section=None, idx=0, key=None):
    """(value, lo, hi) of the idx-th 'v [lo, hi]' on the first line containing needle."""
    for l in block(rel, section):
        if needle in l:
            m = TRIPLE.findall(l)
            v = tuple(float(x) for x in m[idx])
            LEDGER.append((key or f"{rel}|{section}|{needle}|{idx}", *v, rel, l.strip()))
            return v
    raise KeyError(f"{needle!r} not found in {rel} [{section}]")


def table(rel, first_header, section=None):
    """Markdown table whose header row starts with '| first_header' -> (columns, rows of str)."""
    lines = block(rel, section)
    i = next(j for j, l in enumerate(lines) if l.startswith(f"| {first_header}"))
    cols = [c.strip() for c in lines[i].strip("|").split("|")]
    rows = []
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        rows.append([c.strip() for c in l.strip("|").split("|")])
    return cols, rows


def num(s):
    try:
        return float(s)
    except ValueError:
        return np.nan


def zero_line(ax, vertical=True):
    (ax.axvline if vertical else ax.axhline)(0, color=INK2, lw=1, zorder=1)


def forest(ax, labels, series, title, xlabel="dB (R3 minus comparator)", marker_fill=None):
    """Horizontal CI plot. series: {name: [(v, lo, hi) or None per label]}; fill[name][i] False -> hollow marker."""
    n, m = len(labels), len(series)
    off = np.linspace(-0.16, 0.16, m) if m > 1 else [0]
    for j, (name, vals) in enumerate(series.items()):
        col = ENC_C.get(name, C1)
        for i, t in enumerate(vals):
            if t is None:
                continue
            y = n - 1 - i + off[j]
            ax.plot([t[1], t[2]], [y, y], color=col, lw=2, solid_capstyle="round", zorder=2)
            filled = True if marker_fill is None else marker_fill[name][i]
            ax.plot(t[0], y, "o", ms=7, mfc=col if filled else SURF, mec=col, mew=2, zorder=3,
                    label=name if i == next(k for k, x in enumerate(vals) if x is not None) else None)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels[::-1])
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    zero_line(ax)
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc="left")


# ---------------------------------------------------------------- figure 1: primary across evaluation sets
T2, VT, R3V = "results_v1/test2/report_test2.md", "results_v1/final/report_test_cap.md", "results_v1/next/exp4/r3_report.md"
rows1 = ["v1 val: R3 gate (seeds 0-2)", "v1 test: pre-registered (seeds 3-5)", "test2, 93 new clips: pre-registered",
         "v1 test + test2 pooled (descriptive)"]
s1 = {}
for e, i in (("x264", 0), ("x265", 1)):
    s1[e] = [tri(R3V, "| R3 - final4 |", idx=i, key=f"val_R3gate_{e}"),
             tri(VT, "PRIMARY R3 (180k) - final4, k5", e, key=f"v1test_primary_{e}"),
             tri(T2, "PRIMARY R3 (180k, s3-5) - final4, k5", e, key=f"test2_primary_{e}"),
             tri(T2, f"- {e}: ", "Secondary 9, pooled v1 test + test2 (R3 - final4, k5, per encoder; descriptive)",
                 key=f"pooled_primary_{e}")]
fig, ax = plt.subplots(figsize=(7.2, 3.0))
forest(ax, rows1, s1, "R3 minus final4 at lookahead k5, by evaluation set")
ax.legend(loc="lower right")
fig.text(0.01, 0.01, "Mean dB difference per (GOP, budget level), 95% clip-bootstrap CI. Score = dPSNR_B - 0.17 x %over.",
         fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(f"{FIG}/fig1_primary_replication.png", dpi=180)
plt.close(fig)

# ---------------------------------------------------------------- figure 2: test2 k-curves
fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.5), sharey=True)
style = {"final4": (INK2, "s", "-"), "R3": (C1, "o", "-"), "R3 (Ahhana)": (C1, "D", "none"),
         "BC alone": (C2, "^", "--"), "CQL->PPO 540k": (C3, "v", "--")}
for ax, e in zip(axs, ("x264", "x265")):
    cols, rows = table(T2, "method ", e)
    ks = [int(c) for c in cols[1:]]
    tab = {r[0]: [num(x) for x in r[1:]] for r in rows}
    for meth, (col, mk, ls) in style.items():
        if meth not in tab:
            continue
        pts = [(k, v) for k, v in zip(ks, tab[meth]) if not np.isnan(v)]
        for k, v in pts:
            LEDGER.append((f"test2_kcurve_{e}_{meth}_k{k}", v, "", "", T2, f"[{e}] k-curve row '{meth}'"))
        x, y = zip(*pts)
        ax.plot(x, y, ls=ls, color=col, marker=mk, ms=6, mfc=SURF if meth == "R3 (Ahhana)" else col, mec=col,
                mew=1.8, label=meth if meth != "R3 (Ahhana)" else "R3, Ahhana's models (x264)")
    cb = tab["cqp_best (hindsight)"][-1]
    ax.axhline(cb, color=INK2, lw=1, ls=(0, (2, 2)))
    ax.text(0, cb + 0.01, "best constant QP in hindsight", ha="left", va="bottom", fontsize=7.5, color=INK2)
    ax.set_xscale("symlog", linthresh=2)
    ax.set_xticks(ks)
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_xlabel("lookahead k (frames)")
    ax.set_title(f"{e}, test2", loc="left")
axs[0].set_ylabel("mean score (dB)")
axs[0].legend(loc="lower right", fontsize=8)
fig.text(0.01, 0.01, "Hole excluded, seeds averaged. Off-scale: ABR+VBV (x264 -2.8 / -2.4, x265 -2.2 / -1.6 at k0 / k5); "
         "causal constant QP (-2.7 to -7.7).", fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(f"{FIG}/fig2_test2_kcurve.png", dpi=180)
plt.close(fig)

# ---------------------------------------------------------------- figure 3: test2 secondary comparisons
rows3 = [("vs final4 (primary)", "PRIMARY R3 (180k, s3-5) - final4, k5", 0),
         ("vs final4 + per-QP-bin shift", "R3 - final4 + shift, k5", 0),
         ("vs BC alone", "R3 - BC alone, k5", 0),
         ("vs CQL->PPO 540k", "R3 - CQL->PPO 540k, k5", 0),
         ("vs final4, stable GOPs", "Secondary 1, by class", 1),
         ("vs final4, cut/gradual GOPs", "Secondary 1, by class", 0),
         ("vs final4 at k2 (R3 trained at k2)", "R3 - final4, k2", 0),
         ("own-history R3 vs final4", "R3 own history - final4", 0)]
s3 = {e: [tri(T2, nd, e, idx=i, key=f"test2_{lab}_{e}") for lab, nd, i in rows3] for e in ("x264", "x265")}
fig, ax = plt.subplots(figsize=(7.2, 3.9))
forest(ax, [r[0] for r in rows3], s3, "test2: R3 against every comparator (k5 unless stated)")
ax.legend(loc="lower right")
fig.text(0.01, 0.01, "R3 - ABR+VBV (off-scale): x264 +2.24, x265 +1.52, both CI > 0. 95% clip-bootstrap CIs.",
         fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(f"{FIG}/fig3_test2_comparisons.png", dpi=180)
plt.close(fig)

# ---------------------------------------------------------------- figure 4: development experiments (val)
E = "results_v1/next/"
dev = [  # label, file, needle, section, idx, verdict
    ("Exp 3: residual priced at 0.17 vs 0.34", E + "exp3/report.md", "- pooled:", None, 0, "PASS"),
    ("Exp 4 R2: wider offsets + features vs R1", E + "exp4/r2_report.md", "- pooled:", None, 0, "FAIL (rule)"),
    ("Exp 2: handoff hybrid vs final4", E + "exp2/report.md", "- hybrid - final4:", None, 0, "FAIL"),
    ("Exp 5b: BC alone vs final4, x264", E + "exp5/bc_fold.md", "- k0+k5: BC - final4", "x264", 0, "FAIL"),
    ("Exp 5b: BC alone vs final4, x265", E + "exp5/bc_fold.md", "- k0+k5: BC - final4", "x265", 0, "FAIL"),
    ("Exp 5a rev4: final4 + shift vs final4, x264", E + "exp5/shift_val_rev4.md", "**x264:", None, 0, "FAIL (post-hoc)"),
    ("Exp 5a rev4: final4 + shift vs final4, x265", E + "exp5/shift_val_rev4.md", "**x265:", None, 0, "PASS (post-hoc)"),
    ("Exp 6: per-context final4 setting vs final4", E + "exp6/gate.md", "## GATE", None, 0, "FAIL (narrow)"),
    ("R3: PPO from BC actor vs final4", R3V, "| R3 - final4 |", None, 2, "PASS"),
    ("R3: effect of the BC start (R3 - R2c)", R3V, "| R3 - R2c", None, 2, "PASS"),
]
vals4, fill4, labs4 = [], [], []
for lab, f, nd, sec, i, verdict in dev:
    vals4.append(tri(f, nd, sec, idx=i, key=f"dev_{lab}"))
    fill4.append(verdict.startswith("PASS"))
    labs4.append(f"{lab}  [{verdict}]")
fig, ax = plt.subplots(figsize=(9.6, 4.6))
forest(ax, labs4, {"pooled / as labelled": vals4}, "Development experiments that led to R3 (pre-registered rules)",
       xlabel="dB (first method minus second)", marker_fill={"pooled / as labelled": fill4})
fig.text(0.01, 0.01, "Filled = met its pre-registered rule; hollow = did not. Pooled over x264 + x265 unless labelled; "
         "Exp 5b on the 8-clip train-select fold, all others on v1 val.", fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(f"{FIG}/fig4_dev_experiments.png", dpi=180)
plt.close(fig)

# ---------------------------------------------------------------- figure 5: how R3 wins (test2 decomposition, k5)
order = ["final4", "final4 + shift", "R3", "R3 own history", "CQL->PPO 540k", "BC alone"]
fig, axs = plt.subplots(2, 2, figsize=(8.4, 4.6), sharey=True)
for c, e in enumerate(("x264", "x265")):
    cols, rows = table(T2, "method ", e)   # first table = k-curve; decomposition is the one with '% over'
    lines = block(T2, e)
    i = next(j for j, l in enumerate(lines) if l.startswith("| method") and "% over" in l)
    cols = [x.strip() for x in lines[i].strip("|").split("|")]
    d = {}
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        r = [x.strip() for x in l.strip("|").split("|")]
        d[r[0]] = dict(zip(cols, r))
    meths = [m for m in order if m in d]
    for r_, (colname, xl) in enumerate((("% over", "% of episodes over budget"), ("score", "mean score (dB)"))):
        ax = axs[r_, c]
        v = [float(d[m][colname]) for m in meths]
        for m, x in zip(meths, v):
            LEDGER.append((f"test2_decomp_{e}_{m}_{colname}", x, "", "", T2, f"[{e}] decomposition row '{m}'"))
        y = np.arange(len(meths))[::-1]
        ax.barh(y, v, height=0.62, color=[C1 if m == "R3" else "#b9b8b2" for m in meths], edgecolor=SURF, lw=2)
        for yy, x in zip(y, v):
            ax.text(x, yy, f" {x:.1f}" if colname == "% over" else f" {x:+.2f} ", va="center",
                    ha="left" if x >= 0 else "right", fontsize=7.5, color=INK2)
        ax.set_yticks(y)
        ax.set_yticklabels(meths)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel(xl)
        if colname == "score":
            zero_line(ax)
            ax.set_xlim(min(v) * 1.45, 0.05)
        else:
            ax.set_xlim(0, max(v) * 1.18)
        if r_ == 0:
            ax.set_title(f"{e}, test2, k5", loc="left")
fig.tight_layout()
fig.savefig(f"{FIG}/fig5_test2_overshoot.png", dpi=180)
plt.close(fig)

# ---------------------------------------------------------------- figure 6: test2 by content category
fig, ax = plt.subplots(figsize=(7.2, 4.6))
cat = {}
for e in ("x264", "x265"):
    cols, rows = table(T2, "category", e)
    for r in rows:
        t = tuple(float(x) for x in TRIPLE.findall(r[3])[0])
        cat.setdefault(r[0], {})[e] = t
        LEDGER.append((f"test2_cat_{e}_{r[0]}", *t, T2, f"[{e}] category row '{r[0]}' (clips {r[1]})"))
names = sorted(cat, key=lambda c: -np.mean([cat[c][e][0] for e in cat[c]]))
forest(ax, names, {e: [cat[c].get(e) for c in names] for e in ("x264", "x265")},
       "test2: R3 minus final4 at k5 by content category (descriptive)")
ax.legend(loc="upper left")
fig.text(0.01, 0.01, "4-8 clips per category; CIs are wide and no per-category claim is made (PREREG).",
         fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(f"{FIG}/fig6_test2_categories.png", dpi=180)
plt.close(fig)

# ---------------------------------------------------------------- figures 7-8: existing figures, copied as made
shutil.copy(f"{SRC}/results_v1/next/fw/fig_curve.png", f"{FIG}/fig7_learning_curve_val.png")
shutil.copy(f"{SRC}/results_v1/figures/w5_quality_vs_delay.png", f"{FIG}/fig8_quality_vs_delay_v1test_pre_r3.png")

with open(f"{TAB}/key_numbers.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "value", "ci_lo", "ci_hi", "source_file", "source_line"])
    w.writerows(LEDGER)
print(f"figures -> {FIG}; {len(LEDGER)} numbers -> {TAB}/key_numbers.csv")
