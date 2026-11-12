# Re-analysis: clip-level CIs and natural cuts (x264, budgets (26, 30, 34, 38, 42), test)

479 test GOPs in 98 clusters (60 spliced GOPs, each its own cluster). Score differences A − B, seeds averaged per case. 'holds' = the clip-level CI excludes 0 on all cases and on natural (non-spliced) GOPs.

## All budgets

| claim                                                   | A - B                              |   cases | case CI                 | clip CI (98 clusters)   | natural only (clip CI)   | per seed               | verdict         |
|:--------------------------------------------------------|:-----------------------------------|--------:|:------------------------|:------------------------|:-------------------------|:-----------------------|:----------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0          |    2395 | +4.05 [+3.64, +4.50]    | +4.05 [+3.04, +4.91]    | +3.29 [+2.13, +4.08]     | +4.43, +3.81, +3.92    | holds           |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5          |    2395 | +1.16 [+0.88, +1.47]    | +1.16 [+0.38, +1.86]    | +1.31 [+0.48, +2.06]     | +1.67, +0.34, +1.47    | holds           |
| PID-Lagrangian beats imitation (k=0)                    | pid fixed:0 − bc fixed:0           |    2395 | +3.37 [+2.97, +3.80]    | +3.37 [+2.52, +4.14]    | +2.76 [+1.83, +3.40]     | +3.25, +3.23, +3.63    | holds           |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0      |    2395 | +3.90 [+3.47, +4.35]    | +3.90 [+2.88, +4.73]    | +2.99 [+1.71, +3.85]     | +4.26, +3.38, +4.06    | holds           |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5      |    2395 | +1.26 [+0.99, +1.57]    | +1.26 [+0.52, +1.92]    | +1.35 [+0.56, +2.05]     | +1.83, +0.37, +1.58    | holds           |
| feedback control helps imitation (k=0)                  | bc_fb2 fixed:0 − bc fixed:0        |    2395 | +0.15 [-0.09, +0.39]    | +0.15 [-0.19, +0.57]    | +0.30 [-0.03, +0.80]     | +0.17, +0.43, -0.15    | n.s.            |
| constrained RL beats penalty RL (k=5)                   | lagr fixed:5 − cql_ppo fixed:5     |    2395 | +1.63 [+1.36, +1.92]    | +1.63 [+0.93, +2.25]    | +1.37 [+0.48, +2.06]     | +2.99, -0.09, +1.99    | holds           |
| PPO fine-tuning beats imitation (k=5)                   | cql_ppo fixed:5 − bc fixed:5       |    2395 | -0.47 [-0.69, -0.25]    | -0.47 [-1.10, +0.08]    | -0.06 [-0.67, +0.61]     | -1.32, +0.43, -0.53    | case-level only |
| lookahead: k 0 -> 1                                     | cql_ppo fixed:1 − cql_ppo fixed:0  |    2395 | +0.16 [-0.13, +0.44]    | +0.16 [-0.64, +0.74]    | -0.06 [-0.99, +0.50]     | -0.19, -0.87, +1.54    | n.s.            |
| lookahead: k 1 -> 2                                     | cql_ppo fixed:2 − cql_ppo fixed:1  |    2395 | +0.73 [+0.51, +0.97]    | +0.73 [+0.38, +1.31]    | +0.54 [+0.13, +1.13]     | +2.42, +0.08, -0.30    | holds           |
| lookahead: k 2 -> 3                                     | cql_ppo fixed:3 − cql_ppo fixed:2  |    2395 | +0.40 [+0.22, +0.59]    | +0.40 [-0.01, +0.70]    | +0.52 [+0.11, +0.82]     | +0.10, +1.56, -0.46    | case-level only |
| lookahead: k 3 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:3  |    2395 | -0.33 [-0.54, -0.11]    | -0.33 [-0.78, +0.20]    | -0.48 [-0.99, +0.07]     | -1.97, +0.83, +0.15    | case-level only |
| lookahead: k 3 -> 29 (flat beyond 3)                    | cql_ppo fixed:29 − cql_ppo fixed:3 |    2395 | -3.54 [-3.85, -3.23]    | -3.54 [-4.14, -2.97]    | -4.22 [-4.98, -3.70]     | -3.32, -8.64, +1.34    | holds           |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0  |    2395 | +0.97 [+0.72, +1.22]    | +0.97 [+0.41, +1.50]    | +0.53 [-0.13, +0.94]     | +0.36, +1.60, +0.93    | case-level only |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0        |    2395 | +0.12 [-0.04, +0.28]    | +0.12 [-0.10, +0.46]    | -0.13 [-0.30, +0.10]     | +0.65, -0.37, +0.07    | n.s.            |
| learned policy beats the hand lookahead rule (k=5)      | cql_ppo fixed:5 − la_rule k=5      |    2395 | +5.26 [+4.83, +5.74]    | +5.26 [+4.08, +7.02]    | +5.01 [+3.68, +6.85]     | +4.45, +6.25, +5.09    | holds           |
| gap: search vs best learner                             | hindsight search − lagr fixed:5    |    2395 | +5.39 [+5.14, +5.65]    | +5.39 [+4.72, +6.11]    | +5.02 [+4.23, +5.82]     | –                      | holds           |
| constrained RL vs the encoder's ABR (same budget)       | lagr fixed:0 − own abr             |    2395 | +44.27 [+41.83, +46.81] | +44.27 [+36.46, +54.84] | +45.41 [+36.66, +57.60]  | +44.28, +44.03, +44.50 | holds           |
| constrained RL vs the encoder's two-pass (same budget)  | lagr fixed:5 − own 2pass           |    2357 | +8.95 [+7.93, +10.27]   | +8.95 [+7.19, +10.65]   | +9.45 [+7.56, +11.39]    | +9.48, +8.21, +9.15    | holds           |
| constrained RL vs two-pass with the encoder's defaults  | lagr fixed:5 − own 2pass +AQ       |    2357 | +17.87 [+13.58, +23.87] | +17.87 [+10.75, +26.00] | +19.16 [+11.13, +28.73]  | +18.40, +17.13, +18.08 | holds           |
| constrained RL vs the causal feedback rule              | lagr fixed:0 − rule k=0            |    2395 | +19.48 [+18.69, +20.31] | +19.48 [+17.27, +22.55] | +18.55 [+16.03, +21.71]  | +19.49, +19.24, +19.71 | holds           |
| imitation + feedback vs the causal feedback rule        | bc_fb2 fixed:0 − rule k=0          |    2395 | +15.58 [+14.85, +16.32] | +15.58 [+13.35, +18.90] | +15.56 [+13.08, +19.30]  | +15.23, +15.86, +15.64 | holds           |

