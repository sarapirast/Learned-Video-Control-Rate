"""Figures for the 3-page report, from data_*.json. Categorical slots 1-4 of the reference palette, plus markers."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H = "/scratch1/pbanga/ee599/paper/report3/"
D = {k: json.load(open(f"{H}data_{k}.json")) for k in ("x265_2", "x264_2", "x265_5", "x264_5")}
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID, REF = "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
plt.rcParams.update({"font.family": "serif", "font.size": 7.5, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.6, "lines.linewidth": 1.4,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False})

# Fig 1: score per budget QP, k=5, both encoders (5-budget runs)
B = [26, 30, 34, 38, 42]
S = [("bc fixed:5", "BC (imitation)", BLUE, "o"), ("cql_ppo fixed:5", "CQL$\\to$PPO", ORANGE, "s"),
     ("lagr fixed:5", "Lagrangian", AQUA, "^"), ("pid fixed:5", "PID-Lagrangian", YELLOW, "D")]
fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.75), sharey=True)
for ax, (key, name) in zip(axs, (("x265_5", "x265"), ("x264_5", "x264"))):
    d = D[key]
    ax.plot(B, [d["hindsight search"]["b"][str(b)][0] for b in B], color=REF, ls="--", lw=1.0)
    ax.text(42, d["hindsight search"]["b"]["42"][0] - 0.9, "hindsight\nsearch", ha="right", va="top", color=INK2, fontsize=6.5)
    for m, lab, c, mk in S:
        ax.plot(B, [d[m]["b"][str(b)][0] for b in B], color=c, marker=mk, ms=3.2, label=lab,
                markeredgecolor="white", markeredgewidth=0.5)
    ax.axhline(0, color=INK2, lw=0.5)
    ax.set_title(name, fontsize=8, color=INK, pad=2)
    ax.set_xticks(B); ax.set_xlabel("budget QP")
    ax.grid(axis="y", color=GRID, lw=0.5); ax.set_ylim(-1, 12)
axs[0].set_ylabel("score (k = 5)")

h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=4, fontsize=6.2, bbox_to_anchor=(0.53, 1.02), handlelength=1.3, columnspacing=0.6, handletextpad=0.3)
fig.tight_layout(rect=(0, 0, 1, 0.9), w_pad=0.6)
fig.savefig(H + "fig_budget.pdf"); plt.close(fig)

# Fig 2: lookahead curve, CQL->PPO, mean over QP 30 and 38 (the cases both trainings share)
K = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 29]
X = list(range(len(K)))
fig, ax = plt.subplots(figsize=(3.45, 1.7))
for codec, c, mk in (("x265", BLUE, "o"), ("x264", ORANGE, "s")):
    for nb, ls, alpha, lab in (("2", "--", 0.5, "trained on 2 budgets"), ("5", "-", 1.0, "trained on 5 budgets")):
        d = D[f"{codec}_{nb}"]
        y = [(d[f"cql_ppo fixed:{k}"]["b"]["30"][0] + d[f"cql_ppo fixed:{k}"]["b"]["38"][0]) / 2 for k in K]
        ax.plot(X, y, ls=ls, color=c, alpha=alpha, marker=mk, ms=2.8, markeredgecolor="white",
                markeredgewidth=0.4, label=f"{codec}, {lab}")
ax.axhline(0, color=INK2, lw=0.5)
ax.set_xticks(X); ax.set_xticklabels([str(k) for k in K])
ax.set_xlabel("lookahead k (future frames visible; uneven spacing)"); ax.set_ylabel("score (CQL$\\to$PPO)")
ax.grid(axis="y", color=GRID, lw=0.5)
ax.legend(ncol=2, fontsize=6.0, loc="lower center", handlelength=2.2, columnspacing=0.8)
ax.set_ylim(-4.2, 6)
fig.tight_layout()
fig.savefig(H + "fig_lookahead.pdf"); plt.close(fig)
print("ok")

# Fig 3: score vs over-budget share, every learner at k=5 (2-budget runs)
MAG, GREEN = "#e87ba4", "#008300"
FAM = [("Imitation", BLUE, "o", ["bc fixed:5"]),
       ("Offline RL", ORANGE, "s", ["cql fixed:5", "iql fixed:5"]),
       ("Offline$\\to$online", AQUA, "^", ["bc_ppo fixed:5", "cql_ppo fixed:5", "ensemble fixed:5"]),
       ("Online, scratch", YELLOW, "D", ["ppo fixed:5", "a2c fixed:5", "dqn fixed:5"]),
       ("Constrained RL", MAG, "P", ["lagr fixed:5", "pid fixed:5"]),
       ("Model-based", GREEN, "X", ["mpc fixed:5", "mb_ppo fixed:5"])]
NAME = {"bc fixed:5": "BC", "cql fixed:5": "CQL", "iql fixed:5": "IQL", "bc_ppo fixed:5": "BC$\\to$PPO",
        "cql_ppo fixed:5": "CQL$\\to$PPO", "ensemble fixed:5": "ensemble", "ppo fixed:5": "PPO", "a2c fixed:5": "A2C",
        "dqn fixed:5": "DQN", "lagr fixed:5": "Lagrangian", "pid fixed:5": "PID", "mpc fixed:5": "MPC", "mb_ppo fixed:5": "model-based"}
OFF = {("x265", "lagr fixed:5"): (-2, 5, "left"), ("x265", "pid fixed:5"): (3, -8, "left"),
       ("x265", "bc_ppo fixed:5"): (-4, -3, "right"), ("x265", "cql_ppo fixed:5"): (4, 1, "left"),
       ("x265", "mpc fixed:5"): (-3, -8, "right"), ("x265", "a2c fixed:5"): (2, -9, "left"),
       ("x265", "mb_ppo fixed:5"): (3, 3, "left"),
       ("x264", "pid fixed:5"): (-3, 5, "right"), ("x264", "lagr fixed:5"): (5, 3, "left"),
       ("x264", "bc_ppo fixed:5"): (2, -9, "left"), ("x264", "mb_ppo fixed:5"): (-3, 4, "right"),
       ("x264", "a2c fixed:5"): (4, -3, "left"), ("x264", "dqn fixed:5"): (-3, -9, "right")}
fig, axs = plt.subplots(1, 2, figsize=(7.1, 1.85), sharey=True)
for ax, (key, name) in zip(axs, (("x265_2", "x265"), ("x264_2", "x264"))):
    d = D[key]
    for fam, c, mk, ms in FAM:
        xs = [d[m]["all"][2] for m in ms]; ys = [d[m]["all"][0] for m in ms]
        ax.scatter(xs, ys, color=c, marker=mk, s=26, edgecolor="white", linewidth=0.6, label=fam, zorder=3)
        for m, x, y in zip(ms, xs, ys):
            dx, dy, ha = OFF.get((name, m), (3, 2, "left"))
            ax.annotate(NAME[m], (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=5.8, color=INK2, ha=ha)
    for m, lab in (("la_rule k=5", "hand rule"), ("hindsight search", "search")):
        x, y = d[m]["all"][2], d[m]["all"][0]
        ax.scatter([x], [y], color=REF, marker="*", s=40, zorder=3)
        ax.annotate(lab, (x, y), xytext=(4, -2), textcoords="offset points", fontsize=5.8, color=INK2)
    ax.axhline(0, color=INK2, lw=0.5)
    ax.set_title(name, fontsize=8, color=INK, pad=2)
    ax.set_xlabel("share of test cases more than 1 % over budget (%)")
    ax.grid(color=GRID, lw=0.5); ax.set_xlim(-1, 32); ax.set_ylim(-5, 12)
axs[0].set_ylabel("score (k = 5)")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="center right", fontsize=6.5, handletextpad=0.2, bbox_to_anchor=(1.0, 0.55))
fig.tight_layout(rect=(0, 0, 0.86, 1), w_pad=0.8)
fig.savefig(H + "fig_reliability.pdf"); plt.close(fig)
print("ok3")
