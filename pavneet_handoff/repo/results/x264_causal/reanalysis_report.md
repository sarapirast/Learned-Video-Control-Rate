# Re-analysis: clip-level CIs and natural cuts (x264, budgets (26, 30, 34, 38, 42), test)

479 test GOPs in 98 clusters (60 spliced GOPs, each its own cluster). Score differences A − B, seeds averaged per case. 'holds' = the clip-level CI excludes 0 on all cases and on natural (non-spliced) GOPs.

## All budgets

| claim                                                            | A - B                                       |   cases | case CI                 | clip CI (98 clusters)   | natural only (clip CI)   | per seed               | verdict         | clip CI (94 clusters)   |
|:-----------------------------------------------------------------|:--------------------------------------------|--------:|:------------------------|:------------------------|:-------------------------|:-----------------------|:----------------|:------------------------|
| constrained RL beats imitation (k=0)                             | lagr fixed:0 − bc fixed:0                   |    2395 | +10.82 [+9.90, +11.75]  | +10.82 [+8.06, +14.97]  | +9.78 [+7.04, +14.03]    | +8.72, +11.36, +12.37  | holds           | nan                     |
| constrained RL beats imitation (k=5)                             | lagr fixed:5 − bc fixed:5                   |    2395 | +7.54 [+6.77, +8.36]    | +7.54 [+5.37, +11.06]   | +7.42 [+5.12, +11.34]    | +7.07, +10.33, +5.21   | holds           | nan                     |
| PID-Lagrangian beats imitation (k=0)                             | pid fixed:0 − bc fixed:0                    |    2395 | +10.24 [+9.30, +11.20]  | +10.24 [+8.18, +13.37]  | +9.10 [+7.06, +12.19]    | +6.89, +13.09, +10.76  | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=0)          | lagr fixed:0 − bc_fb2 fixed:0               |    2395 | +6.46 [+5.84, +7.08]    | +6.46 [+5.09, +8.30]    | +5.21 [+3.66, +6.84]     | +5.97, +5.60, +7.81    | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=5)          | lagr fixed:5 − bc_fb2 fixed:5               |    2395 | +4.26 [+3.70, +4.80]    | +4.26 [+3.05, +5.51]    | +3.86 [+2.52, +5.20]     | +3.77, +5.85, +3.15    | holds           | nan                     |
| feedback control helps imitation (k=0)                           | bc_fb2 fixed:0 − bc fixed:0                 |    2395 | +4.36 [+3.63, +5.15]    | +4.36 [+2.15, +8.29]    | +4.57 [+2.13, +9.07]     | +2.76, +5.76, +4.56    | holds           | nan                     |
| constrained RL beats penalty RL (k=5)                            | lagr fixed:5 − cql_ppo fixed:5              |    2395 | +0.95 [+0.59, +1.36]    | +0.95 [+0.12, +2.51]    | +1.07 [+0.14, +2.83]     | +1.10, +2.20, -0.44    | holds           | nan                     |
| PPO fine-tuning beats imitation (k=5)                            | cql_ppo fixed:5 − bc fixed:5                |    2395 | +6.59 [+5.93, +7.25]    | +6.59 [+5.10, +8.69]    | +6.35 [+4.82, +8.62]     | +5.97, +8.13, +5.65    | holds           | nan                     |
| lookahead: k 0 -> 1                                              | cql_ppo fixed:1 − cql_ppo fixed:0           |    2395 | +1.10 [+0.74, +1.42]    | +1.10 [+0.14, +1.78]    | +1.04 [-0.07, +1.84]     | +0.74, +2.20, +0.34    | case-level only | nan                     |
| lookahead: k 1 -> 2                                              | cql_ppo fixed:2 − cql_ppo fixed:1           |    2395 | -1.02 [-1.25, -0.81]    | -1.02 [-1.83, -0.47]    | -1.01 [-1.94, -0.43]     | -1.31, -2.03, +0.27    | holds           | nan                     |
| lookahead: k 2 -> 3                                              | cql_ppo fixed:3 − cql_ppo fixed:2           |    2395 | +0.56 [+0.30, +0.85]    | +0.56 [+0.08, +1.26]    | +0.50 [+0.00, +1.26]     | +3.26, -1.61, +0.02    | holds           | nan                     |
| lookahead: k 3 -> 5                                              | cql_ppo fixed:5 − cql_ppo fixed:3           |    2395 | -0.52 [-0.82, -0.23]    | -0.52 [-1.31, +0.02]    | -0.51 [-1.39, +0.10]     | -2.28, +1.17, -0.45    | case-level only | nan                     |
| lookahead: k 0 -> 5                                              | cql_ppo fixed:5 − cql_ppo fixed:0           |    2395 | +0.11 [-0.34, +0.50]    | +0.11 [-1.49, +0.94]    | +0.02 [-1.74, +0.95]     | +0.41, -0.26, +0.18    | n.s.            | nan                     |
| lookahead for constrained RL: k 0 -> 5                           | lagr fixed:5 − lagr fixed:0                 |    2395 | +0.02 [-0.17, +0.22]    | +0.02 [-0.36, +0.33]    | +0.00 [-0.38, +0.31]     | -1.05, +2.60, -1.48    | n.s.            | nan                     |
| learned policy beats the hand lookahead rule (k=5)               | cql_ppo fixed:5 − la_rule k=5               |    2395 | +3.80 [+2.98, +4.55]    | +3.80 [+0.92, +5.39]    | +3.15 [-0.21, +4.86]     | +3.69, +2.91, +4.81    | case-level only | nan                     |
| gap: search vs best learner                                      | hindsight search − lagr fixed:5             |     809 | +10.59 [+8.14, +14.08]  | nan                     | +10.04 [+6.65, +17.30]   | –                      | holds           | +10.59 [+7.60, +17.03]  |
| constrained RL vs the encoder's ABR (same budget)                | lagr fixed:0 − own abr                      |    2395 | +37.95 [+34.54, +41.16] | +37.95 [+28.91, +48.22] | +39.03 [+29.20, +51.26]  | +39.06, +35.74, +39.06 | holds           | nan                     |
| constrained RL vs the encoder's two-pass (same budget)           | lagr fixed:5 − own 2pass                    |    2356 | +1.93 [-0.75, +4.32]    | +1.93 [-6.40, +6.12]    | +2.45 [-7.17, +7.38]     | +2.01, +2.28, +1.49    | n.s.            | nan                     |
| constrained RL vs two-pass with the encoder's defaults           | lagr fixed:5 − own 2pass +AQ                |    2356 | +10.57 [+5.51, +17.36]  | +10.57 [+4.70, +16.32]  | +11.88 [+5.42, +18.59]   | +10.65, +10.93, +10.14 | holds           | nan                     |
| constrained RL vs the causal feedback rule                       | lagr fixed:0 − rule k=0                     |    2395 | +18.16 [+17.33, +18.97] | +18.16 [+15.51, +21.48] | +16.31 [+13.12, +19.66]  | +19.26, +15.94, +19.27 | holds           | nan                     |
| imitation + feedback vs the causal feedback rule                 | bc_fb2 fixed:0 − rule k=0                   |    2395 | +11.70 [+11.04, +12.33] | +11.70 [+9.89, +13.68]  | +11.10 [+8.93, +13.23]   | +13.30, +10.34, +11.46 | holds           | nan                     |
| constrained RL vs STATIC on the causal base QP (causal env)      | lagr fixed:0 − static k=0                   |    2395 | +24.80 [+22.68, +27.10] | +24.80 [+18.36, +35.58] | +23.86 [+16.97, +35.51]  | +25.91, +22.58, +25.91 | holds           | nan                     |
| constrained RL vs the best constant QP in hindsight (causal env) | lagr fixed:0 − best constant QP (hindsight) |    2395 | -2.36 [-4.80, -0.33]    | -2.36 [-11.59, +1.77]   | -2.63 [-13.43, +2.01]    | -1.25, -4.58, -1.25    | case-level only | nan                     |

