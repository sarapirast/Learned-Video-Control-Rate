# test2 results (exp_next/test2/report.py)

Pre-registration exp_next/test2/PREREG.md (frozen 11-17). Frozen v1 models, evaluation only. Score dPSNR_B - 0.17 x %over, 100 dB cap; flat GOPs out; hole excluded unless stated; seeds averaged per episode; 95 % clip bootstrap, one clip per uploader ('*' = CI excludes 0). Labels after the cut review.

## x264

Scored test2 GOPs 860 (88 clips); hole episodes 570 of 17200 final4 rows; cap-affected GOPs 13 (final4 rows with capped PSNR 260).

- **PRIMARY R3 (180k, s3-5) - final4, k5: +0.044 [+0.008, +0.082] *** (n 3326, 88 clips)   [v1 test: +0.067 [+0.023, +0.107]]
- R3 - final4, k5, hole included: +0.048 [+0.010, +0.087] * (n 3440)
- per seed: s3 +0.074; s4 +0.019; s5 +0.038

Secondary 1, by class (R3 - final4, k5): cut/gradual -0.036 [-0.235, +0.101] (n 275, 36 clips); stable +0.051 [+0.014, +0.087] * (n 3051, 88 clips)
- cut/gradual minus stable: -0.087 [-0.270, +0.046]
- by level: L24 +0.099; L30 +0.015; L36 -0.024; L42 +0.088

Secondary 2, by category (R3 - final4, k5; descriptive):

| category       |   clips |   n | R3 - final4               |
|:---------------|--------:|----:|:--------------------------|
| Animation      |       8 | 272 | +0.011 [-0.068, +0.097]   |
| CoverSong      |       8 | 317 | +0.068 [-0.016, +0.164]   |
| Gaming         |       8 | 308 | +0.073 [-0.013, +0.176]   |
| HowTo          |       8 | 313 | +0.108 [-0.067, +0.253]   |
| Lecture        |       8 | 316 | +0.029 [-0.086, +0.121]   |
| LiveMusic      |       8 | 304 | +0.139 [+0.027, +0.293] * |
| LyricVideo     |       4 | 121 | -0.212 [-0.587, +0.287]   |
| MusicVideo     |       7 | 263 | -0.020 [-0.108, +0.065]   |
| NewsClip       |       8 | 310 | +0.058 [-0.013, +0.139]   |
| Sports         |       8 | 297 | +0.020 [-0.046, +0.081]   |
| TelevisionClip |       5 | 195 | +0.121 [-0.025, +0.256]   |
| Vlog           |       8 | 310 | -0.013 [-0.088, +0.076]   |

Secondary 3, k-curve (mean score, hole excluded, seeds averaged; cqp_best is hindsight, k not applicable):

| method               |       0 |       2 |       5 |      10 |      29 |
|:---------------------|--------:|--------:|--------:|--------:|--------:|
| ABR m0.90            |  -2.818 | nan     |  -2.367 | nan     | nan     |
| BC alone             |  -1.077 |  -0.573 |  -0.331 | nan     | nan     |
| CQL->PPO 540k        |  -0.732 | nan     |  -0.434 | nan     | nan     |
| R3                   | nan     |  -0.231 |  -0.129 | nan     | nan     |
| R3 (Ahhana)          |  -0.43  | nan     | nan     | nan     |  -0.118 |
| R3 own history       | nan     | nan     |  -0.136 | nan     | nan     |
| cqp_best (hindsight) | nan     | nan     | nan     | nan     |  -0.298 |
| cqp_est              |  -7.26  |  -4.021 |  -4.013 |  -3.736 |  -3.187 |
| final4               |  -0.527 |  -0.262 |  -0.172 |  -0.129 |  -0.15  |
| final4 + shift       | nan     | nan     |  -0.166 | nan     | nan     |

