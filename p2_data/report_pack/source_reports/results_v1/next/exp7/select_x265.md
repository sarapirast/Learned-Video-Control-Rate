# Exp 7 Part 1 selection, x265 (exp_next/exp7/select_policy.py)

Val same-clip 8-GOP streams (504 cases, 9 source groups), L = 2, seeds averaged per case. Retuned rule (0.99, 4.5, 0.0625) (val score -0.2937); rule as reported (0.98, 4.5, 6.0) (-0.4526). The retuned rule was tuned on these same streams (in-sample).

| candidate | val score | - retuned rule | - rule as reported | > 1 % over | p90 abs err % | signed err % | seeds |
|---|---|---|---|---|---|---|---|
| ppo | -0.3730 | -0.0793 [-0.172, +0.077] | +0.0795 [-0.038, +0.305] | 10.4% | 8.46 | -2.87 | -0.371 -0.369 -0.379 |
| bc_ppo | -0.3730 | -0.0793 [-0.180, +0.118] | +0.0796 [-0.041, +0.294] | 11.4% | 9.64 | -3.03 | -0.358 -0.385 -0.376 |
| ppo_pid | -0.4544 | -0.1607 [-0.284, +0.044] | -0.0018 [-0.148, +0.252] | 4.5% | 11.25 | -4.86 | -0.453 -0.459 -0.451 |
| bc_ppo_pid | -0.3977 | -0.1040 [-0.216, +0.086] | +0.0549 [-0.080, +0.287] | 5.9% | 11.31 | -4.22 | -0.396 -0.424 -0.373 |
| retuned rule | -0.2937 | | | 10.5% | 5.44 | -1.65 | |
| rule as reported | -0.4526 | | | 7.7% | 7.52 | -3.00 | |

Within 0.01 dB of the best: ppo, bc_ppo -> **selected (x265): ppo**; selected - retuned rule -0.0793 -> Part 2 SKIPPED (does not beat the retuned rule on val)

PID sanity check (Sara: about half the rule's overspends): ppo_pid > 1 % over 4.5% vs rule as reported 7.7% / retuned 10.5%; bc_ppo_pid > 1 % over 5.9% vs rule as reported 7.7% / retuned 10.5%

