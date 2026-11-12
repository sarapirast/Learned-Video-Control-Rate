# Re-analysis: clip-level CIs and natural cuts (x265, budgets (26, 30, 34, 38, 42), test)

479 test GOPs in 98 clusters (60 spliced GOPs, each its own cluster). Score differences A − B, seeds averaged per case. 'holds' = the clip-level CI excludes 0 on all cases and on natural (non-spliced) GOPs.

## All budgets

| claim                                                            | A - B                                       |   cases | case CI                 | clip CI (98 clusters)   | natural only (clip CI)   | per seed               | verdict         | clip CI (94 clusters)   |
|:-----------------------------------------------------------------|:--------------------------------------------|--------:|:------------------------|:------------------------|:-------------------------|:-----------------------|:----------------|:------------------------|
| constrained RL beats imitation (k=0)                             | lagr fixed:0 − bc fixed:0                   |    2395 | +6.09 [+5.58, +6.59]    | +6.09 [+4.81, +7.84]    | +4.89 [+3.70, +6.44]     | +6.08, +6.38, +5.81    | holds           | nan                     |
| constrained RL beats imitation (k=5)                             | lagr fixed:5 − bc fixed:5                   |    2395 | +5.65 [+5.14, +6.17]    | +5.65 [+4.31, +7.43]    | +5.19 [+3.88, +6.99]     | +4.31, +6.25, +6.39    | holds           | nan                     |
| PID-Lagrangian beats imitation (k=0)                             | pid fixed:0 − bc fixed:0                    |    2395 | +6.25 [+5.76, +6.75]    | +6.25 [+5.07, +7.85]    | +5.06 [+3.91, +6.48]     | +6.70, +6.00, +6.06    | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=0)          | lagr fixed:0 − bc_fb2 fixed:0               |    2395 | +5.14 [+4.71, +5.57]    | +5.14 [+4.04, +6.50]    | +3.94 [+2.66, +5.12]     | +4.86, +5.53, +5.05    | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=5)          | lagr fixed:5 − bc_fb2 fixed:5               |    2395 | +4.39 [+4.03, +4.77]    | +4.39 [+3.41, +5.60]    | +3.85 [+2.77, +5.11]     | +3.27, +4.85, +5.07    | holds           | nan                     |
| feedback control helps imitation (k=0)                           | bc_fb2 fixed:0 − bc fixed:0                 |    2395 | +0.94 [+0.70, +1.20]    | +0.94 [+0.37, +1.78]    | +0.95 [+0.35, +1.88]     | +1.22, +0.85, +0.76    | holds           | nan                     |
| constrained RL beats penalty RL (k=5)                            | lagr fixed:5 − cql_ppo fixed:5              |    2395 | -0.16 [-0.29, -0.03]    | -0.16 [-0.38, +0.07]    | -0.08 [-0.28, +0.19]     | -1.17, +0.42, +0.27    | case-level only | nan                     |
| PPO fine-tuning beats imitation (k=5)                            | cql_ppo fixed:5 − bc fixed:5                |    2395 | +5.82 [+5.30, +6.34]    | +5.82 [+4.47, +7.60]    | +5.26 [+3.94, +7.03]     | +5.48, +5.84, +6.13    | holds           | nan                     |
| lookahead: k 0 -> 1                                              | cql_ppo fixed:1 − cql_ppo fixed:0           |    2395 | +0.28 [+0.16, +0.41]    | +0.28 [+0.07, +0.47]    | +0.22 [-0.04, +0.40]     | -0.17, +0.49, +0.53    | case-level only | nan                     |
| lookahead: k 1 -> 2                                              | cql_ppo fixed:2 − cql_ppo fixed:1           |    2395 | -0.31 [-0.47, -0.15]    | -0.31 [-0.63, +0.01]    | -0.27 [-0.59, +0.08]     | +0.60, -1.02, -0.51    | case-level only | nan                     |
| lookahead: k 2 -> 3                                              | cql_ppo fixed:3 − cql_ppo fixed:2           |    2395 | -0.01 [-0.30, +0.26]    | -0.01 [-0.94, +0.48]    | -0.10 [-1.18, +0.42]     | -0.16, +0.50, -0.35    | n.s.            | nan                     |
| lookahead: k 3 -> 5                                              | cql_ppo fixed:5 − cql_ppo fixed:3           |    2395 | +0.43 [+0.21, +0.68]    | +0.43 [-0.01, +1.11]    | +0.35 [-0.13, +1.12]     | +0.05, +0.37, +0.88    | case-level only | nan                     |
| lookahead: k 0 -> 5                                              | cql_ppo fixed:5 − cql_ppo fixed:0           |    2395 | +0.40 [+0.24, +0.55]    | +0.40 [+0.05, +0.68]    | +0.21 [-0.23, +0.49]     | +0.30, +0.34, +0.54    | case-level only | nan                     |
| lookahead for constrained RL: k 0 -> 5                           | lagr fixed:5 − lagr fixed:0                 |    2395 | +0.18 [+0.05, +0.32]    | +0.18 [-0.07, +0.41]    | +0.09 [-0.19, +0.32]     | -0.09, -0.05, +0.69    | case-level only | nan                     |
| learned policy beats the hand lookahead rule (k=5)               | cql_ppo fixed:5 − la_rule k=5               |    2395 | +5.25 [+4.91, +5.59]    | +5.25 [+4.60, +5.94]    | +4.54 [+3.76, +5.13]     | +5.63, +4.78, +5.33    | holds           | nan                     |
| gap: search vs best learner                                      | hindsight search − lagr fixed:5             |     809 | +8.93 [+7.94, +10.17]   | nan                     | +8.32 [+6.58, +10.47]    | –                      | holds           | +8.93 [+7.48, +10.97]   |
| constrained RL vs the encoder's ABR (same budget)                | lagr fixed:0 − own abr                      |    2395 | +30.62 [+28.95, +32.24] | +30.62 [+25.56, +37.63] | +29.49 [+23.87, +37.18]  | +30.27, +30.97, +30.62 | holds           | nan                     |
| constrained RL vs the encoder's two-pass (same budget)           | lagr fixed:5 − own 2pass                    |    2395 | +21.96 [+20.58, +23.30] | +21.96 [+17.61, +26.35] | +24.08 [+19.53, +29.49]  | +21.33, +22.07, +22.47 | holds           | nan                     |
| constrained RL vs two-pass with the encoder's defaults           | lagr fixed:5 − own 2pass +AQ                |    2395 | +18.63 [+17.34, +19.96] | +18.63 [+14.46, +21.82] | +19.96 [+15.58, +23.40]  | +18.00, +18.74, +19.14 | holds           | nan                     |
| constrained RL vs the causal feedback rule                       | lagr fixed:0 − rule k=0                     |    2395 | +16.50 [+15.79, +17.22] | +16.50 [+14.19, +19.20] | +14.93 [+12.03, +17.67]  | +16.15, +16.85, +16.51 | holds           | nan                     |
| imitation + feedback vs the causal feedback rule                 | bc_fb2 fixed:0 − rule k=0                   |    2395 | +11.36 [+10.80, +11.93] | +11.36 [+9.70, +13.18]  | +10.99 [+8.96, +13.00]   | +11.30, +11.32, +11.46 | holds           | nan                     |
| constrained RL vs STATIC on the causal base QP (causal env)      | lagr fixed:0 − static k=0                   |    2395 | +18.58 [+17.34, +19.83] | +18.58 [+15.49, +23.00] | +17.36 [+14.33, +21.77]  | +18.23, +18.92, +18.58 | holds           | nan                     |
| constrained RL vs the best constant QP in hindsight (causal env) | lagr fixed:0 − best constant QP (hindsight) |    2395 | +1.07 [+0.27, +1.79]    | +1.07 [-1.35, +2.75]    | +0.76 [-2.13, +2.55]     | +0.72, +1.42, +1.08    | case-level only | nan                     |

