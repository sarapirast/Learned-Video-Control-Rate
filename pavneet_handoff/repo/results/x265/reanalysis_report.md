# Re-analysis: clip-level CIs and natural cuts (x265, budgets (30, 38), test)

479 test GOPs in 98 clusters (60 spliced GOPs, each its own cluster). Score differences A − B, seeds averaged per case. 'holds' = the clip-level CI excludes 0 on all cases and on natural (non-spliced) GOPs.

## All budgets

| claim                                                   | A - B                                   |   cases | case CI                 | clip CI (98 clusters)   | natural only (clip CI)   | per seed               | verdict         |
|:--------------------------------------------------------|:----------------------------------------|--------:|:------------------------|:------------------------|:-------------------------|:-----------------------|:----------------|
| constrained RL beats imitation (k=0)                    | lagr fixed:0 − bc fixed:0               |     958 | +2.68 [+2.21, +3.17]    | +2.68 [+1.89, +3.44]    | +2.39 [+1.48, +3.17]     | +3.27, +2.23, +2.55    | holds           |
| constrained RL beats imitation (k=5)                    | lagr fixed:5 − bc fixed:5               |     958 | +1.19 [+0.78, +1.64]    | +1.19 [+0.49, +1.82]    | +1.33 [+0.69, +1.98]     | +1.70, +0.79, +1.08    | holds           |
| PID-Lagrangian beats imitation (k=0)                    | pid fixed:0 − bc fixed:0                |     958 | +2.78 [+2.24, +3.30]    | +2.78 [+2.00, +3.54]    | +2.46 [+1.57, +3.23]     | +4.52, +1.82, +2.00    | holds           |
| constrained RL beats imitation + feedback control (k=0) | lagr fixed:0 − bc_fb2 fixed:0           |     958 | +2.79 [+2.31, +3.30]    | +2.79 [+2.00, +3.58]    | +2.28 [+1.33, +3.03]     | +3.22, +2.34, +2.80    | holds           |
| constrained RL beats imitation + feedback control (k=5) | lagr fixed:5 − bc_fb2 fixed:5           |     958 | +1.36 [+0.96, +1.78]    | +1.36 [+0.63, +2.01]    | +1.47 [+0.79, +2.16]     | +1.80, +0.99, +1.28    | holds           |
| feedback control helps imitation (k=0)                  | bc_fb2 fixed:0 − bc fixed:0             |     958 | -0.10 [-0.32, +0.09]    | -0.10 [-0.39, +0.13]    | +0.11 [-0.05, +0.35]     | +0.05, -0.11, -0.25    | n.s.            |
| constrained RL beats penalty RL (k=5)                   | lagr fixed:5 − cql_ppo fixed:5          |     958 | +1.47 [+1.15, +1.82]    | +1.47 [+1.02, +1.98]    | +1.38 [+0.89, +1.92]     | +1.74, +0.19, +2.49    | holds           |
| PPO fine-tuning beats imitation (k=5)                   | cql_ppo fixed:5 − bc fixed:5            |     958 | -0.28 [-0.66, +0.10]    | -0.28 [-0.94, +0.22]    | -0.05 [-0.65, +0.45]     | -0.04, +0.60, -1.41    | n.s.            |
| imitation beats offline RL (k=5)                        | bc fixed:5 − cql fixed:5                |     958 | +5.54 [+4.60, +6.56]    | +5.54 [+3.59, +8.77]    | +5.19 [+3.11, +8.68]     | +5.67, +5.24, +5.70    | holds           |
| lookahead: k 0 -> 1                                     | cql_ppo fixed:1 − cql_ppo fixed:0       |     958 | +1.56 [+1.13, +1.99]    | +1.56 [+0.63, +2.34]    | +1.18 [+0.02, +2.06]     | +2.25, +3.44, -1.00    | holds           |
| lookahead: k 1 -> 2                                     | cql_ppo fixed:2 − cql_ppo fixed:1       |     958 | +1.51 [+1.21, +1.81]    | +1.51 [+1.11, +2.00]    | +1.60 [+1.20, +2.16]     | -0.67, -0.50, +5.69    | holds           |
| lookahead: k 2 -> 3                                     | cql_ppo fixed:3 − cql_ppo fixed:2       |     958 | +0.29 [+0.04, +0.55]    | +0.29 [-0.00, +0.59]    | +0.26 [+0.04, +0.49]     | +0.56, +0.49, -0.18    | case-level only |
| lookahead: k 3 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:3       |     958 | -0.61 [-0.92, -0.33]    | -0.61 [-0.98, -0.19]    | -0.75 [-1.12, -0.36]     | -0.57, +0.54, -1.81    | holds           |
| lookahead: k 3 -> 29 (flat beyond 3)                    | cql_ppo fixed:29 − cql_ppo fixed:3      |     958 | -1.73 [-2.12, -1.32]    | -1.73 [-2.34, -1.19]    | -1.64 [-2.18, -1.13]     | -0.95, -3.21, -1.02    | holds           |
| lookahead: k 0 -> 5                                     | cql_ppo fixed:5 − cql_ppo fixed:0       |     958 | +2.74 [+2.22, +3.29]    | +2.74 [+1.79, +3.64]    | +2.30 [+1.15, +3.20]     | +1.57, +3.96, +2.71    | holds           |
| lookahead for constrained RL: k 0 -> 5                  | lagr fixed:5 − lagr fixed:0             |     958 | +0.59 [+0.29, +0.89]    | +0.59 [+0.34, +0.89]    | +0.44 [+0.22, +0.65]     | +1.33, +0.23, +0.21    | holds           |
| learned policy beats the hand lookahead rule (k=5)      | cql_ppo fixed:5 − la_rule k=5           |     958 | +5.99 [+5.32, +6.67]    | +5.99 [+4.77, +7.48]    | +5.72 [+4.41, +7.29]     | +5.89, +7.16, +4.93    | holds           |
| 3-seed ensemble helps                                   | ensemble fixed:5 − cql_ppo fixed:5      |     958 | +1.04 [+0.72, +1.38]    | +1.04 [+0.69, +1.49]    | +0.70 [+0.33, +1.04]     | –                      | holds           |
| first-pass features matter                              | cql_ppo fixed:5 − cql_ppo fixed:5 no-fp |     958 | +4.45 [+3.90, +5.01]    | +4.45 [+3.42, +5.80]    | +4.07 [+2.91, +5.43]     | +5.42, +7.28, +0.66    | holds           |
| cut-triggered lookahead beats none                      | cql_ppo cut_trig:5 − cql_ppo fixed:0    |     958 | +2.58 [+2.15, +3.01]    | +2.58 [+1.80, +3.23]    | +2.39 [+1.49, +3.02]     | +2.15, +2.11, +3.49    | holds           |
| scene-truncated window vs fixed k=5                     | cql_ppo scene_trunc:5 − cql_ppo fixed:5 |     958 | +0.43 [+0.13, +0.74]    | +0.43 [+0.15, +0.80]    | +0.30 [+0.04, +0.60]     | +1.34, +0.35, -0.41    | holds           |
| gap: search vs best learner                             | hindsight search − lagr fixed:5         |     958 | +5.58 [+5.18, +6.02]    | +5.58 [+5.00, +6.32]    | +4.92 [+4.26, +5.39]     | –                      | holds           |
| constrained RL vs the encoder's ABR (same budget)       | lagr fixed:0 − own abr                  |     958 | +32.05 [+29.79, +34.24] | +32.05 [+26.80, +39.08] | +31.64 [+25.79, +39.65]  | +31.48, +32.29, +32.39 | holds           |
| constrained RL vs the encoder's two-pass (same budget)  | lagr fixed:5 − own 2pass                |     958 | +23.70 [+21.98, +25.44] | +23.70 [+19.38, +28.86] | +25.83 [+21.27, +32.30]  | +23.86, +23.58, +23.66 | holds           |
| constrained RL vs two-pass with the encoder's defaults  | lagr fixed:5 − own 2pass +AQ            |     958 | +21.23 [+19.43, +23.04] | +21.23 [+16.91, +24.53] | +22.68 [+18.11, +26.46]  | +21.39, +21.11, +21.19 | holds           |
| constrained RL vs the causal feedback rule              | lagr fixed:0 − rule k=0                 |     958 | +16.90 [+15.61, +18.16] | +16.90 [+14.19, +20.74] | +16.23 [+13.32, +20.32]  | +16.32, +17.14, +17.23 | holds           |
| imitation + feedback vs the causal feedback rule        | bc_fb2 fixed:0 − rule k=0               |     958 | +14.11 [+12.93, +15.34] | +14.11 [+11.37, +18.17] | +13.95 [+10.97, +18.48]  | +13.10, +14.80, +14.43 | holds           |