## Budget QP 26

| claim                                                   | A - B                             |   cases | case CI                | clip CI (98 clusters)   | natural only (clip CI)   | per seed             | verdict         | clip CI (53 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:-----------------------|:------------------------|:-------------------------|:---------------------|:----------------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +8.65 [+7.07, +10.39]  | +8.65 [+5.62, +13.96]   | +8.12 [+4.78, +13.87]    | +9.77, +3.06, +13.10 | holds           | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +8.83 [+6.76, +11.16]  | +8.83 [+4.58, +17.00]   | +8.90 [+4.19, +18.06]    | +7.76, +11.75, +6.96 | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +2.80 [+1.00, +4.44]   | +2.80 [-3.03, +5.85]    | +1.51 [-5.25, +4.83]     | +5.22, -3.41, +6.58  | case-level only | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +1.18 [-0.82, +2.93]   | +1.18 [-5.56, +4.67]    | +0.50 [-7.09, +4.35]     | +1.16, +1.96, +0.43  | n.s.            | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | -3.60 [-5.44, -1.96]   | -3.60 [-10.28, -0.52]   | -3.95 [-11.69, -0.49]    | +0.23, -6.65, -4.38  | holds           | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | -0.85 [-1.42, -0.35]   | -0.85 [-2.14, -0.04]    | -0.66 [-2.05, +0.17]     | -3.15, +5.53, -4.92  | case-level only | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     167 | +19.01 [+7.83, +35.20] | nan                     | +19.59 [+5.80, +51.93]   | –                    | holds           | +19.01 [+7.03, +48.65]  |

## Budget QP 30

| claim                                                   | A - B                             |   cases | case CI                 | clip CI (98 clusters)   | natural only (clip CI)   | per seed               | verdict   | clip CI (55 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:------------------------|:------------------------|:-------------------------|:-----------------------|:----------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +15.21 [+12.63, +18.24] | +15.21 [+9.53, +25.55]  | +13.88 [+7.94, +25.12]   | +11.87, +14.15, +19.61 | holds     | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +9.49 [+7.34, +12.10]   | +9.49 [+5.27, +17.98]   | +9.85 [+5.21, +19.47]    | +7.69, +14.28, +6.51   | holds     | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +8.69 [+7.46, +10.07]   | +8.69 [+6.63, +12.08]   | +6.99 [+5.04, +10.00]    | +7.23, +7.38, +11.46   | holds     | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +5.48 [+4.53, +6.52]    | +5.48 [+3.83, +8.38]    | +5.31 [+3.52, +8.57]     | +3.88, +8.19, +4.37    | holds     | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | -0.03 [-0.46, +0.36]    | -0.03 [-0.96, +0.60]    | -0.07 [-1.13, +0.60]     | +0.31, -0.28, -0.11    | n.s.      | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.29 [-0.13, +0.71]    | +0.29 [-0.44, +0.94]    | +0.36 [-0.35, +1.06]     | -0.85, +2.84, -1.12    | n.s.      | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     153 | +7.69 [+6.51, +9.07]    | nan                     | +7.01 [+5.37, +9.65]     | –                      | holds     | +7.69 [+6.10, +10.28]   |

## Budget QP 34

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed             | verdict         | clip CI (61 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:---------------------|:----------------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +6.89 [+5.59, +8.26] | +6.89 [+4.54, +10.54]   | +5.87 [+3.40, +9.58]     | +4.64, +10.24, +5.79 | holds           | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +5.22 [+4.32, +6.18] | +5.22 [+3.72, +7.17]    | +4.82 [+3.22, +6.96]     | +4.06, +8.15, +3.44  | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +5.28 [+4.40, +6.24] | +5.28 [+3.95, +7.21]    | +4.30 [+2.85, +6.06]     | +4.26, +6.75, +4.85  | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +3.98 [+3.33, +4.68] | +3.98 [+2.96, +5.20]    | +3.59 [+2.46, +4.82]     | +3.07, +5.93, +2.94  | holds           | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.70 [+0.40, +1.00] | +0.70 [+0.17, +1.13]    | +0.54 [-0.11, +1.00]     | +0.77, +0.57, +0.77  | case-level only | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.20 [-0.10, +0.50] | +0.20 [-0.23, +0.64]    | +0.06 [-0.43, +0.44]     | -0.11, +1.07, -0.35  | n.s.            | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     173 | +8.08 [+7.04, +9.20] | nan                     | +7.22 [+5.52, +8.50]     | –                    | holds           | +8.08 [+6.71, +9.42]    |

## Budget QP 38

| claim                                                   | A - B                             |   cases | case CI               | clip CI (98 clusters)   | natural only (clip CI)   | per seed             | verdict   | clip CI (58 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:----------------------|:------------------------|:-------------------------|:---------------------|:----------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +7.87 [+6.35, +9.39]  | +7.87 [+5.08, +12.41]   | +6.58 [+3.75, +11.10]    | +5.32, +11.95, +6.33 | holds     | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +5.26 [+4.11, +6.43]  | +5.26 [+3.41, +7.79]    | +4.89 [+2.96, +7.54]     | +5.24, +7.33, +3.22  | holds     | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +5.69 [+4.68, +6.71]  | +5.69 [+4.07, +8.14]    | +4.49 [+2.85, +6.76]     | +4.76, +7.08, +5.25  | holds     | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +4.33 [+3.56, +5.08]  | +4.33 [+3.04, +6.00]    | +4.00 [+2.69, +5.75]     | +4.09, +5.81, +3.07  | holds     | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +1.39 [+1.02, +1.74]  | +1.39 [+0.97, +1.83]    | +1.30 [+0.83, +1.77]     | +0.42, +2.26, +1.48  | holds     | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.13 [-0.26, +0.52]  | +0.13 [-0.29, +0.54]    | +0.14 [-0.17, +0.41]     | -0.38, +1.33, -0.55  | n.s.      | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     158 | +8.79 [+7.09, +10.76] | nan                     | +6.98 [+5.80, +8.30]     | –                    | holds     | +8.79 [+7.13, +11.37]   |

## Budget QP 42

| claim                                                   | A - B                             |   cases | case CI                 | clip CI (98 clusters)   | natural only (clip CI)   | per seed               | verdict   | clip CI (54 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:------------------------|:------------------------|:-------------------------|:-----------------------|:----------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +15.47 [+13.29, +17.73] | +15.47 [+12.03, +20.56] | +14.45 [+10.79, +19.78]  | +12.01, +17.39, +17.03 | holds     | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +8.89 [+7.53, +10.30]   | +8.89 [+6.78, +11.65]   | +8.64 [+6.43, +11.55]    | +10.61, +10.15, +5.92  | holds     | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +9.83 [+8.28, +11.43]   | +9.83 [+7.74, +12.82]   | +8.77 [+6.63, +11.60]    | +8.37, +10.21, +10.90  | holds     | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +6.32 [+5.24, +7.46]    | +6.32 [+4.71, +8.52]    | +5.90 [+4.26, +8.05]     | +6.66, +7.34, +4.97    | holds     | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +2.09 [+1.32, +2.82]    | +2.09 [+0.99, +3.07]    | +2.28 [+1.34, +3.26]     | +0.35, +2.79, +3.14    | holds     | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.33 [-0.17, +0.87]    | +0.33 [-0.25, +1.00]    | +0.12 [-0.50, +0.82]     | -0.74, +2.21, -0.47    | n.s.      | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     158 | +9.06 [+7.78, +10.49]   | nan                     | +8.86 [+7.23, +10.98]    | –                      | holds     | +9.06 [+7.52, +10.98]   |

## Lookahead by GOP type: stable

| claim              | A - B                             |   cases | case CI              | clip CI (38 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |    1745 | -0.34 [-0.89, +0.14] | -0.34 [-2.32, +0.69]    | -0.34 [-2.32, +0.69]     | -0.17, -0.68, -0.16 | n.s.      |

## Lookahead by GOP type: natural cut

| claim              | A - B                             |   cases | case CI              | clip CI (7 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:-----------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     145 | +0.95 [+0.02, +1.93] | +0.95 [-1.40, +2.27]   | +0.95 [-1.40, +2.27]     | +1.50, +0.76, +0.58 | case-level only |

## Lookahead by GOP type: spliced

| claim              | A - B                             |   cases | case CI              | clip CI (60 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     300 | +0.75 [-0.31, +1.68] | +0.75 [-0.42, +1.73]    | –                        | +2.97, -0.48, -0.23 | n.s.      |