Secondaries 4-6 (paired, hole excluded):
- BC alone - final4, k0: -0.550 [-0.672, -0.422] * (n 3326, 88 clips)
- CQL->PPO 540k - final4, k0: -0.204 [-0.300, -0.126] * (n 3326, 88 clips)
- R3 - final4, k2: +0.031 [-0.015, +0.075] (n 3326, 88 clips)
- R3 - BC alone, k2: +0.342 [+0.273, +0.412] * (n 3326, 88 clips)
- BC alone - final4, k2: -0.311 [-0.378, -0.248] * (n 3326, 88 clips)
- R3 - cqp_est, k2: +3.790 [+3.130, +4.557] * (n 3326, 88 clips)
- R3 - BC alone, k5: +0.203 [+0.149, +0.258] * (n 3326, 88 clips)
- BC alone - final4, k5: -0.159 [-0.219, -0.106] * (n 3326, 88 clips)
- R3 - final4 + shift, k5: +0.037 [+0.016, +0.058] * (n 3326, 88 clips)
- R3 - CQL->PPO 540k, k5: +0.305 [+0.193, +0.446] * (n 3326, 88 clips)
- CQL->PPO 540k - final4, k5: -0.261 [-0.405, -0.144] * (n 3326, 88 clips)
- R3 - ABR m0.90, k5: +2.239 [+1.825, +2.755] * (n 3326, 88 clips)
- R3 - cqp_est, k5: +3.884 [+3.194, +4.646] * (n 3326, 88 clips)
- R3 - ABR m0.90, k5, cap-affected GOPs excluded (ABR rows are uncapped): +2.280 [+1.844, +2.748] * (n 3278, 88 clips)

Secondary 7, decomposition at k5 (hole excluded):

| method         |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:---------------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| ABR m0.90      | 3326 |  -2.367 | -1.547 | -0.821 |         12.186 |        25.892 |         -8.452 |   22.369 |
| BC alone       | 9978 |  -0.331 |  0.066 | -0.398 |          5.576 |        18.397 |         -3.304 |   49.87  |
| CQL->PPO 540k  | 9978 |  -0.434 | -0.016 | -0.418 |          4.543 |         9.001 |          0.631 |   27.911 |
| R3             | 9978 |  -0.129 |  0.075 | -0.204 |          2.958 |         8.976 |         -2.008 |   24.734 |
| R3 own history | 9978 |  -0.136 |  0.077 | -0.213 |          3.025 |         9.158 |         -1.924 |   25.777 |
| cqp_est        | 3326 |  -4.013 |  0     | -4.013 |         36.582 |        70.06  |         12.199 |   49.579 |
| final4         | 3326 |  -0.172 |  0.046 | -0.218 |          2.314 |         6.537 |         -0.115 |   53.367 |
| final4 + shift | 3326 |  -0.166 |  0.033 | -0.199 |          2.508 |         7.723 |         -1.12  |   55.562 |

Secondary 8, R3 with its own previous-GOP history (k5):
- R3 own history - final4: +0.036 [-0.002, +0.072] (n 3326, 88 clips)
- R3 own history - R3 (history effect): -0.008 [-0.015, -0.001] * (n 3326, 88 clips)

Secondary 10, Ahhana's R3 at k0 / k29 (s3-5, 180k; descriptive; val parity 1680/1680 per model):
- R3 (Ahhana) - final4, k0: +0.097 [+0.051, +0.149] * (n 3326, 88 clips)
- R3 (Ahhana) - BC alone, k0: +0.647 [+0.524, +0.770] * (n 3326, 88 clips)
- R3 (Ahhana) - CQL->PPO 540k, k0: +0.302 [+0.215, +0.405] * (n 3326, 88 clips)
- R3 (Ahhana) - final4, k29: +0.032 [+0.005, +0.061] * (n 3326, 88 clips)

## x265

Scored test2 GOPs 860 (88 clips); hole episodes 600 of 17200 final4 rows; cap-affected GOPs 9 (final4 rows with capped PSNR 180).

- **PRIMARY R3 (180k, s3-5) - final4, k5: +0.187 [+0.140, +0.234] *** (n 3320, 88 clips)   [v1 test: +0.163 [+0.086, +0.243]]
- R3 - final4, k5, hole included: +0.192 [+0.144, +0.241] * (n 3440)
- per seed: s3 +0.183; s4 +0.177; s5 +0.202

