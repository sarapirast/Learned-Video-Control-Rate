# Final results, val (exp_next/final/report.py)

Pre-registration exp_next/final/PREREG.md (branch A). All methods rescored with one metric function on the same curves and budgets; hole excluded in the primary; 95 % clip bootstrap ('*' excludes 0). final4's and the 540k reference's test rows existed before this pass (final4 run 11-11; 540k eval default val,test).

## x264

- **PRIMARY R3 (180k) - final4, k5: +0.068 [+0.005, +0.139] *** (n 548)
- R3 (180k) - ABR m0.90: +1.215 [+0.776, +1.746] * (n 548)
- R3 (180k) - CQL->PPO 540k: +0.220 [+0.091, +0.429] * (n 548)
- R3 (180k) - R3 360k: -0.014 [-0.033, +0.010] (n 548)
- R3 (180k) - final4: +0.068 [+0.005, +0.138] * (n 548)
- per seed (R3 180k - final4): s3 +0.054; s4 +0.063; s5 +0.089
- by class (R3 180k - final4): cut/gradual +0.016 [-0.170, +0.210] (n 86); stable +0.078 [+0.021, +0.150] * (n 462)
- by level (R3 180k - final4): L24 +0.083; L30 +0.096; L36 -0.009; L42 +0.105

Decomposition at k5 (hole excluded):

| method        |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:--------------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| ABR m0.90     |  548 |  -1.26  | -0.731 | -0.529 |          7.953 |        15.413 |         -3.788 |   24.818 |
| CQL->PPO 540k | 1644 |  -0.264 |  0.07  | -0.334 |          3.788 |         8.046 |          0.188 |   23.783 |
| R3 180k       | 1644 |  -0.045 |  0.123 | -0.168 |          2.429 |         5.969 |         -1.382 |   22.871 |
| R3 360k       | 1644 |  -0.031 |  0.128 | -0.159 |          2.129 |         4.605 |         -0.95  |   20.438 |
| final4        |  548 |  -0.113 |  0.072 | -0.185 |          1.84  |         3.687 |          0.413 |   55.657 |

k-curve (existing runs; R3 was tested only at k5):

| method        |      0 |       2 |      5 |      10 |      29 |
|:--------------|-------:|--------:|-------:|--------:|--------:|
| ABR m0.90     | -1.525 | nan     | -1.26  | nan     | nan     |
| CQL->PPO 540k | -0.51  |  -0.376 | -0.264 |  -0.262 |  -0.313 |
| final4        | -0.357 |  -0.148 | -0.113 |  -0.121 |  -0.14  |

## x265

- **PRIMARY R3 (180k) - final4, k5: +0.204 [+0.081, +0.346] *** (n 550)
- R3 (180k) - ABR m0.93: +0.965 [+0.511, +1.445] * (n 550)
- R3 (180k) - CQL->PPO 540k: +0.269 [+0.150, +0.432] * (n 550)
- R3 (180k) - R3 360k: +0.006 [-0.013, +0.027] (n 550)
- R3 (180k) - final4: +0.204 [+0.079, +0.349] * (n 550)
- R3 (180k) - final4 + shift: +0.051 [+0.009, +0.091] * (n 550)
- per seed (R3 180k - final4): s3 +0.178; s4 +0.207; s5 +0.227
- by class (R3 180k - final4): cut/gradual +0.094 [-0.144, +0.488] (n 87); stable +0.224 [+0.107, +0.356] * (n 463)
- by level (R3 180k - final4): L24 +0.047; L30 +0.065; L36 +0.170; L42 +0.521

Decomposition at k5 (hole excluded):

| method         |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:---------------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| ABR m0.93      |  550 |  -1.017 | -0.708 | -0.309 |          4.055 |         7.007 |         -0.754 |   30.727 |
| CQL->PPO 540k  | 1650 |  -0.32  | -0.012 | -0.308 |          3.993 |         9.283 |         -0.811 |   22.788 |
| R3 180k        | 1650 |  -0.052 |  0.099 | -0.151 |          2.305 |         4.701 |         -1.517 |   15.818 |
| R3 360k        | 1650 |  -0.058 |  0.07  | -0.128 |          1.784 |         3.816 |         -0.877 |   22.242 |
| final4         |  550 |  -0.256 | -0.085 | -0.171 |          1.627 |         3.448 |          0.344 |   50.364 |
| final4 + shift |  550 |  -0.103 |  0.051 | -0.154 |          1.781 |         4.646 |         -0.433 |   58.727 |

k-curve (existing runs; R3 was tested only at k5):

| method        |      0 |       2 |      5 |      10 |      29 |
|:--------------|-------:|--------:|-------:|--------:|--------:|
| ABR m0.93     | -1.401 | nan     | -1.017 | nan     | nan     |
| CQL->PPO 540k | -0.48  |  -0.367 | -0.32  |  -0.338 |  -0.32  |
| final4        | -0.472 |  -0.265 | -0.256 |  -0.248 |  -0.237 |

## Exp 7 (stream level; frozen configuration)

- x264: no val rows (exp_next/exp7/test_eval.py --split val not run)
- x265: no val rows (exp_next/exp7/test_eval.py --split val not run)

Part 2 (x264, descriptive): see results_v1/next/exp7/part2_x264.md

