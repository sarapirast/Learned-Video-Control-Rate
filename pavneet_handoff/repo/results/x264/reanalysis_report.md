# Re-analysis: clip-level CIs and natural cuts (x264, budgets (30, 38), test)

479 test GOPs in 98 clusters (60 spliced GOPs, each its own cluster). Score differences A − B, seeds averaged per case. 'holds' = the clip-level CI excludes 0 on all cases and on natural (non-spliced) GOPs.

## All budgets

| claim                                                   | A - B                                   |   cases | case CI                 | clip CI (98 clusters)   | natural only (clip CI)   | per seed               | verdict         |
|:--------------------------------------------------------|:----------------------------------------|--------:|:------------------------|:------------------------|:-------------------------|:-----------------------|:----------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0               |     958 | +3.68 [+3.06, +4.37]    | +3.68 [+2.68, +4.62]    | +2.83 [+1.72, +3.60]     | +4.50, +5.18, +1.36    | holds           |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5               |     958 | +1.42 [+0.93, +1.90]    | +1.42 [+0.38, +2.22]    | +1.42 [+0.29, +2.29]     | +0.65, +2.63, +0.98    | holds           |
| PID-Lagrangian beats imitation (k=0)                    | pid fixed:0 − bc fixed:0                |     958 | +3.62 [+3.01, +4.28]    | +3.62 [+2.77, +4.57]    | +2.76 [+1.90, +3.41]     | +4.25, +5.18, +1.43    | holds           |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0           |     958 | +3.30 [+2.69, +3.96]    | +3.30 [+2.31, +4.21]    | +2.30 [+1.17, +3.09]     | +4.05, +4.49, +1.35    | holds           |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5           |     958 | +1.04 [+0.55, +1.56]    | +1.04 [+0.08, +1.95]    | +0.91 [-0.15, +1.96]     | +0.41, +2.00, +0.70    | case-level only |
| feedback control helps imitation (k=0)                  | bc_fb2 fixed:0 − bc fixed:0             |     958 | +0.39 [+0.17, +0.60]    | +0.39 [+0.06, +0.71]    | +0.53 [+0.20, +0.91]     | +0.46, +0.69, +0.01    | holds           |
| constrained RL beats penalty RL (k=5)                   | lagr fixed:5 − cql_ppo fixed:5          |     958 | +3.64 [+3.12, +4.19]    | +3.64 [+2.89, +4.55]    | +3.23 [+2.40, +4.12]     | +5.31, +2.53, +3.08    | holds           |
| PPO fine-tuning beats imitation (k=5)                   | cql_ppo fixed:5 − bc fixed:5            |     958 | -2.22 [-2.73, -1.73]    | -2.22 [-3.32, -1.48]    | -1.81 [-2.80, -1.15]     | -4.66, +0.10, -2.10    | holds           |
| imitation beats offline RL (k=5)                        | bc fixed:5 − cql fixed:5                |     958 | +3.88 [+3.18, +4.63]    | +3.88 [+2.68, +5.79]    | +3.51 [+2.17, +5.47]     | +5.00, +2.44, +4.21    | holds           |
| lookahead: k 0 -> 1                                     | cql_ppo fixed:1 − cql_ppo fixed:0       |     958 | +3.85 [+3.31, +4.43]    | +3.85 [+2.94, +5.02]    | +3.50 [+2.43, +4.69]     | +5.99, +1.49, +4.06    | holds           |
| lookahead: k 1 -> 2                                     | cql_ppo fixed:2 − cql_ppo fixed:1       |     958 | -0.94 [-1.34, -0.56]    | -0.94 [-1.34, -0.50]    | -1.20 [-1.59, -0.85]     | -2.10, -0.55, -0.16    | holds           |
| lookahead: k 2 -> 3                                     | cql_ppo fixed:3 − cql_ppo fixed:2       |     958 | +0.14 [-0.22, +0.51]    | +0.14 [-0.26, +0.55]    | +0.15 [-0.25, +0.54]     | +2.27, +1.67, -3.51    | n.s.            |
| lookahead: k 3 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:3       |     958 | -1.46 [-1.86, -1.06]    | -1.46 [-2.17, -0.97]    | -1.55 [-2.35, -1.05]     | -5.43, -0.81, +1.87    | holds           |
| lookahead: k 3 -> 29 (flat beyond 3)                    | cql_ppo fixed:29 − cql_ppo fixed:3      |     958 | +0.35 [-0.13, +0.85]    | +0.35 [-0.67, +1.06]    | +0.15 [-0.97, +0.90]     | -1.59, -0.26, +2.90    | n.s.            |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0       |     958 | +1.60 [+0.98, +2.22]    | +1.60 [+0.50, +2.78]    | +0.90 [-0.42, +1.98]     | +0.73, +1.80, +2.26    | case-level only |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0             |     958 | +0.17 [-0.09, +0.44]    | +0.17 [-0.09, +0.50]    | -0.15 [-0.43, +0.06]     | -0.73, +0.84, +0.41    | n.s.            |
| learned policy beats the hand lookahead rule (k=5)      | cql_ppo fixed:5 − la_rule k=5           |     958 | +2.37 [+1.62, +3.14]    | +2.37 [+0.98, +3.76]    | +2.35 [+0.92, +3.91]     | +0.16, +4.58, +2.37    | holds           |
| 3-seed ensemble helps                                   | ensemble fixed:5 − cql_ppo fixed:5      |     958 | +3.01 [+2.55, +3.51]    | +3.01 [+2.36, +3.97]    | +2.75 [+2.12, +3.73]     | –                      | holds           |
| first-pass features matter                              | cql_ppo fixed:5 − cql_ppo fixed:5 no-fp |     958 | +1.50 [+0.80, +2.23]    | +1.50 [+0.38, +2.90]    | +1.55 [+0.35, +3.06]     | -1.53, +3.74, +2.30    | holds           |
| cut-triggered lookahead beats none                      | cql_ppo cut_trig:5 − cql_ppo fixed:0    |     958 | +2.84 [+2.32, +3.41]    | +2.84 [+1.98, +3.97]    | +2.21 [+1.21, +3.24]     | +5.08, -0.92, +4.36    | holds           |
| scene-truncated window vs fixed k=5                     | cql_ppo scene_trunc:5 − cql_ppo fixed:5 |     958 | +2.64 [+2.22, +3.10]    | +2.64 [+2.10, +3.33]    | +2.46 [+1.91, +3.18]     | +4.95, -0.19, +3.16    | holds           |
| gap: search vs best learner                             | hindsight search − lagr fixed:5         |     958 | +5.88 [+5.47, +6.34]    | +5.88 [+5.14, +6.64]    | +5.44 [+4.55, +6.23]     | –                      | holds           |
| constrained RL vs the encoder's ABR (same budget)       | lagr fixed:0 − own abr                  |     958 | +43.60 [+40.49, +46.68] | +43.60 [+35.50, +54.52] | +44.86 [+35.70, +57.82]  | +43.96, +44.04, +42.80 | holds           |
| constrained RL vs the encoder's two-pass (same budget)  | lagr fixed:5 − own 2pass                |     948 | +7.59 [+6.89, +8.32]    | +7.59 [+6.41, +8.78]    | +7.96 [+6.81, +9.35]     | +7.06, +8.67, +7.03    | holds           |
| constrained RL vs two-pass with the encoder's defaults  | lagr fixed:5 − own 2pass +AQ            |     948 | +12.80 [+11.06, +14.58] | +12.80 [+8.64, +16.28]  | +13.56 [+8.90, +17.63]   | +12.27, +13.88, +12.25 | holds           |
| constrained RL vs the causal feedback rule              | lagr fixed:0 − rule k=0                 |     958 | +19.04 [+17.82, +20.27] | +19.04 [+16.67, +22.18] | +18.22 [+15.63, +21.58]  | +19.40, +19.48, +18.24 | holds           |
| imitation + feedback vs the causal feedback rule        | bc_fb2 fixed:0 − rule k=0               |     958 | +15.74 [+14.58, +16.90] | +15.74 [+13.42, +19.00] | +15.92 [+13.33, +19.70]  | +15.36, +14.99, +16.88 | holds           |

## Lookahead by GOP type: stable

| claim              | A - B                             |   cases | case CI              | clip CI (38 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     698 | +0.68 [+0.06, +1.33] | +0.68 [-0.62, +1.95]    | +0.68 [-0.62, +1.95]     | +0.33, +0.29, +1.40 | case-level only |

## Lookahead by GOP type: natural cut

| claim              | A - B                             |   cases | case CI              | clip CI (7 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:-----------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |      58 | +4.71 [+2.10, +7.40] | +4.71 [-0.92, +6.02]   | +4.71 [-0.92, +6.02]     | +3.26, +6.04, +4.83 | case-level only |

## Lookahead by GOP type: spliced

| claim              | A - B                             |   cases | case CI              | clip CI (60 clusters)   | natural only (clip CI)   | per seed             | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:---------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     120 | +6.47 [+3.66, +9.27] | +6.47 [+2.94, +10.15]   | –                        | +2.16, +7.04, +10.20 | case-level only |

