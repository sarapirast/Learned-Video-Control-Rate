"""Figures for the paper, built only from the generated reports in results/<codec>/ (no new computation).

  python paper/make_figs.py        -> paper/figs/*.pdf
"""
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "paper", "figs")
os.makedirs(OUT, exist_ok=True)
CODECS = ("x265", "x264")
# reference categorical palette, fixed order (dataviz skill references/palette.md)
S1, S2, S3, S4, S5 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
                     "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "lines.linewidth": 1.6, "pdf.fonttype": 42})


def md_tables(path):
    """All markdown tables of a report: list of (heading, list of row dicts)."""
    out, head, rows, cols = [], "", None, None
    for line in open(path).read().splitlines() + [""]:
        if line.startswith("#"):
            head = line.strip("# ")
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cols is None:
                cols, rows = cells, []
            elif not set("".join(cells)) <= set(":- "):
                rows.append(dict(zip(cols, cells)))
        elif cols is not None:
            out.append((head, rows))
            cols = None
    return out


def num(x):
    try:
        return float(str(x).rstrip("%"))
    except ValueError:
        return np.nan


def rows_by(path, key="method"):
    d = {}
    for head, rows in md_tables(path):
        for r in rows:
            if key in r:
                d.setdefault(r[key], r)
    return d


def lookahead(codec):
    t = md_tables(os.path.join(ROOT, "results", codec, "lookahead_report.md"))[0][1]
    pol = [r for r in t if r["policy"] == "CQL->PPO" and r["split"] == "test"]
    rule = [r for r in t if r["policy"] == "lookahead rule" and r["split"] == "test"]
    k = np.array([num(r["k"]) for r in pol])
    return (k, np.array([num(r["score"]) for r in pol]), np.array([num(r["ci"]) for r in pol]),
            np.array([num(r["saving"]) for r in pol]),
            np.array([num(r["k"]) for r in rule]), np.array([num(r["score"]) for r in rule]),
            np.array([num(r["saving"]) for r in rule]))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def fig_lookahead():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.5), sharey=True)
    for ax, c in zip(axes, CODECS):
        B = rows_by(os.path.join(ROOT, "results", c, "breakdown_report.md"))
        k, sc, ci, sv, kr, scr, _ = lookahead(c)
        ax.fill_between(k, sc - ci, sc + ci, color=S1, alpha=0.15, lw=0)
        ax.plot(k, sc, "-o", color=S1, ms=3.5, label="CQL$\\to$PPO (3 seeds, 95% CI)")
        ax.plot(kr, scr, "--s", color=INK2, ms=3, lw=1.2, label="Lookahead rule (hand-designed)")
        for m, col, mk, lab in (("lagr", S2, "D", "Lagrangian RL"), ("pid", S3, "^", "PID-Lagrangian RL")):
            ks = [0, 5, 10]
            ax.plot(ks, [num(B[f"{m} fixed:{kk}"]["score"]) for kk in ks], mk, color=col, ms=5, ls="none", label=lab)
        hs = num(B["hindsight search"]["score"])
        ax.axhline(hs, color=S4, lw=1.4, ls=":")
        ax.text(29, hs - 0.4, f"hindsight search {hs:.1f}", ha="right", va="top", color=INK, fontsize=7)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.text(29, 0.3, "constant QP = 0", ha="right", va="bottom", color=INK2, fontsize=7)
        ax.set_ylim(-7, 12)
        ax.set_title(c)
        ax.set_xlabel("lookahead $k$ (future frames visible)")
        ax.set_xticks([0, 2, 5, 10, 15, 20, 29])
        ax.set_ylim(-7, 12)
    axes[0].set_ylabel("score (% saving $-$ 2$\\times$% over)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.2))
    save(fig, "lookahead_score.pdf")


def fig_share():
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    for c, col, mk in (("x265", S1, "o"), ("x264", S2, "s")):
        B = rows_by(os.path.join(ROOT, "results", c, "breakdown_report.md"))
        hs = num(B["hindsight search"]["saving"])
        k, _, _, sv, _, _, _ = lookahead(c)
        ax.plot(k, 100 * sv / hs, "-" + mk, color=col, ms=3.5, label=f"{c} (search saves {hs:.1f}%)")
    ax.set_xlabel("lookahead $k$ (future frames visible)")
    ax.set_ylabel("share of search's saving (%)")
    ax.set_ylim(0, 70)
    ax.set_xticks([0, 2, 5, 10, 15, 20, 29])
    ax.legend(frameon=False, loc="lower right")
    save(fig, "share_vs_k.pdf")


def fig_constraint():
    meths = (("BC (imitation)", S5, "//"), ("CQL->PPO", S1, ""), ("Lagrangian RL", S2, ""),
             ("PID-Lagrangian RL", S3, ".."))
    ks = (0, 5, 10)
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 3.6), sharex=True)
    for j, c in enumerate(CODECS):
        T = md_tables(os.path.join(ROOT, "results", c, "constraint_report.md"))
        per_k = {int(h.split("=")[1]): {r["method"]: r for r in rows} for h, rows in T if h.startswith("k =")}
        w = 0.2
        for i, (m, col, hatch) in enumerate(meths):
            x = np.arange(len(ks)) + (i - 1.5) * w
            sc = [num(per_k[k][m]["score"]) for k in ks]
            ov = [num(per_k[k][m][">1% over"]) for k in ks]
            axes[0, j].bar(x, sc, w * 0.9, color=col, hatch=hatch, edgecolor="white", lw=0.4,
                           label=m.replace("->", "$\\to$"))
            axes[1, j].bar(x, ov, w * 0.9, color=col, hatch=hatch, edgecolor="white", lw=0.4)
        axes[0, j].set_title(c)
        axes[0, j].axhline(0, color=INK2, lw=0.8)
        axes[1, j].set_xticks(range(len(ks)), [f"k = {k}" for k in ks])
    axes[0, 0].set_ylabel("score")
    axes[1, 0].set_ylabel("cases >1% over budget (%)")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.05))
    save(fig, "constraint.pdf")