## Lookahead by GOP type: stable

| claim              | A - B                             |   cases | case CI              | clip CI (38 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     696 | +1.93 [+1.42, +2.45] | +1.93 [+0.96, +2.83]    | +1.93 [+0.96, +2.83]     | +1.11, +3.33, +1.34 | holds     |

## Lookahead by GOP type: natural cut

| claim              | A - B                             |   cases | case CI              | clip CI (8 clusters)   | natural only (clip CI)   | per seed            | verdict   |
|:-------------------|:----------------------------------|--------:|:---------------------|:-----------------------|:-------------------------|:--------------------|:----------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |      60 | +5.88 [+3.08, +8.96] | +5.88 [+0.55, +7.23]   | +5.88 [+0.55, +7.23]     | +3.33, +7.46, +6.84 | holds     |

## Lookahead by GOP type: spliced

| claim              | A - B                             |   cases | case CI              | clip CI (60 clusters)   | natural only (clip CI)   | per seed            | verdict         |
|:-------------------|:----------------------------------|--------:|:---------------------|:------------------------|:-------------------------|:--------------------|:----------------|
| lookahead k 0 -> 5 | cql_ppo fixed:5 − cql_ppo fixed:0 |     120 | +5.87 [+3.52, +8.24] | +5.87 [+2.79, +8.76]    | –                        | +3.24, +6.28, +8.10 | case-level only |