## Budget QP 26

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +2.63 [+2.01, +3.21] | +2.63 [+1.19, +3.56]    | +2.89 [+1.41, +3.89]     | +2.95, +2.08, +2.87 | holds     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +1.33 [+0.85, +1.87] | +1.33 [+0.28, +2.19]    | +1.57 [+0.46, +2.48]     | +1.53, +0.65, +1.82 | holds     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +2.61 [+2.03, +3.16] | +2.61 [+1.22, +3.57]    | +2.54 [+0.95, +3.60]     | +3.05, +1.76, +3.01 | holds     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +1.17 [+0.73, +1.67] | +1.17 [+0.28, +1.83]    | +1.36 [+0.42, +2.06]     | +1.66, +0.40, +1.46 | holds     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | -0.36 [-0.95, +0.19] | -0.36 [-1.64, +0.69]    | -0.73 [-2.25, +0.34]     | -0.90, -0.43, +0.27 | n.s.      |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.24 [-0.05, +0.56] | +0.24 [-0.17, +0.92]    | -0.23 [-0.58, +0.28]     | +0.88, -0.40, +0.25 | n.s.      |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +4.60 [+4.15, +5.10] | +4.60 [+3.89, +5.34]    | +4.42 [+3.58, +5.22]     | –                   | holds     |

