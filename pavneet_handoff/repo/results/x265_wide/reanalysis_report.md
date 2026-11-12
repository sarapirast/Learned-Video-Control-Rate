# Re-analysis: clip-level CIs and natural cuts (x265, budgets (26, 30, 34, 38, 42), test)

479 test GOPs in 98 clusters (60 spliced GOPs, each its own cluster). Score differences A − B, seeds averaged per case. 'holds' = the clip-level CI excludes 0 on all cases and on natural (non-spliced) GOPs.

## All budgets

| claim                                                   | A - B                              |   cases | case CI                 | clip CI (98 clusters)   | natural only (clip CI)   | per seed               | verdict         |
|:--------------------------------------------------------|:-----------------------------------|--------:|:------------------------|:------------------------|:-------------------------|:-----------------------|:----------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0          |    2395 | +3.46 [+3.10, +3.82]    | +3.46 [+2.58, +4.24]    | +2.91 [+1.95, +3.68]     | +3.66, +3.21, +3.50    | holds           |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5          |    2395 | +1.53 [+1.30, +1.77]    | +1.53 [+0.87, +2.09]    | +1.57 [+0.89, +2.16]     | +1.09, +2.11, +1.39    | holds           |
| PID-Lagrangian beats imitation (k=0)                    | pid fixed:0 − bc fixed:0           |    2395 | +3.21 [+2.88, +3.55]    | +3.21 [+2.31, +4.01]    | +2.84 [+1.87, +3.70]     | +3.62, +2.70, +3.31    | holds           |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0      |    2395 | +3.76 [+3.39, +4.15]    | +3.76 [+2.82, +4.60]    | +3.06 [+1.96, +3.92]     | +3.84, +3.60, +3.84    | holds           |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5      |    2395 | +1.64 [+1.41, +1.87]    | +1.64 [+0.97, +2.23]    | +1.54 [+0.80, +2.19]     | +1.05, +2.21, +1.65    | holds           |
| feedback control helps imitation (k=0)                  | bc_fb2 fixed:0 − bc fixed:0        |    2395 | -0.30 [-0.46, -0.17]    | -0.30 [-0.53, -0.08]    | -0.15 [-0.32, +0.08]     | -0.18, -0.39, -0.34    | case-level only |
| constrained RL beats penalty RL (k=5)                   | lagr fixed:5 − cql_ppo fixed:5     |    2395 | +0.02 [-0.17, +0.21]    | +0.02 [-0.29, +0.37]    | -0.16 [-0.49, +0.13]     | -0.34, +0.64, -0.25    | n.s.            |
| PPO fine-tuning beats imitation (k=5)                   | cql_ppo fixed:5 − bc fixed:5       |    2395 | +1.51 [+1.28, +1.75]    | +1.51 [+0.93, +1.93]    | +1.74 [+1.22, +2.17]     | +1.42, +1.47, +1.64    | holds           |
| lookahead: k 0 -> 1                                     | cql_ppo fixed:1 − cql_ppo fixed:0  |    2395 | +0.29 [+0.05, +0.54]    | +0.29 [-0.13, +0.72]    | -0.17 [-0.64, +0.13]     | -0.24, +0.52, +0.58    | case-level only |
| lookahead: k 1 -> 2                                     | cql_ppo fixed:2 − cql_ppo fixed:1  |    2395 | -0.50 [-0.70, -0.30]    | -0.50 [-0.83, -0.21]    | -0.22 [-0.43, +0.08]     | +0.57, -0.37, -1.69    | case-level only |
| lookahead: k 2 -> 3                                     | cql_ppo fixed:3 − cql_ppo fixed:2  |    2395 | +0.94 [+0.72, +1.17]    | +0.94 [+0.53, +1.32]    | +0.69 [+0.31, +0.96]     | +0.79, +0.91, +1.14    | holds           |
| lookahead: k 3 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:3  |    2395 | +0.38 [+0.19, +0.58]    | +0.38 [+0.06, +0.79]    | +0.28 [-0.03, +0.69]     | +0.25, +0.15, +0.74    | case-level only |
| lookahead: k 3 -> 29 (flat beyond 3)                    | cql_ppo fixed:29 − cql_ppo fixed:3 |    2395 | -0.96 [-1.21, -0.70]    | -0.96 [-1.48, -0.42]    | -1.02 [-1.50, -0.58]     | +0.07, -1.15, -1.79    | holds           |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0  |    2395 | +1.11 [+0.87, +1.37]    | +1.11 [+0.72, +1.60]    | +0.59 [+0.19, +0.86]     | +1.36, +1.21, +0.77    | holds           |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0        |    2395 | -0.06 [-0.21, +0.10]    | -0.06 [-0.33, +0.27]    | -0.30 [-0.56, -0.11]     | -0.41, +0.34, -0.11    | n.s.            |
| learned policy beats the hand lookahead rule (k=5)      | cql_ppo fixed:5 − la_rule k=5      |    2395 | +6.80 [+6.36, +7.22]    | +6.80 [+5.59, +8.29]    | +6.36 [+5.01, +7.86]     | +7.04, +6.37, +6.97    | holds           |
| gap: search vs best learner                             | hindsight search − lagr fixed:5    |    2395 | +6.20 [+5.96, +6.47]    | +6.20 [+5.63, +6.87]    | +5.69 [+5.02, +6.28]     | –                      | holds           |
| constrained RL vs the encoder's ABR (same budget)       | lagr fixed:0 − own abr             |    2395 | +33.19 [+31.80, +34.61] | +33.19 [+28.04, +40.15] | +32.35 [+26.64, +39.93]  | +33.43, +32.99, +33.14 | holds           |
| constrained RL vs the encoder's two-pass (same budget)  | lagr fixed:5 − own 2pass           |    2395 | +24.73 [+23.54, +25.93] | +24.73 [+20.34, +29.69] | +26.93 [+22.30, +33.06]  | +24.63, +24.93, +24.64 | holds           |
| constrained RL vs two-pass with the encoder's defaults  | lagr fixed:5 − own 2pass +AQ       |    2395 | +21.60 [+20.42, +22.81] | +21.60 [+17.75, +24.77] | +22.90 [+18.81, +26.60]  | +21.49, +21.80, +21.51 | holds           |
| constrained RL vs the causal feedback rule              | lagr fixed:0 − rule k=0            |    2395 | +16.73 [+15.93, +17.53] | +16.73 [+14.29, +20.29] | +16.06 [+13.43, +19.82]  | +16.97, +16.53, +16.69 | holds           |
| imitation + feedback vs the causal feedback rule        | bc_fb2 fixed:0 − rule k=0          |    2395 | +12.97 [+12.25, +13.70] | +12.97 [+10.36, +16.88] | +13.00 [+10.09, +17.40]  | +13.13, +12.93, +12.85 | holds           |

