# Multi-GOP rate control (x264, test)

Streams of 8 IDR GOPs (same-clip time-ordered runs, and mixed streams from different clips) under one budget = s x bits at constant QP q0, q0 in (30, 38), s in (0.85, 1.0, 1.18). Each step picks a GOP's constant QP as an offset -6..+6 on the causal model QP. Score = % saving at equal pooled (MSE) PSNR vs the stream's constant-QP curve - 2 x % over budget. 'share of hindsight gain' = (method - rule L=0) / (hindsight plan - rule L=0). Differences: 95 % bootstrap over cases (seeds averaged).

| method                     |   seeds |   cases |   score |   saving | >1% over   |   mean over % |   share of hindsight gain |   score, same-clip |   score, mixed | score vs rule L=0       | score vs bc (same L)    |
|:---------------------------|--------:|--------:|--------:|---------:|:-----------|--------------:|--------------------------:|-------------------:|---------------:|:------------------------|:------------------------|
| rule (model QP) L=0        |       1 |     912 |  -44.86 |   -37.75 | 33%        |          3.55 |                      0    |             -16.32 |         -59.7  | nan                     | nan                     |
| rule (model QP) L=2        |       1 |     912 |  -14.08 |   -11.24 | 34%        |          1.42 |                      0.54 |              -7.57 |         -17.47 | +30.78 [+19.73, +43.37] | nan                     |
| best constant QP (offline) |       1 |     912 |    0    |     0    | 0%         |          0    |                      0.78 |               0    |           0    | +44.86 [+33.71, +57.44] | nan                     |
| hindsight plan (offline)   |       1 |     912 |   12.45 |    12.46 | 0%         |          0    |                      1    |               8.67 |          14.42 | +57.31 [+46.19, +69.96] | nan                     |
| bc L=0                     |       3 |     912 |  -16.06 |   -13.9  | 9%         |          1.08 |                      0.5  |             -13.43 |         -17.43 | +28.80 [+18.07, +41.02] | nan                     |
| bc L=2                     |       3 |     912 |  -19.63 |   -18.1  | 7%         |          0.76 |                      0.44 |             -15.27 |         -21.9  | +25.23 [+14.05, +37.84] | nan                     |
| bc_ppo L=0                 |       3 |     912 |    0.11 |     0.47 | 2%         |          0.18 |                      0.78 |              -1.76 |           1.07 | +44.97 [+34.22, +57.06] | +16.17 [+14.74, +17.74] |
| bc_ppo L=2                 |       3 |     912 |    1.86 |     2.06 | 1%         |          0.1  |                      0.82 |              -0.11 |           2.89 | +46.72 [+35.71, +59.12] | +21.49 [+20.04, +23.03] |
| ppo L=0                    |       3 |     912 |   -0.77 |    -0.33 | 2%         |          0.22 |                      0.77 |              -2.04 |          -0.12 | +44.09 [+33.42, +56.11] | +15.29 [+13.91, +16.85] |
| ppo L=2                    |       3 |     912 |    1.87 |     2.05 | 1%         |          0.09 |                      0.82 |               0.12 |           2.78 | +46.73 [+35.71, +59.13] | +21.50 [+20.07, +23.07] |