## Budget QP 30

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +4.22 [+3.46, +5.00] | +4.22 [+3.07, +5.22]    | +3.89 [+2.64, +4.85]     | +5.04, +3.66, +3.97 | holds     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +1.20 [+0.78, +1.64] | +1.20 [+0.42, +1.87]    | +1.45 [+0.69, +2.20]     | +2.19, -0.30, +1.71 | holds     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +4.05 [+3.40, +4.73] | +4.05 [+3.01, +4.90]    | +3.45 [+2.23, +4.30]     | +4.97, +3.29, +3.90 | holds     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +1.15 [+0.78, +1.51] | +1.15 [+0.49, +1.70]    | +1.37 [+0.73, +1.98]     | +2.08, -0.29, +1.67 | holds     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.19 [-0.34, +0.69] | +0.19 [-0.58, +0.94]    | -0.15 [-0.98, +0.51]     | -0.27, +0.68, +0.15 | n.s.      |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.27 [-0.04, +0.61] | +0.27 [-0.07, +0.80]    | -0.09 [-0.33, +0.25]     | +0.64, -0.46, +0.64 | n.s.      |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +4.66 [+4.23, +5.13] | +4.66 [+4.02, +5.25]    | +4.32 [+3.51, +4.96]     | –                   | holds     |

## Budget QP 34

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +2.92 [+2.19, +3.67] | +2.92 [+1.91, +3.79]    | +2.16 [+1.03, +2.89]     | +2.75, +2.92, +3.09 | holds           |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +0.58 [+0.08, +1.13] | +0.58 [-0.35, +1.30]    | +0.67 [-0.33, +1.40]     | +0.82, -0.03, +0.95 | case-level only |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +3.08 [+2.32, +3.83] | +3.08 [+1.91, +4.00]    | +2.10 [+0.68, +3.08]     | +3.01, +2.83, +3.41 | holds           |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +0.75 [+0.26, +1.29] | +0.75 [-0.15, +1.44]    | +0.75 [-0.20, +1.48]     | +1.02, +0.02, +1.20 | case-level only |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +1.01 [+0.53, +1.52] | +1.01 [+0.45, +1.52]    | +0.82 [+0.32, +1.17]     | +0.77, +1.32, +0.95 | holds           |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.10 [-0.23, +0.42] | +0.10 [-0.17, +0.42]    | -0.01 [-0.23, +0.22]     | +0.64, -0.25, -0.10 | n.s.            |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +5.36 [+4.87, +5.91] | +5.36 [+4.63, +6.23]    | +5.03 [+4.20, +5.96]     | –                   | holds           |

## Budget QP 38

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +4.61 [+3.54, +5.77] | +4.61 [+3.29, +6.03]    | +2.91 [+1.35, +4.01]     | +5.06, +4.58, +4.18 | holds           |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +0.81 [+0.25, +1.42] | +0.81 [+0.02, +1.46]    | +0.80 [-0.03, +1.46]     | +1.41, +0.18, +0.85 | case-level only |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +4.43 [+3.23, +5.72] | +4.43 [+2.90, +5.99]    | +2.91 [+1.02, +4.47]     | +4.62, +4.22, +4.47 | holds           |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +1.14 [+0.60, +1.74] | +1.14 [+0.23, +1.89]    | +1.12 [+0.15, +1.95]     | +1.72, +0.53, +1.17 | holds           |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +1.51 [+0.97, +2.06] | +1.51 [+0.86, +2.17]    | +0.97 [+0.30, +1.48]     | +0.98, +2.77, +0.77 | holds           |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | -0.01 [-0.45, +0.39] | -0.01 [-0.43, +0.52]    | -0.17 [-0.56, +0.20]     | +0.54, -0.33, -0.24 | n.s.            |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +6.02 [+5.45, +6.72] | +6.02 [+5.12, +6.88]    | +5.62 [+4.50, +6.62]     | –                   | holds           |

