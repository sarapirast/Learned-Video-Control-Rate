"""Quality vs budget reliability, v1 test, all streams, L=2: re-tuned rule B margin sweep (line) vs RL policies (points).

rule: (% over, score) for margins 0.88..1.00 -- the "rule B (retuned), all streams" test curve, L=2,
      from outputs/pid_vs_retuned_<codec>.txt (rule B re-tuned on all val streams).
points / pid_curve: (% over, score) on all test streams, 3-seed means from the stored eval rows
      (p4/models for the PID runs, pavneet_handoff artifacts for PPO and bc_ppo_lag).
The PID target sweep (2/5/10 %) is descriptive: the targets were compared on test.
"""
import matplotlib.pyplot as plt

DATA = {
    "x264": {
        "rule": ([0.9, 1.6, 2.4, 3.7, 4.6, 6.1, 8.2, 11.2, 17.2, 27.7],
                 [-0.931, -0.835, -0.742, -0.655, -0.619, -0.581, -0.552, -0.527, -0.517, -0.531]),
        "points": {"PPO": (14.8, -0.378), "bc_ppo_lag (fixed λ)": (7.4, -0.400),
                   "ppo_pid": (6.7, -0.408), "bc_ppo_pid": (5.8, -0.401)},
        "pid_curve": ([3.4, 5.8, 11.1], [-0.431, -0.401, -0.374]),
    },
    "x265": {
        "rule": ([1.0, 1.2, 2.1, 3.8, 5.0, 6.5, 8.4, 11.9, 18.3, 28.6],
                 [-0.806, -0.709, -0.621, -0.544, -0.507, -0.474, -0.447, -0.424, -0.420, -0.435]),
        "points": {"PPO": (11.8, -0.222), "bc_ppo_lag (fixed λ)": (5.4, -0.217),
                   "ppo_pid": (5.3, -0.263), "bc_ppo_pid": (4.8, -0.228)},
        "pid_curve": ([2.7, 4.8, 9.5], [-0.268, -0.228, -0.221]),
    },
}
MARGINS = [0.88, 0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99, 1.00]
STYLE = {"PPO": ("#888888", "o"), "bc_ppo_lag (fixed λ)": ("#1f77b4", "s"),
         "ppo_pid": ("#ff7f0e", "^"), "bc_ppo_pid": ("#d62728", "D")}

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, (codec, d) in zip(axes, DATA.items()):
    xs, ys = d["rule"]
    ax.plot(xs, ys, "-", color="black", lw=1.5, label="rule B, re-tuned (margin sweep)")
    for x, y, m in zip(xs, ys, MARGINS):
        ax.annotate(f"{m:.2f}", (x, y), textcoords="offset points", xytext=(4, -10), fontsize=7, color="gray")
    px, py = d["pid_curve"]
    ax.plot(px, py, "--", color="#d62728", lw=1.5, label="bc_ppo_pid, targets 2/5/10 % (descriptive)")
    for x, y, t, off in zip(px, py, ("target 2%", "target 5%", "target 10%"), ((0, -14), (-8, 0), (0, -14))):
        ax.annotate(t, (x, y), textcoords="offset points", xytext=off, fontsize=7, color="#d62728",
                    ha="right" if off[0] < 0 else "center", va="center" if off[0] < 0 else "baseline")
    for name, (x, y) in d["points"].items():
        c, mk = STYLE[name]
        ax.scatter(x, y, color=c, marker=mk, s=60, zorder=3, label=name)
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 30]); ax.set_xticklabels(["1", "2", "5", "10", "20", "30"])
    ax.set_xlabel("streams > 1% over budget (%)")
    ax.set_ylabel("score (dB, higher is better)")
    ax.set_title(f"{codec}, v1 test (all streams), lookahead 2 GOPs")
    ax.grid(alpha=0.3)
    ax.margins(y=0.08)
axes[0].legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig("figures/tradeoff_L2.png", dpi=200)
print("wrote figures/tradeoff_L2.png")