Secondary 1, by class (R3 - final4, k5): cut/gradual +0.133 [+0.016, +0.268] * (n 275, 36 clips); stable +0.192 [+0.143, +0.243] * (n 3045, 88 clips)
- cut/gradual minus stable: -0.059 [-0.182, +0.077]
- by level: L24 +0.105; L30 +0.090; L36 +0.120; L42 +0.421

Secondary 2, by category (R3 - final4, k5; descriptive):

| category       |   clips |   n | R3 - final4               |
|:---------------|--------:|----:|:--------------------------|
| Animation      |       8 | 273 | +0.180 [+0.058, +0.305] * |
| CoverSong      |       8 | 317 | +0.267 [+0.091, +0.480] * |
| Gaming         |       8 | 308 | +0.128 [+0.033, +0.240] * |
| HowTo          |       8 | 312 | +0.297 [+0.074, +0.524] * |
| Lecture        |       8 | 315 | +0.227 [+0.081, +0.333] * |
| LiveMusic      |       8 | 303 | +0.223 [+0.101, +0.367] * |
| LyricVideo     |       4 | 121 | +0.135 [-0.195, +0.551]   |
| MusicVideo     |       7 | 260 | +0.074 [-0.087, +0.209]   |
| NewsClip       |       8 | 309 | +0.240 [+0.112, +0.378] * |
| Sports         |       8 | 297 | +0.108 [+0.015, +0.187] * |
| TelevisionClip |       5 | 195 | +0.258 [+0.073, +0.419] * |
| Vlog           |       8 | 310 | +0.080 [+0.003, +0.166] * |

Secondary 3, k-curve (mean score, hole excluded, seeds averaged; cqp_best is hindsight, k not applicable):

| method               |       0 |       2 |       5 |      10 |      29 |
|:---------------------|--------:|--------:|--------:|--------:|--------:|
| ABR m0.93            |  -2.223 | nan     |  -1.621 | nan     | nan     |
| BC alone             |  -1.119 |  -0.582 |  -0.31  | nan     | nan     |
| CQL->PPO 540k        |  -0.621 | nan     |  -0.408 | nan     | nan     |
| R3                   | nan     |  -0.225 |  -0.103 | nan     | nan     |
| R3 own history       | nan     | nan     |  -0.106 | nan     | nan     |
| cqp_best (hindsight) | nan     | nan     | nan     | nan     |  -0.299 |
| cqp_est              |  -7.679 |  -3.778 |  -3.688 |  -3.344 |  -2.666 |
| final4               |  -0.616 |  -0.371 |  -0.29  |  -0.262 |  -0.285 |
| final4 + shift       | nan     | nan     |  -0.156 | nan     | nan     |

Secondaries 4-6 (paired, hole excluded):
- BC alone - final4, k0: -0.503 [-0.609, -0.395] * (n 3320, 88 clips)
- CQL->PPO 540k - final4, k0: -0.005 [-0.091, +0.063] (n 3320, 88 clips)
- R3 - final4, k2: +0.146 [+0.081, +0.212] * (n 3320, 88 clips)
- R3 - BC alone, k2: +0.356 [+0.293, +0.422] * (n 3320, 88 clips)
- BC alone - final4, k2: -0.210 [-0.280, -0.146] * (n 3320, 88 clips)
- R3 - cqp_est, k2: +3.553 [+3.008, +4.201] * (n 3320, 88 clips)
- R3 - BC alone, k5: +0.207 [+0.166, +0.256] * (n 3320, 88 clips)
- BC alone - final4, k5: -0.020 [-0.069, +0.024] (n 3320, 88 clips)
- R3 - final4 + shift, k5: +0.053 [+0.031, +0.075] * (n 3320, 88 clips)
- R3 - CQL->PPO 540k, k5: +0.304 [+0.212, +0.414] * (n 3320, 88 clips)
- CQL->PPO 540k - final4, k5: -0.117 [-0.243, -0.012] * (n 3320, 88 clips)
- R3 - ABR m0.93, k5: +1.518 [+1.208, +1.851] * (n 3320, 88 clips)
- R3 - cqp_est, k5: +3.585 [+3.019, +4.248] * (n 3320, 88 clips)
- R3 - ABR m0.93, k5, cap-affected GOPs excluded (ABR rows are uncapped): +1.541 [+1.230, +1.870] * (n 3288, 88 clips)