## Budget QP 26

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +2.32 [+1.72, +2.95] | +2.32 [+1.60, +3.16]    | +1.82 [+1.04, +2.67]     | +2.94, +2.08, +1.95 | holds           |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +1.22 [+0.76, +1.69] | +1.22 [+0.45, +1.78]    | +1.19 [+0.35, +1.78]     | +1.22, +1.65, +0.79 | holds           |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +2.35 [+1.80, +2.92] | +2.35 [+1.56, +3.14]    | +1.86 [+0.92, +2.71]     | +2.59, +2.43, +2.04 | holds           |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +1.32 [+0.87, +1.81] | +1.32 [+0.45, +1.94]    | +1.11 [+0.12, +1.78]     | +1.22, +1.93, +0.83 | holds           |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.64 [+0.19, +1.12] | +0.64 [+0.15, +1.20]    | +0.31 [-0.22, +0.75]     | +2.12, +0.12, -0.32 | case-level only |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.45 [+0.11, +0.83] | +0.45 [-0.00, +0.88]    | +0.10 [-0.41, +0.49]     | +0.31, +0.62, +0.40 | case-level only |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +5.18 [+4.72, +5.67] | +5.18 [+4.36, +6.03]    | +4.98 [+3.99, +5.94]     | –                   | holds           |

