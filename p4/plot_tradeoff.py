"""Quality vs budget reliability, v1 test, L=2: rule margin sweep (line) vs RL policies (points)."""
import matplotlib.pyplot as plt

# rule: (% over, score) for margins 0.88..1.00, from rule_margin_x264/x265.txt (L=2 test lines)
# points: (% over, score) from report_pid_*_test.md and the bcpid_*.txt logs (3-seed means)
DATA = {
    "x264": {
        "rule": ([1.2, 1.7, 2.8, 4.3, 7.0, 13.2, 29.2], [-0.905, -0.813, -0.723, -0.637, -0.566, -0.517, -0.528]),
        "points": {"PPO": (15, -0.378), "bc_ppo_lag (fixed λ)": (7, -0.400),
                   "ppo_pid": (7, -0.408), "bc_ppo_pid": (5.8, -0.402)},
    },
    "x265": {
        "rule": ([0.9, 1.1, 2.1, 3.5, 6.2, 11.9, 29.4], [-0.806, -0.710, -0.622, -0.540, -0.468, -0.423, -0.433]),
        "points": {"PPO": (12, -0.222), "bc_ppo_lag (fixed λ)": (5, -0.217),
                   "ppo_pid": (5.3, -0.263), "bc_ppo_pid": (4.8, -0.228)},
    },
}
MARGINS = [0.88, 0.90, 0.92, 0.94, 0.96, 0.98, 1.00]
STYLE = {"PPO": ("#888888", "o"), "bc_ppo_lag (fixed λ)": ("#1f77b4", "s"),
         "ppo_pid": ("#ff7f0e", "^"), "bc_ppo_pid": ("#d62728", "D")}

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, (codec, d) in zip(axes, DATA.items()):
    xs, ys = d["rule"]
    ax.plot(xs, ys, "-", color="black", lw=1.5, label="remaining-budget rule (margin sweep)")
    for x, y, m in zip(xs, ys, MARGINS):
        ax.annotate(f"{m:.2f}", (x, y), textcoords="offset points", xytext=(4, -10), fontsize=7, color="gray")
    for name, (x, y) in d["points"].items():
        c, mk = STYLE[name]
        ax.scatter(x, y, color=c, marker=mk, s=60, zorder=3, label=name)
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 30]); ax.set_xticklabels(["1", "2", "5", "10", "20", "30"])
    ax.set_xlabel("streams > 1% over budget (%)")
    ax.set_ylabel("score (dB, higher is better)")
    ax.set_title(f"{codec}, v1 test, lookahead 2 GOPs")
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig("figures/tradeoff_L2.png", dpi=200)
print("wrote tradeoff_L2.png")