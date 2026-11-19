# Exp 4 R3: cut-GOP breakdown, val k5 (x264; exp_next/exp4/r3_cuts.py)

Descriptive, not a gate. vs final4, seeds averaged, hole excluded; dA = change in quality for the bits (A) vs final4; position = first detected cut after frame 0 (label cut/gradual).

| enc | method | GOP group | n | vs final4 | dA |
|---|---|---|---|---|---|
| x264 | R2 | early 1-9 | 4 | -0.037 [-0.037, -0.037] * | -0.039 |
| x264 | R2 | late 20-29 | 23 | -0.024 [-0.026, -0.018] * | -0.017 |
| x264 | R2 | mid 10-19 | 35 | -0.105 [-0.301, +0.295] | -0.132 |
| x264 | R2 | no detected cut | 24 | +0.127 [+0.006, +0.233] * | +0.042 |
| x264 | R2 | stable | 462 | +0.019 [-0.023, +0.061] | -0.001 |
| x264 | R3 | early 1-9 | 4 | +0.032 [+0.032, +0.032] * | +0.041 |
| x264 | R3 | late 20-29 | 23 | -0.056 [-0.078, -0.013] * | -0.034 |
| x264 | R3 | mid 10-19 | 35 | -0.031 [-0.261, +0.472] | -0.071 |
| x264 | R3 | no detected cut | 24 | +0.061 [-0.013, +0.149] | +0.001 |
| x264 | R3 | stable | 462 | +0.080 [+0.027, +0.139] * | +0.050 |

R3 mean QP offset vs final4 by frame relative to the first cut (0 = cut frame; includes mean[t]); stable GOPs' mean offset for reference:

| enc   |   -3 |   -2 |   -1 |    0 |     1 |     2 |    3 |
|:------|-----:|-----:|-----:|-----:|------:|------:|-----:|
| x264  | 0.78 | 0.33 | 1.03 | 0.31 | -0.19 | -0.23 | -0.2 |

stable GOPs, all frames: x264 -0.42