## Budget QP 30

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +2.94 [+2.13, +3.74] | +2.94 [+1.70, +4.24]    | +2.60 [+1.22, +3.93]     | +2.87, +3.11, +2.83 | holds           |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +1.31 [+0.80, +1.86] | +1.31 [+0.43, +2.32]    | +1.33 [+0.37, +2.49]     | +0.96, +1.83, +1.13 | holds           |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +3.13 [+2.26, +4.03] | +3.13 [+1.82, +4.48]    | +2.59 [+1.13, +3.94]     | +2.94, +3.21, +3.23 | holds           |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +1.23 [+0.75, +1.76] | +1.23 [+0.33, +2.20]    | +1.20 [+0.20, +2.28]     | +0.82, +1.63, +1.24 | holds           |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.62 [+0.17, +1.11] | +0.62 [+0.16, +1.11]    | +0.24 [-0.22, +0.57]     | +1.48, +0.63, -0.23 | case-level only |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | +0.25 [-0.03, +0.53] | +0.25 [-0.03, +0.65]    | +0.03 [-0.17, +0.32]     | +0.18, +0.55, +0.02 | n.s.            |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +6.11 [+5.66, +6.63] | +6.11 [+5.43, +6.82]    | +5.68 [+4.85, +6.33]     | –                   | holds           |

## Budget QP 34

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +2.93 [+2.12, +3.69] | +2.93 [+1.86, +3.90]    | +2.30 [+1.08, +3.28]     | +3.16, +2.51, +3.11 | holds     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +1.05 [+0.53, +1.61] | +1.05 [+0.20, +1.73]    | +1.24 [+0.42, +1.96]     | +0.61, +1.50, +1.05 | holds     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +3.45 [+2.56, +4.36] | +3.45 [+2.24, +4.61]    | +2.62 [+1.25, +3.78]     | +3.75, +3.18, +3.43 | holds     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +1.21 [+0.71, +1.75] | +1.21 [+0.38, +1.92]    | +1.23 [+0.37, +2.00]     | +0.42, +1.80, +1.42 | holds     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +0.82 [+0.30, +1.34] | +0.82 [+0.37, +1.38]    | +0.39 [+0.00, +0.66]     | +0.60, +0.85, +1.01 | holds     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | -0.03 [-0.37, +0.35] | -0.03 [-0.35, +0.42]    | -0.23 [-0.52, +0.13]     | -0.39, +0.37, -0.07 | n.s.      |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +6.15 [+5.54, +6.87] | +6.15 [+5.50, +7.04]    | +5.38 [+4.68, +5.92]     | –                   | holds     |

## Budget QP 38

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +3.71 [+2.84, +4.57] | +3.71 [+2.65, +4.56]    | +3.16 [+1.97, +3.97]     | +3.67, +3.18, +4.27 | holds     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +1.38 [+0.87, +1.91] | +1.38 [+0.68, +2.10]    | +1.34 [+0.64, +2.07]     | +0.68, +1.92, +1.55 | holds     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +4.21 [+3.29, +5.20] | +4.21 [+3.06, +5.16]    | +3.38 [+2.01, +4.30]     | +4.14, +3.70, +4.80 | holds     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +1.57 [+1.04, +2.12] | +1.57 [+0.85, +2.41]    | +1.33 [+0.56, +2.17]     | +0.68, +1.93, +2.12 | holds     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +1.07 [+0.57, +1.60] | +1.07 [+0.56, +1.64]    | +0.49 [+0.02, +0.83]     | +0.50, +1.62, +1.08 | holds     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | -0.48 [-0.82, -0.14] | -0.48 [-0.84, -0.10]    | -0.75 [-1.12, -0.50]     | -0.91, +0.03, -0.57 | holds     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +6.57 [+6.04, +7.14] | +6.57 [+5.88, +7.40]    | +6.09 [+5.30, +6.87]     | –                   | holds     |

## Budget QP 42

