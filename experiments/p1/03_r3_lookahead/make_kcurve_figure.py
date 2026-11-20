"""make_kcurve_figure.py: figure of BC, R3 and R2c across lookahead on val, one row per encoder (x264, x265), styled like figure 2 of Aayush's
report pack (p2_data/report_pack/scripts/make_figures.py: palette, markers, symlog k axis).

Left panel: mean score vs k for final4, BC alone (R3's 20k checkpoint), R3, R2c and shift-only (R2c's 20k checkpoint),
with the best constant QP in hindsight as a reference line (the mean score of the best single constant QP per GOP
chosen in hindsight; the same reference as in Aayush's figure 2). Right panel: paired differences with 95 % clip-bootstrap
CIs: R3 - final4, BC - final4, R3 - BC (what PPO adds over its BC start), R2c - final4, R3 - R2c (series side by
side, grouped on each k tick). Points that rest on one seed (k2 and k10;
R2c at k5) are hollow, with a "hollow = 1 seed" legend entry; all others average seeds 3-5 per episode.
Inputs (no new runs): results/r3_kcurve/rows_final.parquet and rows_final_x265.parquet (score_final_capped.py [--enc
x265]: one PSNR cap everywhere, capped curves; x265 k2 / k5 = Aayush's runs), results/baselines_val/rows_scored_cap.parquet (02, for the best constant QP in hindsight).
Outputs: results/r3_kcurve/fig_val_kcurve_bc_r3_r2c.png (both panels), fig_val_kcurve_scores[_x265].png (left panel only,
for slides, per encoder), fig_val_kcurve_report.png (the two score panels in one row, for the final report) and
fig_val_kcurve_bc_r3_r2c.csv (every plotted number).
Run (Aayush's ee599 env: pandas, pyarrow, matplotlib; seconds): python -I make_kcurve_figure.py
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.transforms import offset_copy  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_final_capped import boot  # noqa: E402  (same clip bootstrap as the final table)

R = "/scratch1/ahhanagu/ee599/results"
OUT = f"{R}/r3_kcurve/fig_val_kcurve_bc_r3_r2c"
ENCS = ("x264", "x265")
SLIDE = {"x264": f"{R}/r3_kcurve/fig_val_kcurve_scores.png", "x265": f"{R}/r3_kcurve/fig_val_kcurve_scores_x265.png"}
REPORT_FIG = f"{R}/r3_kcurve/fig_val_kcurve_report.png"   # one row: x264 | x265 score panels (final report)
KS = (0, 2, 5, 10, 29)

# palette and rcParams copied from p2_data/report_pack/scripts/make_figures.py (figure 2 look)
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
LIGHT = "#9b9a95"
C4 = "#7a4fd0"                          # extra series (R3 - BC): not in the report-pack palette
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "axes.edgecolor": INK2,
    "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "font.size": 9.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "axes.titlesize": 10.5,
    "axes.titleweight": "bold", "lines.linewidth": 2})
# figure 2 styles (the controller = final4, R3, BC alone); legends say "the controller"; R2c = slot 3 with its own marker, shift-only = light neutral
STYLE = {"final4": (INK2, "s", "-"), "BC": (C2, "^", "--"), "R3": (C1, "o", "-"),
         "R2c": (C3, "P", "-"), "shift-only": (LIGHT, "x", ":")}
LABEL = {"final4": "the controller", "BC": "BC alone (R3's start)", "R3": "R3 (BC start + PPO)",
         "R2c": "R2c (PPO, standard start)", "shift-only": "the controller + shift + cap (R2c's start)"}
DIFFS = [("R3 − controller", "R3", "final4", C1, "o"), ("BC − controller", "BC", "final4", C2, "^"),
         ("R3 − BC", "R3", "BC", C4, "v"), ("R2c − controller", "R2c", "final4", C3, "P"),
         ("R3 − R2c", "R3", "R2c", INK, "D")]
OFFSET = 2.5                            # points between neighbouring series at one k (5 series: -5 .. +5)


def main():
    b = pd.read_parquet(f"{R}/baselines_val/rows_scored_cap.parquet")
    hollow = Line2D([], [], ls="none", marker="o", ms=6, mfc=SURF, mec=INK2, mew=1.6, label="hollow = 1 seed")
    rows = []

    def axis_k(ax):
        ax.set_xscale("symlog", linthresh=2)
        ax.set_xticks(KS)
        ax.set_xticklabels([str(k) for k in KS])
        ax.set_xlabel("lookahead k (frames)")
        ax.set_xlim(-0.6, 40)

    def load(enc):                        # rows of score_final_capped.py (--enc x265 adds Aayush's k2/k5 runs)
        d = pd.read_parquet(f"{R}/r3_kcurve/rows_final{'' if enc == 'x264' else '_' + enc}.parquet")
        d = d[~d.hole]
        seeds = d[d.method != "final4"].groupby(["method", "k"]).seed.nunique()
        cqp = b[(b.enc == enc) & (b.method == "CQP best (hindsight)") & ~b.hole].score.mean()

        def ep(m, k):                     # seeds averaged per episode
            x = d[(d.method == m) & (d.k == k)]
            return x.groupby(["gid", "level", "clip"]).score.mean()

        def one_seed(m, k):
            return m != "final4" and seeds.get((m, k), 0) == 1
        return ep, one_seed, seeds, cqp

    def draw_left(axl, enc, record):      # mean score vs k (2-panel figure and the slide version)
        ep, one_seed, seeds, cqp = load(enc)
        for m, (col, mk, ls) in STYLE.items():
            pts = [(k, ep(m, k).mean(), one_seed(m, k)) for k in KS if len(ep(m, k))]
            if not pts:
                continue
            x, y, single = zip(*pts)
            axl.plot(x, y, ls=ls, color=col, lw=1.6 if m == "shift-only" else 2, zorder=2)
            for k, v, s in pts:
                axl.plot(k, v, marker=mk, ms=6.5, color=col, mec=col, mew=1.8, mfc=SURF if s else col, ls="none",
                         zorder=3)
                if record:
                    rows.append({"enc": enc, "panel": "score", "series": m, "k": k, "value": v, "lo": "", "hi": "",
                                 "seeds": int(seeds.get((m, k), 0)) if m != "final4" else "", "one_seed": s})
            axl.plot([], [], ls=ls, color=col, marker=mk, ms=6, mfc=col, mec=col, mew=1.8, label=LABEL[m])
        axl.axhline(cqp, color=INK2, lw=1, ls=(0, (2, 2)))
        axl.text(29, cqp - 0.012, "best constant QP in hindsight", ha="right", va="top", fontsize=7.5, color=INK2)
        axl.set_ylabel("mean score (dB)")
        axl.set_title(f"{enc}, val: score vs lookahead", loc="left")
        h, lab = axl.get_legend_handles_labels()
        if enc == "x264":                 # x265 has no single-seed points
            h, lab = h + [hollow], lab + [hollow.get_label()]
        axl.legend(h, lab, loc="lower right", fontsize=7.5)
        axis_k(axl)

    def draw_right(axr, fig, enc):        # paired differences with clip-bootstrap CIs, series grouped on each k
        ep, one_seed, seeds, cqp = load(enc)
        off = {t[0]: OFFSET * (i - (len(DIFFS) - 1) / 2) for i, t in enumerate(DIFFS)}
        ends = []                         # CI ends: offset artists are not autoscaled, so set the y range from these
        for lab, a, bb, col, mk in DIFFS:
            tr = offset_copy(axr.transData, fig=fig, x=off[lab], y=0, units="points")
            pts = []
            for k in KS:
                ea, eb = ep(a, k), ep(bb, k)
                if not len(ea) or not len(eb):
                    continue
                j = pd.concat([ea.rename("a"), eb.rename("b")], axis=1, join="inner").reset_index()
                v, lo, hi = boot((j.a - j.b).to_numpy(), j["clip"].to_numpy())
                s = one_seed(a, k) or one_seed(bb, k)
                pts.append((k, v, lo, hi, s))
                ends += [lo, hi]
                rows.append({"enc": enc, "panel": "difference", "series": lab, "k": k, "value": v, "lo": lo, "hi": hi,
                             "seeds": "", "one_seed": s})
            if not pts:
                continue
            x, y = [p[0] for p in pts], [p[1] for p in pts]
            axr.plot(x, y, color=col, lw=1.2, alpha=0.55, zorder=2, transform=tr)
            for xk, v, lo, hi, s in pts:
                axr.plot([xk, xk], [lo, hi], color=col, lw=1.3, solid_capstyle="round", zorder=2, transform=tr)
                axr.plot(xk, v, marker=mk, ms=5, color=col, mec=col, mew=1.4, mfc=SURF if s else col, ls="none",
                         zorder=3, transform=tr)
            axr.plot([], [], color=col, marker=mk, ms=5, mfc=col, mec=col, label=lab)
        axr.axhline(0, color=INK2, lw=1, zorder=1)
        pad = 0.05 * (max(ends) - min(ends))
        axr.set_ylim(min(ends) - pad, max(ends) + pad)
        axr.set_ylabel("dB (paired difference)")
        axr.set_title(f"{enc}, val: paired differences", loc="left")
        h, lab = axr.get_legend_handles_labels()
        if enc == "x264":
            h, lab = h + [hollow], lab + [hollow.get_label()]
        axr.legend(h, lab, loc="lower right", fontsize=7.5)
        axis_k(axr)

    # ---- both encoders, two panels each
    fig, axs = plt.subplots(2, 2, figsize=(10.4, 8.4))
    for row, enc in zip(axs, ENCS):
        draw_left(row[0], enc, record=True)
        draw_right(row[1], fig, enc)
    fig.text(0.01, 0.01, "Val, level-24 hole excluded, seeds 3-5 averaged per episode, one PSNR cap everywhere; bars: 95 % clip "
             "bootstrap; right panels: series side by side at each k.\nBC = R3's 20k checkpoint (the imitation start); R2c = "
             "R3's training without the BC start. Dotted line: best single constant QP per GOP in hindsight (as in the report "
             "pack's figure 2).\nx264: hollow = one seed (R3 / BC at k2, k10; R2c at k5). x265: k0 / k29 my runs; k2 / k5 "
             "Aayush's existing runs (R3 and BC alone, seeds 3-5); no R2c or k10 for x265.", fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    fig.savefig(f"{OUT}.png", dpi=180)

    # ---- left panel alone, for slides (one per encoder)
    notes = {"x264": "x264, val, hole excluded, seeds 3-5 averaged; hollow = one seed. One PSNR cap everywhere.\n"
                     "BC = R3's start (imitation); R2c = PPO from the standard start. Dotted: best constant QP per GOP in hindsight.",
             "x265": "x265, val, hole excluded, seeds 3-5 averaged. One PSNR cap everywhere. k2 / k5: Aayush's runs.\n"
                     "BC = R3's start (imitation). Dotted: best constant QP per GOP in hindsight."}
    for enc in ENCS:
        fs, ax1 = plt.subplots(figsize=(5.6, 4.3))
        draw_left(ax1, enc, record=False)
        fs.text(0.01, 0.01, notes[enc], fontsize=6.8, color=INK2)
        fs.tight_layout(rect=(0, 0.09, 1, 1))
        fs.savefig(SLIDE[enc], dpi=180)
    # ---- report version: the two score panels side by side (the paired differences are in the report's table)
    fr, axs2 = plt.subplots(1, 2, figsize=(10.4, 3.7))
    for ax, enc in zip(axs2, ENCS):
        draw_left(ax, enc, record=False)
    fr.tight_layout()                    # no footer: the report caption carries the notes
    fr.savefig(REPORT_FIG, dpi=180)
    pd.DataFrame(rows).to_csv(f"{OUT}.csv", index=False, float_format="%.4f")
    print(f"-> {OUT}.png, {', '.join(SLIDE.values())}, {REPORT_FIG}, {OUT}.csv")


if __name__ == "__main__":
    main()
