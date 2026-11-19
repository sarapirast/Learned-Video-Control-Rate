# Final results, val (exp_next/final/report.py)

Pre-registration exp_next/final/PREREG.md (branch A). All methods rescored with one metric function on the same curves and budgets; hole excluded in the primary; 95 % clip bootstrap ('*' excludes 0). final4's and the 540k reference's test rows existed before this pass (final4 run 11-11; 540k eval default val,test).

**PSNR-cap correction (11-16):** every plane's per-frame PSNR capped at 100 dB everywhere (curves recomputed from rd_frames, final4 re-measured by re-encoding its stored QPs: bits identical; learners' rclib rows were already capped). ABR rows are not re-measured (uncapped; at most 1 GOP x 4 levels per k).

## x264

- **PRIMARY R3 (180k) - final4, k5: +0.077 [+0.020, +0.143] *** (n 548)
- R3 (180k) - ABR m0.90: +1.215 [+0.776, +1.746] * (n 548)
- R3 (180k) - CQL->PPO 540k: +0.220 [+0.091, +0.429] * (n 548)
- R3 (180k) - R3 360k: -0.014 [-0.033, +0.010] (n 548)
- per seed (R3 180k - final4): s3 +0.062; s4 +0.071; s5 +0.098
- by class (R3 180k - final4): cut/gradual +0.069 [-0.077, +0.205] (n 86); stable +0.078 [+0.020, +0.147] * (n 462)
- by level (R3 180k - final4): L24 +0.112; L30 +0.097; L36 -0.006; L42 +0.107

Decomposition at k5 (hole excluded):

| method        |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:--------------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| ABR m0.90     |  548 |  -1.253 | -0.725 | -0.528 |          7.953 |        15.413 |         -3.788 |   24.818 |
| CQL->PPO 540k | 1644 |  -0.258 |  0.077 | -0.334 |          3.788 |         8.046 |          0.188 |   23.783 |
| R3 180k       | 1644 |  -0.038 |  0.13  | -0.168 |          2.429 |         5.969 |         -1.382 |   22.871 |
| R3 360k       | 1644 |  -0.024 |  0.135 | -0.159 |          2.129 |         4.605 |         -0.95  |   20.438 |
| final4        |  548 |  -0.115 |  0.07  | -0.185 |          1.84  |         3.687 |          0.413 |   55.657 |

k-curve (existing runs; R3 was tested only at k5):

| method        |      0 |       2 |      5 |      10 |      29 |
|:--------------|-------:|--------:|-------:|--------:|--------:|
| ABR m0.90     | -1.518 | nan     | -1.253 | nan     | nan     |
| CQL->PPO 540k | -0.504 |  -0.369 | -0.258 |  -0.255 |  -0.306 |
| final4        | -0.358 |  -0.148 | -0.115 |  -0.119 |  -0.142 |

## x265

- **PRIMARY R3 (180k) - final4, k5: +0.209 [+0.092, +0.349] *** (n 550)
- R3 (180k) - ABR m0.93: +0.965 [+0.526, +1.483] * (n 550)
- R3 (180k) - CQL->PPO 540k: +0.269 [+0.155, +0.439] * (n 550)
- R3 (180k) - R3 360k: +0.006 [-0.013, +0.027] (n 550)
- R3 (180k) - final4 + shift: +0.051 [+0.009, +0.093] * (n 550)
- per seed (R3 180k - final4): s3 +0.183; s4 +0.212; s5 +0.232
- by class (R3 180k - final4): cut/gradual +0.126 [-0.079, +0.505] (n 87); stable +0.224 [+0.104, +0.357] * (n 463)
- by level (R3 180k - final4): L24 +0.067; L30 +0.067; L36 +0.170; L42 +0.521

Decomposition at k5 (hole excluded):

| method         |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:---------------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| ABR m0.93      |  550 |  -1.01  | -0.705 | -0.305 |          4.055 |         7.007 |         -0.754 |   30.727 |
| CQL->PPO 540k  | 1650 |  -0.314 | -0.006 | -0.308 |          3.993 |         9.283 |         -0.811 |   22.788 |
| R3 180k        | 1650 |  -0.045 |  0.105 | -0.151 |          2.305 |         4.701 |         -1.517 |   15.818 |
| R3 360k        | 1650 |  -0.051 |  0.076 | -0.127 |          1.784 |         3.816 |         -0.877 |   22.242 |
| final4         |  550 |  -0.254 | -0.084 | -0.17  |          1.627 |         3.448 |          0.344 |   50.364 |
| final4 + shift |  550 |  -0.096 |  0.058 | -0.154 |          1.781 |         4.646 |         -0.433 |   58.727 |

k-curve (existing runs; R3 was tested only at k5):

| method        |      0 |       2 |      5 |      10 |      29 |
|:--------------|-------:|--------:|-------:|--------:|--------:|
| ABR m0.93     | -1.395 | nan     | -1.01  | nan     | nan     |
| CQL->PPO 540k | -0.473 |  -0.361 | -0.314 |  -0.331 |  -0.314 |
| final4        | -0.47  |  -0.262 | -0.254 |  -0.243 |  -0.237 |

## Exp 7 (stream level; frozen configuration)

- x264: no val rows (exp_next/exp7/test_eval.py --split val not run)
- x265: no val rows (exp_next/exp7/test_eval.py --split val not run)

Part 2 (x264, descriptive): see results_v1/next/exp7/part2_x264.md