| claim                                                   | A - B                             |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:--------------------------------------------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0         |     479 | +5.38 [+4.43, +6.36] | +5.38 [+4.36, +6.49]    | +4.66 [+3.62, +5.55]     | +5.65, +5.15, +5.35 | holds     |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5         |     479 | +2.68 [+2.07, +3.29] | +2.68 [+1.76, +3.37]    | +2.77 [+1.86, +3.51]     | +1.97, +3.64, +2.44 | holds     |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0     |     479 | +5.65 [+4.70, +6.61] | +5.65 [+4.58, +6.80]    | +4.84 [+3.73, +5.87]     | +5.79, +5.46, +5.69 | holds     |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5     |     479 | +2.86 [+2.26, +3.49] | +2.86 [+1.89, +3.70]    | +2.81 [+1.80, +3.71]     | +2.13, +3.79, +2.67 | holds     |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0 |     479 | +2.41 [+1.71, +3.20] | +2.41 [+1.73, +3.20]    | +1.48 [+0.74, +2.00]     | +2.12, +2.81, +2.30 | holds     |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0       |     479 | -0.47 [-0.83, -0.10] | -0.47 [-0.95, -0.06]    | -0.65 [-1.17, -0.29]     | -1.23, +0.12, -0.31 | holds     |
| gap: search vs best learner                             | hindsight search − lagr fixed:5   |     479 | +7.02 [+6.44, +7.64] | +7.02 [+6.31, +7.96]    | +6.30 [+5.64, +7.01]     | –                   | holds     |

## Lookahead by GOP type: stable

| claim              | A - B                             |   cases | case CI              | clip CI (38 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |    1740 | +0.30 [+0.15, +0.44] | +0.30 [+0.09, +0.53]    | +0.30 [+0.09, +0.53]     | +0.53, +0.28, +0.08 | holds     |

## Lookahead by GOP type: natural cut

| claim              | A - B                             |   cases | case CI              | clip CI (8 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:-----------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     150 | +2.98 [+1.39, +4.95] | +2.98 [-2.42, +5.02]   | +2.98 [-2.42, +5.02]     | +5.28, -0.66, +4.33 | case-level only |

## Lookahead by GOP type: spliced

| claim              | A - B                             |   cases | case CI              | clip CI (60 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     300 | +4.80 [+3.47, +6.24] | +4.80 [+2.53, +7.34]    | –                        | +3.14, +6.80, +4.47 | case-level only |

## Training on 5 vs 2 budgets (QP 30/38 test cases)

| claim                                    | A - B                                                     |   cases | case CI              | clip CI (98 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-----------------------------------------|:----------------------------------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| 5- vs 2-budget training: cql_ppo fixed:0 | cql_ppo fixed:0 [5 budgets] − cql_ppo fixed:0 [2 budgets] |     958 | +2.68 [+2.17, +3.19] | +2.68 [+1.68, +3.64]    | +2.65 [+1.51, +3.66]     | +1.81, +2.00, +4.22 | holds           |
| 5- vs 2-budget training: cql_ppo fixed:5 | cql_ppo fixed:5 [5 budgets] − cql_ppo fixed:5 [2 budgets] |     958 | +0.78 [+0.50, +1.06] | +0.78 [+0.42, +1.17]    | +0.72 [+0.33, +1.10]     | +1.23, -0.83, +1.94 | holds           |
| 5- vs 2-budget training: bc fixed:5      | bc fixed:5 [5 budgets] − bc fixed:5 [2 budgets]           |     958 | -0.92 [-1.18, -0.64] | -0.92 [-1.33, -0.54]    | -0.97 [-1.43, -0.61]     | -0.18, -1.60, -0.97 | holds           |
| 5- vs 2-budget training: lagr fixed:5    | lagr fixed:5 [5 budgets] − lagr fixed:5 [2 budgets]       |     958 | -0.76 [-0.99, -0.46] | -0.76 [-1.03, -0.37]    | -0.97 [-1.21, -0.76]     | -1.05, -0.51, -0.71 | holds           |
| 5- vs 2-budget training: pid fixed:5     | pid fixed:5 [5 budgets] − pid fixed:5 [2 budgets]         |     958 | +0.28 [+0.07, +0.49] | +0.28 [-0.03, +0.74]    | +0.11 [-0.19, +0.55]     | +0.46, +0.15, +0.22 | case-level only |

