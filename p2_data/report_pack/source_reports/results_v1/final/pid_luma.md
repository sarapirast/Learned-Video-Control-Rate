# PID-Lagrangian PPO vs the rule at equal reliability, in luma PSNR (exp_next/exp7/pid_luma.py)

Sara's comparison (repo/p4/rule_margin_sweep.py: the rule on its original tuning at margin 0.96, ~6-7 % of streams > 1 % over, vs her constrained PPO runs, 3 seeds averaged, 8-GOP v1 test streams) with every row rescored from its per-GOP QPs in luma PSNR of pooled MSE (Pavneet's D50 definition). Rows: team repo p4/models/<enc>/ (PID runs) and pavneet_handoff/artifacts/<enc>/v1/results_stream (bc_ppo_lag, rule tuning); read only. No encodes. CIs: her cluster bootstrap (stream_rl.cboot); * = CI excludes 0. Over = % of streams > 1 % over budget (bits only, the same in both conventions).

| enc | L | RL run - rule@0.96 | YUV 6:1:1 (her README) | luma | n | over: RL / rule (%) |
|---|---:|---|---|---|---:|---|
| x264 | 2 | ppo_pid | +0.158 [+0.120, +0.200] * | +0.195 [+0.148, +0.246] * | 2172 | 6.7 / 7.0 |
| x264 | 2 | bc_ppo_pid | +0.165 [+0.118, +0.218] * | +0.190 [+0.133, +0.253] * | 2172 | 5.8 / 7.0 |
| x264 | 2 | bc_ppo_lag | +0.165 [+0.118, +0.220] * | +0.186 [+0.131, +0.250] * | 2172 | 7.4 / 7.0 |
| x264 | 0 | ppo_pid | +0.136 [+0.076, +0.212] * | +0.175 [+0.103, +0.265] * | 2172 | 7.6 / 7.3 |
| x264 | 0 | bc_ppo_lag | +0.170 [+0.103, +0.267] * | +0.198 [+0.114, +0.317] * | 2172 | 7.9 / 7.3 |
| x265 | 2 | ppo_pid | +0.205 [+0.164, +0.266] * | +0.239 [+0.194, +0.308] * | 2172 | 5.3 / 6.2 |
| x265 | 2 | bc_ppo_pid | +0.240 [+0.181, +0.321] * | +0.267 [+0.203, +0.358] * | 2172 | 4.8 / 6.2 |
| x265 | 2 | bc_ppo_lag | +0.251 [+0.193, +0.333] * | +0.281 [+0.217, +0.373] * | 2172 | 5.4 / 6.2 |
| x265 | 0 | ppo_pid | +0.180 [+0.100, +0.291] * | +0.225 [+0.127, +0.359] * | 2172 | 5.1 / 5.9 |
| x265 | 0 | bc_ppo_lag | +0.188 [+0.085, +0.327] * | +0.223 [+0.097, +0.386] * | 2172 | 5.4 / 5.9 |

x264 range over the rows above: YUV +0.14 to +0.17; luma +0.18 to +0.20

x265 range over the rows above: YUV +0.18 to +0.25; luma +0.22 to +0.28

Check passed: every YUV mean reproduces her README table to 3 decimals; the luma tables' bits equal every row's stored bits.
