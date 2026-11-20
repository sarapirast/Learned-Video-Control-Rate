# Table I with the 100 dB PSNR cap (exp_next/final/table1_cap.py)

Per-GOP v1 test score (dB) by lookahead k, the rows of results_v1/w5/w5_numbers.md and abr_dpsnr.md (11-11, uncapped) rescored with the 100 dB per-plane PSNR cap. Same rows, same convention as the 11-11 table (hole episodes included, flat GOPs excluded, learners 3 seeds averaged). R3 added 11-20 (k5 only). No encodes. ABR+VBV: curve corrected, episode PSNR not re-measured (as report_test_cap.md).

## x264

Capped, hole included (Table I convention):

| method | k0 | k2 | k5 | k10 | k29 |
|---|---:|---:|---:|---:|---:|
| Search (ceiling) | +0.298 | +0.298 | +0.298 | +0.298 | +0.298 |
| Controller (final4) | -0.349 | -0.164 | -0.129 | -0.119 | -0.126 |
| BC (causal base) | -1.492 | -0.853 | -0.561 | -0.412 | -0.204 |
| CQL->PPO | -1.272 | -0.762 | -0.582 | -0.423 | -0.374 |
| ABR+VBV | -1.632 | -1.644 | -1.547 | -1.516 | -1.576 |
| R3 (180k, seeds 3-5) | - | - | -0.055 | - | - |

Change vs the 11-11 (uncapped) numbers, capped - uncapped (mean; max |row change|):

| method | k0 | k2 | k5 | k10 | k29 |
|---|---:|---:|---:|---:|---:|
| Search (ceiling) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) |
| Controller (final4) | -0.0000 (0.00) | -0.0000 (0.00) | -0.0000 (0.00) | -0.0000 (0.00) | -0.0000 (0.00) |
| BC (causal base) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) |
| CQL->PPO | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) |
| ABR+VBV | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) |
| R3 (180k, seeds 3-5) | - | - | +0.0016 (0.40) | - | - |

Capped, hole excluded (the convention of report_test_cap.md and the R3 tables; for reference):

| method | k0 | k2 | k5 | k10 | k29 |
|---|---:|---:|---:|---:|---:|
| Search (ceiling) | +0.296 | +0.296 | +0.296 | +0.296 | +0.296 |
| Controller (final4) | -0.310 | -0.143 | -0.107 | -0.097 | -0.108 |
| BC (causal base) | -1.457 | -0.839 | -0.551 | -0.397 | -0.197 |
| CQL->PPO | -1.235 | -0.747 | -0.561 | -0.411 | -0.367 |
| ABR+VBV | -1.626 | -1.640 | -1.548 | -1.518 | -1.571 |
| R3 (180k, seeds 3-5) | - | - | -0.040 | - | - |

Share of the search's gain over ABR+VBV, (S - S_ABR) / (S_search - S_ABR), capped, hole included, S_ABR = middle of its capped range (-1.644 to -1.516 -> -1.580); %:

| method | k0 | k2 | k5 | k10 | k29 |
|---|---:|---:|---:|---:|---:|
| Controller (final4) | 66 | 75 | 77 | 78 | 77 |
| BC (causal base) | 5 | 39 | 54 | 62 | 73 |
| CQL->PPO | 16 | 44 | 53 | 62 | 64 |
| R3 (180k, seeds 3-5) | - | - | 81 | - | - |

R3 at k5 (180k, seeds 3-5 averaged, final test pass rows): capped, hole included -0.055 dB -> share 81.2 % (S_search +0.298, S_ABR -1.580); capped, hole excluded -0.040. R3 was run on v1 test at k5 only.

Rows per cell: 1008 (GOP x level, hole included), 993 hole excluded; GOPs with a changed curve in these rows: 1.

## x265

Capped, hole included (Table I convention):

| method | k0 | k2 | k5 | k10 | k29 |
|---|---:|---:|---:|---:|---:|
| Search (ceiling) | +0.282 | +0.282 | +0.282 | +0.282 | +0.282 |
| Controller (final4) | -0.434 | -0.279 | -0.205 | -0.193 | -0.241 |
| BC (causal base) | -1.366 | -0.880 | -0.603 | -0.396 | -0.212 |
| CQL->PPO | -1.115 | -0.784 | -0.533 | -0.427 | -0.407 |
| ABR+VBV | -1.252 | -1.162 | -1.191 | -1.179 | -1.225 |
| R3 (180k, seeds 3-5) | - | - | -0.036 | - | - |

Change vs the 11-11 (uncapped) numbers, capped - uncapped (mean; max |row change|):

| method | k0 | k2 | k5 | k10 | k29 |
|---|---:|---:|---:|---:|---:|
| Search (ceiling) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) |
| Controller (final4) | +0.0000 (0.00) | +0.0000 (0.00) | +0.0000 (0.00) | +0.0000 (0.00) | +0.0000 (0.00) |
| BC (causal base) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) |
| CQL->PPO | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) |
| ABR+VBV | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) | +0.0016 (0.40) |
| R3 (180k, seeds 3-5) | - | - | +0.0016 (0.40) | - | - |

Capped, hole excluded (the convention of report_test_cap.md and the R3 tables; for reference):

| method | k0 | k2 | k5 | k10 | k29 |
|---|---:|---:|---:|---:|---:|
| Search (ceiling) | +0.285 | +0.285 | +0.285 | +0.285 | +0.285 |
| Controller (final4) | -0.397 | -0.260 | -0.185 | -0.174 | -0.227 |
| BC (causal base) | -1.325 | -0.872 | -0.585 | -0.381 | -0.201 |
| CQL->PPO | -1.073 | -0.767 | -0.509 | -0.410 | -0.390 |
| ABR+VBV | -1.235 | -1.150 | -1.183 | -1.169 | -1.215 |
| R3 (180k, seeds 3-5) | - | - | -0.022 | - | - |

Share of the search's gain over ABR+VBV, (S - S_ABR) / (S_search - S_ABR), capped, hole included, S_ABR = middle of its capped range (-1.252 to -1.162 -> -1.207); %:

| method | k0 | k2 | k5 | k10 | k29 |
|---|---:|---:|---:|---:|---:|
| Controller (final4) | 52 | 62 | 67 | 68 | 65 |
| BC (causal base) | -11 | 22 | 41 | 54 | 67 |
| CQL->PPO | 6 | 28 | 45 | 52 | 54 |
| R3 (180k, seeds 3-5) | - | - | 79 | - | - |

R3 at k5 (180k, seeds 3-5 averaged, final test pass rows): capped, hole included -0.036 dB -> share 78.6 % (S_search +0.282, S_ABR -1.207); capped, hole excluded -0.022. R3 was run on v1 test at k5 only.

Rows per cell: 1008 (GOP x level, hole included), 994 hole excluded; GOPs with a changed curve in these rows: 1.

Checks passed: uncapped + hole included reproduces w5_numbers.md (search, BC, CQL->PPO; final4 x264) to 3 decimals; capped + hole excluded reproduces final4's k-row of report_test_cap.md (both encoders) and the primary R3 - final4 at k5 (x264 +0.067, x265 +0.163). R3 rows: results_v1/final/r3_test_<enc>.pkl, scored by exp_next/final/report.py's Scorer (added 11-20).