def fig_clip():
    order = [("rule (model QP) L=0", "hand rule, L=0"), ("rule (model QP) L=2", "hand rule, L=2"),
             ("bc L=0", "BC (imitation), L=0"), ("bc L=2", "BC (imitation), L=2"),
             ("best constant QP (offline)", "best constant QP (hindsight)"),
             ("ppo L=0", "PPO, L=0"), ("ppo L=2", "PPO, L=2"), ("bc_ppo L=0", "BC$\\to$PPO, L=0"),
             ("bc_ppo L=2", "BC$\\to$PPO, L=2"), ("hindsight plan (offline)", "hindsight per-GOP plan")]
    fig, ax = plt.subplots(figsize=(3.45, 3.0))
    h = 0.38
    for j, (c, col, hatch) in enumerate((("x265", S1, ""), ("x264", S2, "//"))):
        R = rows_by(os.path.join(ROOT, "results", c, "clip_report.md"))
        y = np.arange(len(order)) + (j - 0.5) * h
        v = np.array([num(R[m]["score"]) for m, _ in order])
        ax.barh(y, np.maximum(v, -25), h * 0.9, color=col, hatch=hatch, edgecolor="white", lw=0.4, label=c)
        for yy, vv in zip(y, v):
            if vv < -25:
                ax.text(0.5, yy, f"{vv:.1f} (bar clipped)", va="center", ha="left", fontsize=6, color=INK)
    ax.text(0.5, order.index(("best constant QP (offline)", "best constant QP (hindsight)")), "0 (reference)",
            va="center", ha="left", fontsize=6, color=INK)
    ax.set_yticks(range(len(order)), [lab for _, lab in order])
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlim(-25, 15)
    ax.set_xlabel("score (% saving at equal pooled PSNR $-$ 2$\\times$% over)")
    ax.legend(frameon=False, loc="lower left")
    save(fig, "multigop.pdf")


def fig_ownrc():
    labels = [("own abr_vbv", "own ABR + VBV"), ("own abr", "own ABR"), ("own 2pass", "own 2-pass"),
              ("own 2pass +AQ", "own 2-pass + AQ"), ("constant QP", "constant QP"),
              ("la_rule k=5", "lookahead rule, k=5"), ("bc fixed:5", "BC, k=5"),
              ("cql_ppo fixed:5", "CQL$\\to$PPO, k=5"), ("lagr fixed:5", "Lagrangian RL, k=5"),
              ("hindsight search", "hindsight search")]
    fig, ax = plt.subplots(figsize=(3.45, 2.9))
    h = 0.38
    for j, (c, col, hatch) in enumerate((("x265", S1, ""), ("x264", S2, "//"))):
        B = rows_by(os.path.join(ROOT, "results", c, "breakdown_report.md"))
        y = np.arange(len(labels)) + (j - 0.5) * h
        ax.barh(y, [num(B[m]["saving"]) for m, _ in labels], h * 0.9, color=col, hatch=hatch, edgecolor="white",
                lw=0.4, label=c)
    ax.set_yticks(range(len(labels)), [lab for _, lab in labels])
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel("bits saved at equal PSNR vs constant QP (%)")
    ax.legend(frameon=False, loc="lower left")
    save(fig, "ownrc.pdf")


if __name__ == "__main__":
    fig_lookahead()
    fig_share()
    fig_constraint()
    fig_clip()
    fig_ownrc()
