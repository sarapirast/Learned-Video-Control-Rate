# Multi-GOP rate control (x265, test)

Streams of 8 IDR GOPs (same-clip time-ordered runs, and mixed streams from different clips) under one budget = s x bits at constant QP q0, q0 in (30, 38), s in (0.85, 1.0, 1.18). Each step picks a GOP's constant QP as an offset -6..+6 on the causal model QP. Score = % saving at equal pooled (MSE) PSNR vs the stream's constant-QP curve - 2 x % over budget. 'share of hindsight gain' = (method - rule L=0) / (hindsight plan - rule L=0). Differences: 95 % bootstrap over cases (seeds averaged).

| method                     |   seeds |   cases |   score |   saving | >1% over   |   mean over % |   share of hindsight gain |   score, same-clip |   score, mixed | score vs rule L=0       | score vs bc (same L)    |
|:---------------------------|--------:|--------:|--------:|---------:|:-----------|--------------:|--------------------------:|-------------------:|---------------:|:------------------------|:------------------------|
| rule (model QP) L=0        |       1 |     912 |  -20.68 |   -17.66 | 27%        |          1.51 |                      0    |             -15.68 |         -23.28 | nan                     | nan                     |
| rule (model QP) L=2        |       1 |     912 |  -10.37 |    -8.6  | 27%        |          0.88 |                      0.31 |              -5.14 |         -13.09 | +10.31 [+6.91, +14.44]  | nan                     |
| best constant QP (offline) |       1 |     912 |    0    |     0    | 0%         |          0    |                      0.62 |               0    |           0    | +20.68 [+17.68, +24.69] | nan                     |
| hindsight plan (offline)   |       1 |     912 |   12.54 |    12.54 | 0%         |          0    |                      1    |               8.36 |          14.71 | +33.22 [+30.21, +37.15] | nan                     |
| bc L=0                     |       3 |     912 |  -16.99 |   -14.74 | 10%        |          1.12 |                      0.11 |             -15.6  |         -17.71 | +3.70 [+0.85, +7.49]    | nan                     |
| bc L=2                     |       3 |     912 |  -19.56 |   -18.09 | 7%         |          0.74 |                      0.03 |             -14.99 |         -21.94 | +1.12 [-2.12, +5.09]    | nan                     |
| bc_ppo L=0                 |       3 |     912 |    1.65 |     1.7  | 1%         |          0.03 |                      0.67 |              -1.32 |           3.19 | +22.33 [+19.45, +26.11] | +18.63 [+17.19, +20.09] |
| bc_ppo L=2                 |       3 |     912 |    3.23 |     3.28 | 1%         |          0.03 |                      0.72 |               0.52 |           4.64 | +23.91 [+20.94, +27.85] | +22.79 [+21.42, +24.21] |
| ppo L=0                    |       3 |     912 |    0.96 |     1.05 | 2%         |          0.04 |                      0.65 |              -1.55 |           2.26 | +21.64 [+18.82, +25.38] | +17.94 [+16.51, +19.42] |
| ppo L=2                    |       3 |     912 |    3.04 |     3.13 | 1%         |          0.04 |                      0.71 |               0.23 |           4.51 | +23.73 [+20.75, +27.66] | +22.61 [+21.22, +24.03] |
