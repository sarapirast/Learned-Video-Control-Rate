# Exp 7 step 1: reproduce Pavneet's D34 val numbers, x264 (exp_next/exp7/repro.py)

His code (eb08445) and stored policies / rule settings; val, all 1704 cases. Pass = max |new - stored| per row <= 0.005 dB.

| what | val mean (re-run) | val mean (stored) | max abs row diff | pass |
|---|---|---|---|---|
| rule_wide L0 (0.98, 4.5, 3.0) | -0.8654 | -0.8654 | 0.00e+00 | OK |
| rule_wide L2 (0.98, 4.5, 3.0) | -0.6551 | -0.6551 | 0.00e+00 | OK |
| baselines rule L0 (0.98, 4.5, 3.0) | -0.8654 | -0.8654 | 0.00e+00 | OK |
| baselines rule L2 (0.98, 4.5, 3.0) | -0.6551 | -0.6551 | 0.00e+00 | OK |
| bc_L0_s0 | -1.1667 | -1.1667 | 0.00e+00 | OK |
| bc_L0_s1 | -1.1925 | -1.1925 | 0.00e+00 | OK |
| bc_L0_s2 | -1.1698 | -1.1698 | 0.00e+00 | OK |
| bc_L2_s0 | -0.6095 | -0.6095 | 0.00e+00 | OK |
| bc_L2_s1 | -0.6765 | -0.6765 | 0.00e+00 | OK |
| bc_L2_s2 | -0.7228 | -0.7228 | 0.00e+00 | OK |
| bc_ppo_L0_s0 | -0.5941 | -0.5941 | 0.00e+00 | OK |
| bc_ppo_L0_s1 | -0.5394 | -0.5394 | 0.00e+00 | OK |
| bc_ppo_L0_s2 | -0.5520 | -0.5520 | 0.00e+00 | OK |
| bc_ppo_L2_s0 | -0.4042 | -0.4042 | 0.00e+00 | OK |
| bc_ppo_L2_s1 | -0.3902 | -0.3902 | 0.00e+00 | OK |
| bc_ppo_L2_s2 | -0.3936 | -0.3936 | 0.00e+00 | OK |
| bc_ppo_lag_L0_s0 | -0.5926 | -0.5926 | 0.00e+00 | OK |
| bc_ppo_lag_L0_s1 | -0.6308 | -0.6308 | 0.00e+00 | OK |
| bc_ppo_lag_L0_s2 | -0.5853 | -0.5853 | 0.00e+00 | OK |
| bc_ppo_lag_L2_s0 | -0.4305 | -0.4305 | 0.00e+00 | OK |
| bc_ppo_lag_L2_s1 | -0.3913 | -0.3913 | 0.00e+00 | OK |
| bc_ppo_lag_L2_s2 | -0.4538 | -0.4538 | 0.00e+00 | OK |
| ppo_L0_s0 | -0.6104 | -0.6104 | 0.00e+00 | OK |
| ppo_L0_s1 | -0.6128 | -0.6128 | 0.00e+00 | OK |
| ppo_L0_s2 | -0.5940 | -0.5940 | 0.00e+00 | OK |
| ppo_L2_s0 | -0.4079 | -0.4079 | 0.00e+00 | OK |
| ppo_L2_s1 | -0.4106 | -0.4106 | 0.00e+00 | OK |
| ppo_L2_s2 | -0.4134 | -0.4134 | 0.00e+00 | OK |

**ALL REPRODUCE**