## Budget QP 42

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +5.87 [+4.65, +7.29] | +5.87 [+4.55, +7.67]    | +4.62 [+3.27, +6.10]     | +6.32, +5.83, +5.46 | holds     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +1.86 [+0.98, +3.08] | +1.86 [+0.64, +3.29]    | +2.05 [+0.77, +3.59]     | +2.38, +1.21, +2.00 | holds     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +5.33 [+4.12, +6.71] | +5.33 [+4.05, +7.18]    | +3.95 [+2.59, +5.46]     | +5.65, +4.82, +5.53 | holds     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +2.08 [+1.20, +3.31] | +2.08 [+0.93, +3.56]    | +2.15 [+0.89, +3.78]     | +2.67, +1.17, +2.41 | holds     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +2.47 [+1.90, +3.04] | +2.47 [+1.73, +3.16]    | +1.72 [+0.84, +2.31]     | +1.23, +3.65, +2.53 | holds     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | -0.02 [-0.41, +0.37] | -0.02 [-0.47, +0.43]    | -0.13 [-0.61, +0.35]     | +0.56, -0.43, -0.19 | n.s.      |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +6.30 [+5.66, +7.06] | +6.30 [+5.34, +7.50]    | +5.73 [+4.65, +6.94]     | –                   | holds     |

## Lookahead by GOP type: stable

| claim              | A - B                             |   cases | case CI              | clip CI (38 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |    1745 | +0.22 [+0.01, +0.43] | +0.22 [-0.39, +0.74]    | +0.22 [-0.39, +0.74]     | +0.18, +0.46, +0.02 | case-level only |

## Lookahead by GOP type: natural cut

| claim              | A - B                             |   cases | case CI              | clip CI (7 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:-----------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     145 | +2.97 [+1.75, +4.20] | +2.97 [-0.91, +4.57]   | +2.97 [-0.91, +4.57]     | -0.53, +4.28, +5.16 | case-level only |

## Lookahead by GOP type: spliced

| claim              | A - B                             |   cases | case CI              | clip CI (60 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     300 | +4.02 [+2.77, +5.28] | +4.02 [+1.86, +6.14]    | –                        | +4.04, +5.94, +2.09 | case-level only |

## Training on 5 vs 2 budgets (QP 30/38 test cases)

| claim                                    | A - B                                                     |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:-----------------------------------------|:----------------------------------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| 5- vs 2-budget training: cql_ppo fixed:0 | cql_ppo fixed:0 [5 budgets] − cql_ppo fixed:0 [2 budgets] |     958 | +3.48 [+2.85, +4.15] | +3.48 [+2.37, +5.18]    | +3.03 [+1.78, +4.71]     | +4.44, +1.75, +4.24 | holds     |
| 5- vs 2-budget training: cql_ppo fixed:5 | cql_ppo fixed:5 [5 budgets] − cql_ppo fixed:5 [2 budgets] |     958 | +2.73 [+2.27, +3.23] | +2.73 [+2.06, +3.68]    | +2.54 [+1.89, +3.53]     | +4.06, +1.67, +2.45 | holds     |
| 5- vs 2-budget training: bc fixed:5      | bc fixed:5 [5 budgets] − bc fixed:5 [2 budgets]           |     958 | +0.96 [+0.61, +1.32] | +0.96 [+0.39, +1.51]    | +0.76 [+0.08, +1.35]     | +0.43, +1.41, +1.03 | holds     |
| 5- vs 2-budget training: lagr fixed:5    | lagr fixed:5 [5 budgets] − lagr fixed:5 [2 budgets]       |     958 | +0.54 [+0.33, +0.78] | +0.54 [+0.32, +0.86]    | +0.47 [+0.26, +0.77]     | +1.58, -1.28, +1.33 | holds     |
| 5- vs 2-budget training: pid fixed:5     | pid fixed:5 [5 budgets] − pid fixed:5 [2 budgets]         |     958 | -0.02 [-0.27, +0.21] | -0.02 [-0.30, +0.34]    | -0.03 [-0.25, +0.31]     | +0.86, -0.08, -0.84 | n.s.      |