## Budget QP 26

| claim                                                   | A - B                             |   cases | case CI                | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict         | clip CI (53 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:-----------------------|:------------------------|:-------------------------|:--------------------|:----------------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +4.61 [+3.67, +5.57]   | +4.61 [+3.43, +6.19]    | +3.27 [+1.97, +4.54]     | +3.98, +3.90, +5.95 | holds           | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +6.74 [+5.31, +8.23]   | +6.74 [+4.12, +10.66]   | +6.11 [+3.30, +10.37]    | +3.34, +7.92, +8.95 | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +3.59 [+2.68, +4.48]   | +3.59 [+1.66, +5.05]    | +2.25 [-0.13, +3.60]     | +2.77, +2.99, +5.00 | case-level only | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +3.94 [+3.00, +4.90]   | +3.94 [+2.23, +5.62]    | +3.06 [+0.92, +4.86]     | +0.98, +4.99, +5.83 | holds           | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.13 [-0.28, +0.57]   | +0.13 [-0.72, +0.86]    | -0.01 [-1.02, +0.80]     | +0.09, +0.39, -0.09 | n.s.            | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | -0.41 [-0.71, -0.13]   | -0.41 [-0.82, -0.12]    | -0.38 [-0.77, -0.11]     | -2.15, +1.07, -0.15 | holds           | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     167 | +11.67 [+7.90, +16.85] | nan                     | +11.40 [+5.52, +19.98]   | –                   | holds           | +11.67 [+6.81, +19.63]  |

## Budget QP 30

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict   | clip CI (55 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +5.68 [+4.59, +6.82] | +5.68 [+4.21, +7.63]    | +4.31 [+2.70, +5.99]     | +6.73, +5.16, +5.15 | holds     | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +4.41 [+3.57, +5.32] | +4.41 [+3.07, +6.40]    | +3.80 [+2.36, +5.82]     | +4.19, +4.15, +4.91 | holds     | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +4.93 [+3.99, +5.90] | +4.93 [+3.68, +6.34]    | +3.42 [+1.88, +4.59]     | +5.20, +4.81, +4.78 | holds     | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +3.61 [+2.88, +4.37] | +3.61 [+2.52, +4.86]    | +2.92 [+1.63, +4.09]     | +3.34, +3.45, +4.02 | holds     | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.17 [-0.11, +0.44] | +0.17 [-0.13, +0.45]    | -0.04 [-0.37, +0.19]     | +0.21, +0.20, +0.09 | n.s.      | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | -0.05 [-0.30, +0.18] | -0.05 [-0.41, +0.22]    | -0.11 [-0.49, +0.14]     | +0.37, -0.73, +0.21 | n.s.      | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     153 | +8.24 [+7.12, +9.51] | nan                     | +7.39 [+6.43, +8.30]     | –                   | holds     | +8.24 [+7.16, +9.67]    |

## Budget QP 34

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict         | clip CI (61 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +5.25 [+4.22, +6.33] | +5.25 [+3.56, +7.67]    | +4.10 [+2.39, +6.57]     | +5.80, +5.23, +4.72 | holds           | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +4.30 [+3.38, +5.26] | +4.30 [+2.82, +6.36]    | +3.92 [+2.43, +6.20]     | +3.94, +4.86, +4.11 | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +4.88 [+3.92, +5.84] | +4.88 [+3.59, +6.53]    | +3.78 [+2.48, +5.22]     | +5.00, +4.82, +4.83 | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +4.06 [+3.35, +4.83] | +4.06 [+2.98, +5.51]    | +3.57 [+2.45, +5.17]     | +3.63, +4.35, +4.19 | holds           | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.15 [-0.23, +0.47] | +0.15 [-0.42, +0.59]    | +0.11 [-0.47, +0.52]     | +0.22, -0.07, +0.31 | n.s.            | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.40 [+0.05, +0.80] | +0.40 [-0.05, +0.82]    | +0.22 [-0.23, +0.57]     | +0.57, +0.19, +0.43 | case-level only | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     173 | +7.21 [+5.83, +9.02] | nan                     | +6.38 [+4.85, +8.46]     | –                   | holds           | +7.21 [+5.85, +9.34]    |

## Budget QP 38

| claim                                                   | A - B                             |   cases | case CI               | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict         | clip CI (58 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:----------------------|:------------------------|:-------------------------|:--------------------|:----------------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +5.76 [+4.77, +6.82]  | +5.76 [+4.25, +7.94]    | +4.82 [+3.38, +6.84]     | +5.78, +5.95, +5.55 | holds           | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +5.50 [+4.58, +6.49]  | +5.50 [+3.77, +7.87]    | +5.25 [+3.43, +7.81]     | +4.17, +6.11, +6.23 | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +5.36 [+4.55, +6.20]  | +5.36 [+4.11, +6.99]    | +4.22 [+2.92, +5.68]     | +5.07, +5.90, +5.10 | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +4.69 [+3.94, +5.51]  | +4.69 [+3.35, +6.48]    | +4.43 [+3.02, +6.28]     | +3.74, +5.08, +5.26 | holds           | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.60 [+0.31, +0.90]  | +0.60 [+0.17, +0.95]    | +0.32 [-0.17, +0.65]     | +0.45, +0.50, +0.85 | case-level only | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.55 [+0.30, +0.81]  | +0.55 [+0.17, +0.87]    | +0.42 [+0.03, +0.72]     | +0.35, -0.15, +1.46 | holds           | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     158 | +8.61 [+7.21, +10.43] | nan                     | +7.78 [+6.12, +9.69]     | –                   | holds           | +8.61 [+7.09, +10.56]   |

## Budget QP 42

| claim                                                   | A - B                             |   cases | case CI               | clip CI (98 clusters)   | natural only (clip CI)   | per seed             | verdict         | clip CI (54 clusters)   |
|:--------------------------------------------------------|:----------------------------------|--------:|:----------------------|:------------------------|:-------------------------|:---------------------|:----------------|:------------------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +9.15 [+7.81, +10.50] | +9.15 [+7.22, +11.71]   | +7.94 [+6.02, +10.35]    | +8.10, +11.68, +7.67 | holds           | nan                     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +7.30 [+6.18, +8.46]  | +7.30 [+5.40, +9.75]    | +6.85 [+4.94, +9.39]     | +5.92, +8.23, +7.76  | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +6.96 [+5.93, +8.03]  | +6.96 [+5.43, +8.89]    | +6.03 [+4.43, +7.92]     | +6.24, +9.12, +5.54  | holds           | nan                     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +5.68 [+4.83, +6.63]  | +5.68 [+4.24, +7.53]    | +5.25 [+3.75, +7.17]     | +4.65, +6.35, +6.03  | holds           | nan                     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.93 [+0.59, +1.27]  | +0.93 [+0.53, +1.32]    | +0.66 [+0.17, +1.02]     | +0.54, +0.70, +1.55  | holds           | nan                     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.43 [+0.14, +0.72]  | +0.43 [+0.06, +0.77]    | +0.32 [-0.05, +0.62]     | +0.41, -0.62, +1.52  | case-level only | nan                     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     158 | +8.88 [+7.61, +10.51] | nan                     | +8.54 [+7.13, +10.42]    | –                    | holds           | +8.88 [+7.52, +10.78]   |

## Lookahead by GOP type: stable

| claim              | A - B                             |   cases | case CI              | clip CI (38 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |    1740 | +0.17 [+0.01, +0.31] | +0.17 [-0.28, +0.50]    | +0.17 [-0.28, +0.50]     | -0.08, +0.45, +0.13 | case-level only |

## Lookahead by GOP type: natural cut

| claim              | A - B                             |   cases | case CI              | clip CI (8 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:-----------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     150 | +0.91 [+0.10, +1.76] | +0.91 [-0.35, +1.63]   | +0.91 [-0.35, +1.63]     | +1.36, -0.94, +2.29 | case-level only |

## Lookahead by GOP type: spliced

| claim              | A - B                             |   cases | case CI              | clip CI (60 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     300 | +1.72 [+1.01, +2.36] | +1.72 [+0.77, +2.69]    | –                        | +2.03, +1.01, +2.10 | case-level only |

