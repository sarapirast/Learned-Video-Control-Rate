# Exp 7 step 1: reproduce Pavneet's D34 val numbers, x265 (exp_next/exp7/repro.py)

His code (eb08445) and stored policies / rule settings; val, all 1704 cases. Pass = max |new - stored| per row <= 0.005 dB.

| what | val mean (re-run) | val mean (stored) | max abs row diff | pass |
|---|---|---|---|---|
| rule_wide L0 (0.98, 4.0, 3.0) | -0.7728 | -0.7728 | 0.00e+00 | OK |
| rule_wide L2 (0.98, 4.5, 6.0) | -0.5102 | -0.5102 | 0.00e+00 | OK |
| baselines rule L0 (0.98, 4.5, 3.0) | -0.7876 | -0.7876 | 0.00e+00 | OK |
| baselines rule L2 (0.98, 4.5, 3.0) | -0.5123 | -0.5123 | 0.00e+00 | OK |
| bc_L0_s0 | -1.0250 | -1.0250 | 0.00e+00 | OK |
| bc_L0_s1 | -1.0483 | -1.0483 | 0.00e+00 | OK |
| bc_L0_s2 | -1.1459 | -1.1459 | 0.00e+00 | OK |
| bc_L2_s0 | -0.5507 | -0.5507 | 0.00e+00 | OK |
| bc_L2_s1 | -0.6027 | -0.6027 | 0.00e+00 | OK |
| bc_L2_s2 | -0.5627 | -0.5627 | 0.00e+00 | OK |
| bc_ppo_L0_s0 | -0.5104 | -0.5104 | 0.00e+00 | OK |
| bc_ppo_L0_s1 | -0.5180 | -0.5180 | 0.00e+00 | OK |
| bc_ppo_L0_s2 | -0.5362 | -0.5362 | 0.00e+00 | OK |
| bc_ppo_L2_s0 | -0.2859 | -0.2859 | 0.00e+00 | OK |
| bc_ppo_L2_s1 | -0.2930 | -0.2930 | 0.00e+00 | OK |
| bc_ppo_L2_s2 | -0.2895 | -0.2895 | 0.00e+00 | OK |
| bc_ppo_lag_L0_s0 | -0.5557 | -0.5557 | 0.00e+00 | OK |
| bc_ppo_lag_L0_s1 | -0.5909 | -0.5909 | 0.00e+00 | OK |
| bc_ppo_lag_L0_s2 | -0.5668 | -0.5668 | 0.00e+00 | OK |
| bc_ppo_lag_L2_s0 | -0.2995 | -0.2995 | 0.00e+00 | OK |
| bc_ppo_lag_L2_s1 | -0.3003 | -0.3003 | 0.00e+00 | OK |
| bc_ppo_lag_L2_s2 | -0.2795 | -0.2795 | 0.00e+00 | OK |
| ppo_L0_s0 | -0.5184 | -0.5184 | 0.00e+00 | OK |
| ppo_L0_s1 | -0.5854 | -0.5854 | 0.00e+00 | OK |
| ppo_L0_s2 | -0.5444 | -0.5444 | 0.00e+00 | OK |
| ppo_L2_s0 | -0.3090 | -0.3090 | 0.00e+00 | OK |
| ppo_L2_s1 | -0.2859 | -0.2859 | 0.00e+00 | OK |
| ppo_L2_s2 | -0.3094 | -0.3094 | 0.00e+00 | OK |

**ALL REPRODUCE**

