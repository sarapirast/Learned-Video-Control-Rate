"""W5 figures: quality vs delay (lookahead k), from results_v1/w5/curve_points.csv (scripts/w5_numbers.py). No encodes.

Fig 1  w5_quality_vs_delay.{png,pdf}: test score (dB) vs k, x264 | x265, controller final4 / final3, residual
       res@hist, learners bc@prev / cql_ppo@prev; dashed = hindsight search (ceiling), 0 = constant QP at the budget.
Fig 2  w5_quality_vs_delay_by_class.{png,pdf}: same for stable vs cut GOPs (final4, final3, res@hist; the
       learners' wide k0 range is in fig 1).
Error bars: 95% bootstrap over clips. Colours: categorical slots 1-5 of the dataviz reference palette, fixed per
method across both figures.

  python -I scripts/w5_figures.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/figures"
KS = (0, 2, 5, 10, 29)
SER = {  # method -> (label, colour); colour follows the method in every panel
    "final4": ("controller + history (final4)", "#2a78d6"),
    "final3": ("controller (final3)", "#eb6834"),
    "res@hist": ("residual RL on final4", "#1baf7a"),
    "bc@prev": ("BC, prev-GOP base", "#eda100"),
    "cql_ppo@prev": ("CQL->PPO, prev-GOP base", "#e87ba4"),
}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "text.color": INK, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "white", "axes.facecolor": "white"})
XT = [f"{k}\n{round(1000 * k / 30)} ms" for k in KS]


def panel(ax, P, codec, cls, methods, title):
    d = P[(P.codec == codec) & (P.split == "test") & (P.cls == cls)]
    s = d[d.method == "search"].score.mean()
    ax.axhline(s, color=MUTED, lw=1.5, ls="--", zorder=1)
    ax.text(len(KS) - 1 + 0.25, s, f"search (ceiling) {s:+.2f}", va="bottom", ha="left", fontsize=8, color=MUTED)
    ax.axhline(0, color=MUTED, lw=0.8, zorder=1)
    ax.text(len(KS) - 1 + 0.25, 0, "constant QP at the budget", va="top", ha="left", fontsize=8, color=MUTED)
    n = len(methods)
    for i, m in enumerate(methods):
        x = d[d.method == m].set_index("k").reindex(KS)
        xs = [j + (i - (n - 1) / 2) * 0.07 for j in range(len(KS))]
        lab, col = SER[m]
        ax.errorbar(xs, x.score, yerr=[x.score - x.lo, x.hi - x.score], color=col, lw=2, marker="o", ms=5,
                    mec="white", mew=1, elinewidth=1, capsize=0, label=lab, zorder=3)
    ax.set_xticks(range(len(KS)), XT)
    ax.set_xlim(-0.3, len(KS) - 1 + 0.2)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=10, color=INK)


def main():
    os.makedirs(OUT, exist_ok=True)
    P = pd.read_csv(f"{ROOT}/results_v1/w5/curve_points.csv")
    m1 = ["final4", "final3", "res@hist", "bc@prev", "cql_ppo@prev"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, c in zip(axs, ("x264", "x265")):
        panel(ax, P, c, "all", m1, c)
    axs[0].set_ylabel("score at the budget (dB)")
    for ax in axs:
        ax.set_xlabel("lookahead k (frames; delay at 30 fps)")
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=5, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 1.0))
    fig.suptitle("Quality at the bit budget vs lookahead delay (test, 95% clip-bootstrap CIs)", y=1.07, fontsize=11)
    fig.tight_layout(rect=(0, 0, 0.88, 0.95))
    for ext in ("png", "pdf"):
        fig.savefig(f"{OUT}/w5_quality_vs_delay.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)

    m2 = ["final4", "final3", "res@hist"]
    fig, axs = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    for i, cls in enumerate(("stable", "cut")):
        for j, c in enumerate(("x264", "x265")):
            n = int(P[(P.codec == c) & (P.split == "test") & (P.cls == cls) & (P.method == "final4")
                      & (P.k == 0)].n.iloc[0])
            panel(axs[i, j], P, c, cls, m2, f"{c}, {cls} GOPs ({n} GOP x budget rows)")
        axs[i, 0].set_ylabel("score at the budget (dB)")
    for ax in axs[1]:
        ax.set_xlabel("lookahead k (frames; delay at 30 fps)")
    h, lab = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=3, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 1.0))
    fig.suptitle("Quality vs delay by GOP class (test, 95% clip-bootstrap CIs)", y=1.04, fontsize=11)
    fig.tight_layout(rect=(0, 0, 0.88, 0.97))
    for ext in ("png", "pdf"):
        fig.savefig(f"{OUT}/w5_quality_vs_delay_by_class.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("written", OUT)


if __name__ == "__main__":
    main()
