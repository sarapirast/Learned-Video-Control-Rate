# Exp 7 stream level in luma PSNR (exp_next/exp7/luma_rescore.py)

The sealed Exp 7 test rows (results_v1/final/exp7_test_<enc>.pkl) rescored from their stored per-GOP QPs in luma PSNR of pooled MSE, the definition of Pavneet's D50 luma stream rows (own_rc_stream_v1.rescore_luma). No encodes. Policy = the selected stream policy (x264 bc_ppo L2, x265 ppo L2), 3 seeds averaged per stream; retuned rule = rule A (rule_8_<enc>_v2, L=2); rule as reported = Pavneet's D34 rule (rule_wide). 95 % cluster bootstrap over source groups; * = CI excludes 0. Over = streams > 1 % over budget.

| enc | streams | comparison | YUV 6:1:1 (as reported) | luma | n | over: policy / rule (%) |
|---|---|---|---|---|---:|---|
| x264 | 8-GOP same-clip | policy - rule A (retuned) | -0.026 [-0.089, +0.036] | -0.045 [-0.136, +0.046] | 972 | 12 / 26 |
| x264 | 8-GOP same-clip | policy - rule as reported | +0.056 [-0.036, +0.123] | +0.054 [-0.058, +0.128] | 972 | 12 / 12 |
| x264 | 8-GOP mixed | policy - rule A (retuned) | +0.510 [+0.379, +0.655] * | +0.598 [+0.446, +0.778] * | 1200 | 12 / 34 |
| x264 | 8-GOP mixed | policy - rule as reported | +0.200 [+0.140, +0.271] * | +0.223 [+0.147, +0.305] * | 1200 | 12 / 14 |
| x264 | film 16-GOP | policy - rule A (retuned) | +0.028 [-0.044, +0.103] | (no per-frame luma) | 432 | 5 / 3 (YUV) |
| x264 | film 32-GOP | policy - rule A (retuned) | +0.001 [-0.104, +0.103] | (no per-frame luma) | 144 | 7 / 8 (YUV) |
| x265 | 8-GOP same-clip | policy - rule A (retuned) | +0.050 [-0.012, +0.143] | +0.073 [-0.006, +0.207] | 972 | 9 / 13 |
| x265 | 8-GOP same-clip | policy - rule as reported | +0.152 [+0.106, +0.213] * | +0.161 [+0.101, +0.212] * | 972 | 9 / 10 |
| x265 | 8-GOP mixed | policy - rule A (retuned) | +0.472 [+0.364, +0.591] * | +0.551 [+0.431, +0.683] * | 1200 | 14 / 24 |
| x265 | 8-GOP mixed | policy - rule as reported | +0.243 [+0.197, +0.295] * | +0.291 [+0.234, +0.350] * | 1200 | 14 / 14 |
| x265 | film 16-GOP | policy - rule A (retuned) | +0.097 [+0.030, +0.166] * | (no per-frame luma) | 432 | 1 / 11 (YUV) |
| x265 | film 32-GOP | policy - rule A (retuned) | +0.096 [+0.052, +0.145] * | (no per-frame luma) | 144 | 5 / 6 (YUV) |

Checks passed: summed luma-table bits equal every row's stored bits (max rel. diff < 1e-6); the YUV primary (policy - rule A, 8-GOP same-clip) reproduces report_test_cap.md (x264 -0.026, x265 +0.050).
Over-budget flags do not depend on the PSNR convention (bits only); the luma column's over rates equal YUV's.
