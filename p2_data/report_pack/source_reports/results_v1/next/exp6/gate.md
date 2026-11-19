# Exp 6 gate: per-context final4 setting, leave-one-clip-out (exp_next/exp6/gate.py)

Pre-registration: exp_next/exp6/PREREG.md. 12 final4-family history settings (hist1 + hist2, no-history control excluded), val, flat GOPs and level-24 hole excluded, project metric. Contexts: k x base-QP-estimate bin x previous-GOP ratio bin x visible-complexity bin (budget level not used: clip-level hindsight). Pick = largest clip-clustered lower bound (mean - 1 SE) on the other 15 clips if > 0, else final4.

## GATE: picked - final4, pooled: +0.027 [-0.000, +0.050] (n 5490) -> **FAIL** (>= +0.03 and CI above 0)

- x264: +0.000 [-0.023, +0.019]; non-final4 picked on 61% of episodes
- x265: +0.054 [+0.016, +0.093] *; non-final4 picked on 66% of episodes
- by k: k0 +0.031; k2 +0.004; k5 +0.043; k10 +0.056; k29 +0.001
- oracle per-cell best setting (in-sample, upper bound, not the gate): +0.109

## Each setting vs final4 (val mean, all contexts)

| setting                                      |   x264 |   x265 |
|:---------------------------------------------|-------:|-------:|
| 0.97:6.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0 | -0.048 | -0.056 |
| 0.97:6.0:1.0:4.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0 | -0.056 | -0.063 |
| 1.0:4.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0  | -0.069 |  0.009 |
| 1.0:5.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0  | -0.012 |  0.009 |
| 1.0:6.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:1.0  | -0.066 | -0.088 |
| 1.0:6.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0  |  0     |  0     |
| 1.0:6.0:1.0:4.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0  |  0.007 | -0.011 |
| 1.0:9.0:1.0:2.0:3.0:4.0:0.0:1.0:1.0:0.0:2.0  | -0.13  | -0.134 |
| 1.0:9.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:1.0  | -0.193 | -0.355 |
| 1.0:9.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0  | -0.11  | -0.263 |
| 1.0:9.0:1.0:4.0:3.0:4.0:0.0:1.0:1.0:0.0:2.0  | -0.128 | -0.143 |
| 1.0:9.0:1.0:4.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0  | -0.112 | -0.267 |

