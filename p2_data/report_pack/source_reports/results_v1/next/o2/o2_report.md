# o[2] ablation, eval only (exp_next/o2/o2_report.py)

o[2] = (budget level != 24): clip-level hindsight under clip-mean budgets. Masked = the same trained policy re-run on val with o[2] = 0 (unmasked re-run reproduced the stored rows 8/8 per group and encoder). Masked - stored, paired, seeds averaged, 95% clip bootstrap ('*' excludes 0), hole excluded. A drop means the policy uses o[2] at evaluation; it cannot show whether having o[2] in training changed what was learned (e.g. the critic's values) -- BC / R3 trained without o[2] answer that. Single cells with a CI just touching 0 are not read (3 groups x 2 arms x several breakdowns).

Arms: zero = o[2] forced to 0 (tells the policy every GOP is level 24: measures reliance on the bit, not what a deployed policy sees); standin = o[2] = 1 if final4's frame-0 planning QP >= 27 else 0 (causal; agrees with the true bit on 88% of val episodes). Reading: zero drops and standin recovers most -> the bit can be approximated causally, a caveat suffices; both drop -> earlier learner numbers overstate a causal policy; zero unchanged -> no issue.

| group | arm | enc | k | n | arm - stored | L24 | L30 | L36 | L42 | use masked / stored | episodes with identical QPs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L540 | standin | x264 | 0 | 548 | +0.005 [-0.002, +0.012] | -0.004 | +0.008 | +0.007 | +0.007 | 0.984 / 0.984 | 84% |
| L540 | standin | x264 | 5 | 548 | -0.005 [-0.011, -0.001] * | -0.002 | -0.010 | -0.007 | +0.000 | 1.003 / 1.002 | 94% |
| L540 | standin | x265 | 0 | 550 | -0.020 [-0.045, -0.002] * | -0.020 | -0.029 | -0.019 | -0.011 | 0.970 / 0.968 | 84% |
| L540 | standin | x265 | 5 | 550 | -0.001 [-0.005, +0.003] | -0.006 | +0.003 | -0.002 | -0.000 | 0.992 / 0.992 | 93% |
| L540 | zero | x264 | 0 | 548 | +0.003 [-0.013, +0.022] | +0.000 | -0.020 | +0.057 | -0.023 | 0.987 / 0.984 | 24% |
| L540 | zero | x264 | 5 | 548 | -0.045 [-0.114, +0.006] | +0.000 | +0.026 | +0.002 | -0.202 | 1.017 / 1.002 | 24% |
| L540 | zero | x265 | 0 | 550 | +0.037 [-0.029, +0.087] | +0.000 | +0.069 | +0.050 | +0.027 | 0.987 / 0.968 | 24% |
| L540 | zero | x265 | 5 | 550 | +0.030 [-0.010, +0.065] | +0.000 | +0.029 | +0.057 | +0.032 | 1.004 / 0.992 | 24% |
| R1 | standin | x264 | 0 | 548 | -0.003 [-0.007, +0.001] | -0.008 | -0.003 | -0.001 | +0.001 | 0.980 / 0.980 | 86% |
| R1 | standin | x264 | 5 | 548 | -0.002 [-0.009, +0.004] | -0.002 | -0.000 | -0.006 | +0.000 | 0.999 / 0.999 | 94% |
| R1 | standin | x265 | 0 | 550 | -0.002 [-0.004, +0.001] | -0.007 | +0.002 | -0.001 | -0.001 | 0.975 / 0.975 | 84% |
| R1 | standin | x265 | 5 | 550 | -0.000 [-0.002, +0.001] | -0.002 | -0.000 | +0.000 | +0.000 | 0.984 / 0.984 | 93% |
| R1 | zero | x264 | 0 | 548 | +0.006 [-0.004, +0.018] | -0.000 | -0.004 | +0.008 | +0.020 | 0.985 / 0.980 | 28% |
| R1 | zero | x264 | 5 | 548 | -0.004 [-0.021, +0.012] | +0.000 | -0.003 | -0.005 | -0.009 | 1.002 / 0.999 | 24% |
| R1 | zero | x265 | 0 | 550 | +0.009 [-0.006, +0.018] | -0.000 | +0.006 | +0.021 | +0.006 | 0.976 / 0.975 | 30% |
| R1 | zero | x265 | 5 | 550 | -0.001 [-0.007, +0.005] | +0.000 | -0.002 | -0.006 | +0.006 | 0.986 / 0.984 | 24% |
| R2 | standin | x264 | 0 | 548 | +0.000 [-0.006, +0.008] | -0.009 | +0.016 | -0.006 | -0.000 | 0.987 / 0.987 | 84% |
| R2 | standin | x264 | 5 | 548 | +0.001 [-0.002, +0.006] | -0.003 | +0.008 | -0.001 | +0.000 | 0.998 / 0.998 | 94% |
| R2 | standin | x265 | 0 | 550 | -0.000 [-0.003, +0.003] | -0.003 | -0.002 | +0.003 | -0.000 | 0.959 / 0.959 | 84% |
| R2 | standin | x265 | 5 | 550 | -0.001 [-0.004, +0.000] | +0.002 | -0.006 | -0.001 | +0.000 | 0.992 / 0.992 | 93% |
| R2 | zero | x264 | 0 | 548 | +0.012 [-0.000, +0.024] | +0.000 | +0.046 | +0.015 | -0.014 | 0.990 / 0.987 | 25% |
| R2 | zero | x264 | 5 | 548 | +0.003 [-0.006, +0.013] | +0.000 | +0.012 | +0.006 | -0.005 | 0.999 / 0.998 | 24% |
| R2 | zero | x265 | 0 | 550 | +0.007 [-0.004, +0.019] | +0.000 | +0.014 | +0.002 | +0.013 | 0.961 / 0.959 | 25% |
| R2 | zero | x265 | 5 | 550 | -0.001 [-0.010, +0.007] | +0.000 | -0.018 | -0.003 | +0.018 | 0.992 / 0.992 | 25% |

Pooled over k and encoders: L540 standin -0.005 [-0.013, +0.000]; L540 zero +0.006 [-0.028, +0.032]; R1 standin -0.002 [-0.004, +0.001]; R1 zero +0.002 [-0.006, +0.012]; R2 standin -0.000 [-0.002, +0.003]; R2 zero +0.005 [+0.000, +0.011] *