Secondary 7, decomposition at k5 (hole excluded):

| method         |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:---------------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| ABR m0.93      | 3320 |  -1.621 | -1.326 | -0.295 |          4.269 |         8.095 |         -1.515 |   30.934 |
| BC alone       | 9960 |  -0.31  |  0.013 | -0.323 |          4.499 |        14.368 |         -2.236 |   50.954 |
| CQL->PPO 540k  | 9960 |  -0.408 | -0.052 | -0.355 |          4.123 |         9.293 |          0.019 |   32.269 |
| R3             | 9960 |  -0.103 |  0.081 | -0.185 |          2.754 |         7.357 |         -1.89  |   20.281 |
| R3 own history | 9960 |  -0.106 |  0.079 | -0.185 |          2.706 |         7.129 |         -1.769 |   20.974 |
| cqp_est        | 3320 |  -3.688 |  0     | -3.688 |         33.801 |        65.223 |         10.983 |   50.512 |
| final4         | 3320 |  -0.29  | -0.075 | -0.216 |          2.261 |         5.816 |          0.1   |   54.94  |
| final4 + shift | 3320 |  -0.156 |  0.036 | -0.192 |          2.324 |         7.035 |         -0.817 |   58.042 |

Secondary 8, R3 with its own previous-GOP history (k5):
- R3 own history - final4: +0.184 [+0.135, +0.234] * (n 3320, 88 clips)
- R3 own history - R3 (history effect): -0.003 [-0.010, +0.004] (n 3320, 88 clips)

## Secondary 9, pooled v1 test + test2 (R3 - final4, k5, per encoder; descriptive)

- x264: +0.049 [+0.017, +0.079] * (n 4319: v1 test 993, test2 3326)
- x265: +0.181 [+0.142, +0.223] * (n 4314: v1 test 994, test2 3320)

## Parity gate (PREREG section 2)

- OK   decode: OK (y4m md5 identical, 3 clips)
- OK   cuts: OK (28 rows)
- OK   rd: rd_native OK (1848 rows); rd_frames OK (58800 rows)
- OK   fp: OK (3360 rows)
- OK   fpstats: OK (3360 rows)
- OK   flat: OK (28 rows)
- OK   budgets: budgets parity: 224 rows (3 clips); mismatched columns: none
- OK   prev: budgets_prev parity x264: 560 rows; mismatched columns: none | budgets_prev parity x265: 560 rows; mismatched columns: none
- OK   ctrl: final4 x264 OK (560 rows); final4 x265 OK (560 rows); final3 x264 OK (560 rows); final3 x265 OK (560 rows)
- OK   infos: x264_orig OK (28 GOPs); x264_lf OK (28 GOPs); x264_resh OK (27 GOPs); x264_lfqp OK (27 GOPs); x265_orig OK (28 GOPs); x265_lf OK (28 GOPs); x265_resh OK (27 GOPs); x265_lfqp OK (27 GOPs)
- OK   abr: x264 OK (224 rows); x265 OK (224 rows)
- OK   shift: OK (108/108 episodes equal)
- OK   r3k5 x264: rows equal to the stored v1 test rows 324/324
- OK   cqlppo x264: rows equal to the stored v1 test rows 648/648
- OK   cap_fix x264: parity GOPs 1 curves, 20 final4 rows equal to v1's
- OK   r3k5 x265: rows equal to the stored v1 test rows 324/324
- OK   cqlppo x265: rows equal to the stored v1 test rows 648/648
- OK   cap_fix x265: parity GOPs 1 curves, 20 final4 rows equal to v1's

**Gate: PASSED**

