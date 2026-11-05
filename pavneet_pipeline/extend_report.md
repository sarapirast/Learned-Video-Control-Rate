# Extensions on the expanded data (real x265, held-out test)

Test: 416 cases, 102 with a scene cut (70 natural, 32 spliced). Saving = % bits saved vs native x265 constant-QP at equal PSNR, each case clipped to +-50 % (the unclipped mean is shown too). Trained rows: mean of 3 seeds. Val score = validation saving - 0.1 x % GOPs over budget. Paired differences: 95 % bootstrap over cases. Reference: the k=5 CQL -> PPO policy chosen on validation in expand.py.

## x265's own rate control on the same budget

abr_la0 = 1-pass ABR, no lookahead; abr_la20 = 1-pass ABR, 20-frame lookahead; 2pass = 2-pass ABR (sees the whole GOP first); vbv = ABR with a VBV buffer of one GOP; *_default = x265's default AQ + cutree on (tools a --qpfile policy cannot use). All P-only, veryfast, same budget B per GOP.

| method | val score | test all | unclipped | scene cuts | natural | spliced | stable | GOPs >1% over | vs causal rule | vs k=5 policy |
|---|---|---|---|---|---|---|---|---|---|---|
| fixed rule, budget-fitted in hindsight (non-causal) | 3.33 | 1.68 | 1.69 | 2.40 | 1.07 | 5.31 | 1.45 | 0% | +0.60 [+0.19, +1.12] | -0.48 [-0.95, +0.04] |
| fixed rule, causal (p=0.9) | 3.01 | 1.08 | 1.05 | 1.15 | -0.65 | 5.10 | 1.06 | 0% | +0.00 [+0.00, +0.00] | -1.08 [-1.60, -0.59] |
| k=5 policy (reference) | 2.83 | 2.16 | 1.79 | 3.87 | 2.02 | 7.90 | 1.60 | 6% | +1.08 [+0.60, +1.64] | +0.00 [+0.00, +0.00] |
| x265 abr_la0 | -16.25 | -13.42 | -14.79 | -5.29 | -2.90 | -10.45 | -16.04 | 35% | -14.53 [-16.43, -12.67] | -15.63 [-17.45, -13.86] |
| x265 abr_la20 | -16.25 | -13.42 | -14.79 | -5.29 | -2.90 | -10.45 | -16.04 | 35% | -14.53 [-16.46, -12.56] | -15.63 [-17.53, -13.80] |
| x265 2pass | -10.90 | -7.28 | -8.93 | 1.60 | 0.26 | 4.53 | -10.17 | 42% | -8.37 [-9.95, -6.79] | -9.44 [-10.89, -7.98] |
| x265 vbv | -26.19 | -17.39 | -24.68 | -4.80 | -2.68 | -9.44 | -21.47 | 78% | -18.47 [-20.74, -16.14] | -19.54 [-21.73, -17.45] |
| x265 abr_default | -17.50 | -10.31 | -11.51 | -5.78 | -4.82 | -7.89 | -11.78 | 21% | -11.39 [-12.73, -10.04] | -12.47 [-13.80, -11.08] |
| x265 2pass_default | -10.49 | -1.09 | -1.26 | 1.67 | -0.33 | 6.04 | -1.98 | 56% | -2.17 [-2.96, -1.45] | -3.25 [-3.93, -2.55] |

| x265 mode | mean overshoot | max overshoot | GOPs >5% over | GOPs >10% under |
|---|---|---|---|---|
| x265 abr_la0 | -2.3% | +63.5% | 18% | 19% |
| x265 abr_la20 | -2.3% | +63.5% | 18% | 19% |
| x265 2pass | +3.9% | +129.2% | 20% | 0% |
| x265 vbv | +3.0% | +24.0% | 33% | 3% |
| x265 abr_default | -6.6% | +92.6% | 15% | 49% |
| x265 2pass_default | +7.5% | +86.1% | 41% | 0% |

## Learners, imitation vs RL, ensemble

Each row starts from the same logged search data.

| method | val score | test all | unclipped | scene cuts | natural | spliced | stable | GOPs >1% over | vs causal rule | vs k=5 policy |
|---|---|---|---|---|---|---|---|---|---|---|
| k=5: CQL alone (no RL) | 1.77 | 1.85 | 1.81 | 3.79 | 2.32 | 7.00 | 1.22 | 9% | +0.76 [+0.29, +1.23] | -0.31 [-0.57, -0.02] |
| k=5: BC alone | 0.57 | 1.15 | 0.81 | 3.52 | 2.05 | 6.75 | 0.37 | 8% | +0.06 [-0.55, +0.75] | -1.01 [-1.32, -0.70] |
| k=5: BC -> PPO | 2.12 | 1.52 | 0.97 | 3.13 | 1.23 | 7.28 | 1.00 | 5% | +0.44 [+0.00, +0.90] | -0.64 [-0.97, -0.34] |
| k=5: CQL -> PPO (reference) | 2.83 | 2.16 | 1.79 | 3.87 | 2.02 | 7.90 | 1.60 | 6% | +1.08 [+0.60, +1.59] | +0.00 [+0.00, +0.00] |
| k=5: CQL -> A2C | 3.03 | 1.93 | 1.85 | 3.38 | 1.68 | 7.09 | 1.47 | 2% | +0.85 [+0.47, +1.27] | -0.22 [-0.45, +0.00] |
| k=5: CQL Q-net -> DQN | 1.50 | -0.48 | -0.46 | 1.77 | -1.25 | 8.37 | -1.21 | 5% | -1.56 [-2.09, -0.99] | -2.64 [-3.04, -2.17] |
| k=5: 3-seed ensemble (one policy) | 2.74 | 1.83 | 0.28 | 2.51 | 0.49 | 6.94 | 1.61 | 3% | +0.75 [+0.28, +1.23] | -0.33 [-0.77, +0.00] |

