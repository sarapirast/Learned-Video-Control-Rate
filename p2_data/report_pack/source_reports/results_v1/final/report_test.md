# Final results, test (exp_next/final/report.py)

Pre-registration exp_next/final/PREREG.md (branch A). All methods rescored with one metric function on the same curves and budgets; hole excluded in the primary; 95 % clip bootstrap ('*' excludes 0). final4's and the 540k reference's test rows existed before this pass (final4 run 11-11; 540k eval default val,test).

## x264

- **PRIMARY R3 (180k) - final4, k5: +0.066 [+0.022, +0.106] *** (n 993)
- R3 (180k) - ABR m0.90: +1.047 [+0.795, +1.334] * (n 993)
- R3 (180k) - CQL->PPO 540k: +0.129 [+0.039, +0.239] * (n 993)
- R3 (180k) - R3 360k: -0.028 [-0.066, +0.001] (n 993)
- per seed (R3 180k - final4): s3 +0.064; s4 +0.028; s5 +0.107
- by class (R3 180k - final4): cut/gradual +0.056 [-0.049, +0.159] (n 208); stable +0.069 [+0.026, +0.106] * (n 785)
- by level (R3 180k - final4): L24 +0.083; L30 +0.095; L36 +0.035; L42 +0.053

Decomposition at k5 (hole excluded):

| method        |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:--------------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| ABR m0.90     |  993 |  -1.088 | -0.539 | -0.549 |          8.697 |        17.221 |         -5.056 |   26.989 |
| CQL->PPO 540k | 2979 |  -0.17  |  0.088 | -0.259 |          3.366 |         5.952 |         -0.834 |   20.04  |
| R3 180k       | 2979 |  -0.041 |  0.13  | -0.171 |          2.531 |         5.485 |         -1.452 |   24.102 |
| R3 360k       | 2979 |  -0.013 |  0.14  | -0.153 |          2.165 |         3.835 |         -1.103 |   23.028 |
| final4        |  993 |  -0.107 |  0.067 | -0.174 |          1.925 |         4.335 |         -0.17  |   54.683 |

k-curve (existing runs; R3 was tested only at k5):

| method        |      0 |       2 |      5 |      10 |      29 |
|:--------------|-------:|--------:|-------:|--------:|--------:|
| ABR m0.90     | -1.43  | nan     | -1.088 | nan     | nan     |
| CQL->PPO 540k | -0.404 |  -0.291 | -0.17  |  -0.175 |  -0.137 |
| final4        | -0.31  |  -0.143 | -0.107 |  -0.097 |  -0.108 |

## x265

- **PRIMARY R3 (180k) - final4, k5: +0.162 [+0.085, +0.243] *** (n 994)
- R3 (180k) - ABR m0.93: +0.711 [+0.535, +0.900] * (n 994)
- R3 (180k) - CQL->PPO 540k: +0.199 [+0.083, +0.340] * (n 994)
- R3 (180k) - R3 360k: +0.022 [-0.000, +0.048] (n 994)
- R3 (180k) - final4 + shift: +0.074 [+0.041, +0.105] * (n 994)
- per seed (R3 180k - final4): s3 +0.156; s4 +0.160; s5 +0.170
- by class (R3 180k - final4): cut/gradual +0.098 [-0.017, +0.201] (n 208); stable +0.179 [+0.101, +0.270] * (n 786)
- by level (R3 180k - final4): L24 +0.063; L30 +0.062; L36 +0.122; L42 +0.395

Decomposition at k5 (hole excluded):

| method         |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:---------------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| ABR m0.93      |  994 |  -0.733 | -0.477 | -0.257 |          3.995 |         7.313 |         -1.937 |   26.861 |
| CQL->PPO 540k  | 2982 |  -0.221 |  0.05  | -0.271 |          3.402 |         6.429 |         -0.839 |   24.111 |
| R3 180k        | 2982 |  -0.023 |  0.12  | -0.143 |          2.193 |         3.905 |         -1.548 |   21.261 |
| R3 360k        | 2982 |  -0.045 |  0.092 | -0.137 |          1.99  |         3.843 |         -1.134 |   23.81  |
| final4         |  994 |  -0.185 | -0.03  | -0.155 |          1.634 |         3.755 |         -0.106 |   55.231 |
| final4 + shift |  994 |  -0.097 |  0.05  | -0.147 |          1.535 |         3.335 |          0.057 |   65.191 |

k-curve (existing runs; R3 was tested only at k5):

| method        |      0 |       2 |      5 |      10 |      29 |
|:--------------|-------:|--------:|-------:|--------:|--------:|
| ABR m0.93     | -1.147 | nan     | -0.733 | nan     | nan     |
| CQL->PPO 540k | -0.38  |  -0.294 | -0.221 |  -0.217 |  -0.148 |
| final4        | -0.397 |  -0.26  | -0.185 |  -0.174 |  -0.227 |

## Exp 7 (stream level; frozen configuration)

- x264 N=8 clip: policy - retuned rule -0.026 [-0.091, +0.040] (n 972)  <- PRIMARY
- x264 N=8 clip: policy - rule as reported +0.056 [-0.044, +0.126] (n 972)
- x264 N=8 mixed: policy - retuned rule +0.510 [+0.379, +0.649] * (n 1200)
- x264 N=8 mixed: policy - rule as reported +0.200 [+0.138, +0.266] * (n 1200)
- x264 N=16 clip: policy - retuned rule +0.028 [-0.046, +0.105] (n 432)
- x264 N=16 clip: policy - rule as reported +0.058 [-0.003, +0.121] (n 432)
- x264 N=32 clip: policy - retuned rule +0.001 [-0.111, +0.102] (n 144)
- x264 N=32 clip: policy - rule as reported +0.037 [-0.061, +0.144] (n 144)
- x265 N=8 clip: policy - retuned rule +0.050 [-0.009, +0.148] (n 972)  <- PRIMARY
- x265 N=8 clip: policy - rule as reported +0.152 [+0.109, +0.213] * (n 972)
- x265 N=8 mixed: policy - retuned rule +0.472 [+0.363, +0.588] * (n 1200)
- x265 N=8 mixed: policy - rule as reported +0.243 [+0.197, +0.294] * (n 1200)
- x265 N=16 clip: policy - retuned rule +0.097 [+0.035, +0.162] * (n 432)
- x265 N=16 clip: policy - rule as reported +0.123 [+0.066, +0.185] * (n 432)
- x265 N=32 clip: policy - retuned rule +0.096 [+0.052, +0.147] * (n 144)
- x265 N=32 clip: policy - rule as reported +0.157 [+0.090, +0.234] * (n 144)

Part 2 (x264, descriptive): see results_v1/next/exp7/part2_x264_test.md

