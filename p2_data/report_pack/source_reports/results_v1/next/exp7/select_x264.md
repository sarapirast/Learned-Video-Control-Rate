# Exp 7 Part 1 selection, x264 (exp_next/exp7/select_policy.py)

Val same-clip 8-GOP streams (504 cases, 9 source groups), L = 2, seeds averaged per case. Retuned rule (1.0, 5.0, 0.0625) (val score -0.4995); rule as reported (0.98, 4.5, 3.0) (-0.6225). The retuned rule was tuned on these same streams (in-sample).

| candidate | val score | - retuned rule | - rule as reported | > 1 % over | p90 abs err % | signed err % | seeds |
|---|---|---|---|---|---|---|---|
| ppo | -0.4825 | +0.0170 [-0.098, +0.276] | +0.1400 [+0.010, +0.395] | 14.0% | 10.45 | -3.38 | -0.483 -0.457 -0.508 |
| bc_ppo | -0.4694 | +0.0301 [-0.127, +0.401] | +0.1531 [-0.014, +0.467] | 12.8% | 11.63 | -3.56 | -0.465 -0.461 -0.482 |
| ppo_pid | -0.5484 | -0.0489 [-0.163, +0.191] | +0.0741 [-0.066, +0.361] | 8.1% | 13.33 | -5.02 | -0.565 -0.529 -0.551 |
| bc_ppo_pid | -0.4865 | +0.0129 [-0.140, +0.363] | +0.1360 [-0.030, +0.446] | 7.6% | 12.62 | -4.60 | -0.468 -0.465 -0.527 |
| retuned rule | -0.4995 | | | 22.4% | 7.40 | -1.86 | |
| rule as reported | -0.6225 | | | 12.9% | 10.70 | -3.35 | |

Within 0.01 dB of the best: bc_ppo -> **selected (x264): bc_ppo**; selected - retuned rule +0.0301 -> Part 2 ALLOWED (beats the retuned rule on val)

PID sanity check (Sara: about half the rule's overspends): ppo_pid > 1 % over 8.1% vs rule as reported 12.9% / retuned 22.4%; bc_ppo_pid > 1 % over 7.6% vs rule as reported 12.9% / retuned 22.4%