## Adaptive lookahead gate

The gate sees only the k=0 observation and asks for the k=5 policy per frame.

| method | val score | test all | unclipped | scene cuts | natural | spliced | stable | GOPs >1% over | vs causal rule | vs k=5 policy |
|---|---|---|---|---|---|---|---|---|---|---|
| gate k=0 / k=5, lam=0.1 | 1.77 | 1.17 | 1.09 | 2.32 | -0.15 | 7.74 | 0.79 | 9% | +0.09 [-0.30, +0.49] | -0.99 [-1.34, -0.65] |
| gate k=0 / k=5, lam=0.3 | 1.73 | 1.23 | 1.11 | 2.40 | -0.17 | 8.02 | 0.85 | 10% | +0.15 [-0.23, +0.53] | -0.93 [-1.30, -0.57] |

Share of frames handed to the k=5 policy: gate k=0 / k=5, lam=0.1 44%; gate k=0 / k=5, lam=0.3 28%.

## New observation features (CQL -> PPO, 60k steps)

fb: achieved PSNR (last, mean), bit-prediction error (last, mean), frames since the last cut. scene: fb + per window frame cut strength, motion, spatial detail, gradual-transition flag. sum: fb + window summary (mean/max/min complexity, any cut, where the cut is, complexity after it) instead of the raw window.

| method | val score | test all | unclipped | scene cuts | natural | spliced | stable | GOPs >1% over | vs causal rule | vs k=5 policy |
|---|---|---|---|---|---|---|---|---|---|---|
| k=5 reference (current features) | 2.83 | 2.16 | 1.79 | 3.87 | 2.02 | 7.90 | 1.60 | 6% | +1.08 [+0.62, +1.60] | +0.00 [+0.00, +0.00] |
| fb, k=5 | 2.20 | 2.18 | 2.13 | 4.31 | 2.22 | 8.89 | 1.48 | 6% | +1.09 [+0.61, +1.64] | +0.02 [-0.17, +0.20] |
| scene, k=5 | 2.45 | 2.39 | 2.34 | 4.35 | 2.27 | 8.90 | 1.75 | 8% | +1.31 [+0.80, +1.92] | +0.23 [+0.02, +0.48] |
| sum, k=5 | 3.09 | 2.05 | 1.29 | 4.16 | 1.90 | 9.09 | 1.36 | 6% | +0.97 [+0.55, +1.39] | -0.11 [-0.42, +0.23] |
| sum, k=29 | 1.47 | 1.42 | 1.25 | 3.79 | 1.55 | 8.69 | 0.65 | 5% | +0.33 [-0.26, +0.91] | -0.74 [-1.02, -0.49] |
| k=29, current features | 0.84 | 1.55 | 1.04 | 2.90 | 1.06 | 6.92 | 1.11 | 10% | +0.47 [+0.07, +0.92] | -0.61 [-0.97, -0.27] |

## Model-based planning (learned bits/PSNR model + receding-horizon search)

Model: 2259900 logged frames; held-out error 0.225 log2 bits (17 %), 0.18 dB. Margin = fraction of the budget held back.

| method | val score | test all | unclipped | scene cuts | natural | spliced | stable | GOPs >1% over | vs causal rule | vs k=5 policy |
|---|---|---|---|---|---|---|---|---|---|---|
| MPC k=5, margin 0.0 | -4.57 | -3.51 | -3.65 | -0.25 | -3.36 | 6.55 | -4.57 | 48% | -4.59 [-5.42, -3.79] | -5.67 [-6.57, -4.80] |
| MPC k=5, margin 0.03 | -2.35 | -3.36 | -3.49 | 0.03 | -2.96 | 6.56 | -4.47 | 26% | -4.45 [-5.27, -3.63] | -5.52 [-6.38, -4.74] |
| MPC k=5, margin 0.06 | -1.09 | -2.80 | -2.86 | 0.92 | -1.68 | 6.61 | -4.01 | 17% | -3.88 [-4.64, -3.11] | -4.96 [-5.76, -4.19] |
| MPC k=29, margin 0.0 | -2.59 | -2.62 | -2.79 | -0.22 | -2.87 | 5.59 | -3.40 | 25% | -3.70 [-4.46, -2.91] | -4.78 [-5.58, -4.03] |
| MPC k=29, margin 0.03 | -0.76 | -2.46 | -2.56 | -0.51 | -3.18 | 5.34 | -3.10 | 9% | -3.54 [-4.27, -2.80] | -4.62 [-5.38, -3.88] |
| MPC k=29, margin 0.06 | 0.28 | -2.11 | -2.03 | -0.40 | -2.87 | 5.00 | -2.66 | 4% | -3.19 [-3.88, -2.47] | -4.27 [-5.05, -3.49] |

## Budget constraint on the k=5 policy

Both continue from the k=5 policy for 40k steps (scene-cut GOPs 4x).

| method | val score | test all | unclipped | scene cuts | natural | spliced | stable | GOPs >1% over | vs causal rule | vs k=5 policy |
|---|---|---|---|---|---|---|---|---|---|---|
| k=5 Lagrangian, rate update | 2.56 | 1.35 | 1.28 | 3.02 | 1.20 | 7.02 | 0.81 | 0% | +0.27 [-0.22, +0.81] | -0.81 [-1.08, -0.57] |
| k=5 Lagrangian, PID update | 2.76 | 1.69 | 1.67 | 3.92 | 2.58 | 6.85 | 0.96 | 1% | +0.60 [+0.11, +1.15] | -0.47 [-0.79, -0.08] |

Final kappa (rate): 1241, 1824, 1599.

Final kappa (pid): 1400, 1930, 1545.

## Full lookahead curve on the new data (CQL -> PPO, 60k steps)



| method | val score | test all | unclipped | scene cuts | natural | spliced | stable | GOPs >1% over | vs causal rule | vs k=5 policy |
|---|---|---|---|---|---|---|---|---|---|---|
| k=0 | 2.00 | 1.26 | 0.63 | 2.32 | -0.31 | 8.07 | 0.92 | 11% | +0.18 [-0.17, +0.57] | -0.90 [-1.29, -0.51] |
| k=1 | 2.37 | 1.56 | 1.49 | 3.00 | 1.04 | 7.29 | 1.09 | 7% | +0.48 [+0.07, +0.93] | -0.60 [-0.85, -0.36] |
| k=2 | 1.41 | 1.70 | 1.62 | 3.14 | 1.79 | 6.12 | 1.23 | 10% | +0.61 [+0.13, +1.12] | -0.46 [-0.71, -0.21] |
| k=5 | 2.83 | 2.16 | 1.79 | 3.87 | 2.02 | 7.90 | 1.60 | 6% | +1.08 [+0.61, +1.62] | +0.00 [+0.00, +0.00] |
| k=10 | 2.35 | 1.77 | 1.81 | 3.84 | 2.16 | 7.54 | 1.10 | 6% | +0.69 [+0.20, +1.22] | -0.38 [-0.67, -0.02] |
| k=29 | 0.84 | 1.55 | 1.04 | 2.90 | 1.06 | 6.92 | 1.11 | 10% | +0.47 [+0.03, +0.91] | -0.61 [-0.98, -0.27] |

Best on validation over all rows above: **sum, k=5** (val score 3.09).
| method | val score | test all | unclipped | scene cuts | natural | spliced | stable | GOPs >1% over | vs causal rule | vs k=5 policy |
|---|---|---|---|---|---|---|---|---|---|---|
| sum, k=5 | 3.09 | 2.05 | 1.29 | 4.16 | 1.90 | 9.09 | 1.36 | 6% | +0.97 [+0.54, +1.41] | -0.11 [-0.42, +0.19] |

## Where the k=5 policy wins and loses (test GOPs, by scene statistics)

208 test GOPs; per GOP the k=5 policy's saving (3 seeds, both QPs) and its difference from the budget-fitted rule. Terciles of each statistic; Spearman correlation of the difference with it.

| statistic | low third: policy / vs rule | middle third | high third | Spearman (difference) |
|---|---|---|---|---|
| max cut strength | 1.99 / +0.04 | 0.79 / -0.10 | 3.69 / +1.50 | +0.24 |
| mean motion | 1.15 / -0.09 | 4.16 / +1.22 | 1.18 / +0.32 | +0.16 |
| mean spatial detail | 1.75 / +1.17 | 2.05 / +0.75 | 2.68 / -0.49 | -0.16 |

| GOP type | GOPs | k=5 policy | budget-fitted rule | difference |
|---|---|---|---|---|
| gradual transition | 7 | 1.29 | 0.06 | +1.24 |
| hard cut, moderate (0.35-0.6) | 35 | 3.22 | 0.94 | +2.27 |
| hard cut, strong (>0.6) | 16 | 5.29 | 5.59 | -0.29 |
| no cut, high motion | 57 | 1.44 | 1.01 | +0.43 |
| no cut, low motion | 93 | 1.73 | 1.82 | -0.09 |

Largest losses vs the rule: ed1/g0 -33.5 (cut 0.60, gradual 0); bottle/g5 -8.1 (cut 0.07, gradual 0); ed3/g3 -7.9 (cut 0.54, gradual 0); spliced4/g6 -7.0 (cut 0.54, gradual 0); spliced4/g5 -6.4 (cut 0.03, gradual 0).
