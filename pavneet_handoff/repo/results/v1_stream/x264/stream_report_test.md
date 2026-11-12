# Stream-level rate control, dataset v1 (x264, test)

Streams of 8 IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one budget = s x sum of the GOPs' v1 budgets at level q0, q0 in (24, 30, 36, 42), s in (0.85, 1.0, 1.18). Each step picks one GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).

Margins tuned on val: split L=0: margin 0.9, QP/doubling 4.5, prior weight 0.5; rule L=0: margin 0.98, QP/doubling 4.5, prior weight 3.0; rule L=2: margin 0.98, QP/doubling 4.5, prior weight 3.0.

| method                              |   seeds |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   mean over % |   same-clip |   mixed |    s=1 | vs rule (same L)        |   share of ceiling gap |
|:------------------------------------|--------:|--------:|-------------:|----------:|:------|:-----------|--------------:|------------:|--------:|-------:|:------------------------|-----------------------:|
| equal split per GOP (tuned m)       |       1 |    2172 |       -1.195 |    -0.969 | 90.8% | 16%        |         1.334 |      -0.865 |  -1.463 | -1.189 | -0.485 [-0.608, -0.385] |                 -0.525 |
| remaining-budget rule (tuned m) L=0 |       1 |    2172 |       -0.71  |    -0.594 | 96.3% | 13%        |         0.686 |      -0.517 |  -0.867 | -0.701 | nan                     |                  0     |
| remaining-budget rule (tuned m) L=2 |       1 |    2172 |       -0.517 |    -0.404 | 97.1% | 13%        |         0.667 |      -0.428 |  -0.59  | -0.511 | nan                     |                  0     |
| best constant QP (offline)          |       1 |    2172 |       -0.213 |    -0.134 | 96.9% | 17%        |         0.46  |      -0.205 |  -0.219 | -0.21  | +0.498 [+0.406, +0.633] |                  0.538 |
| hindsight per-GOP plan (offline)    |       1 |    2172 |        0.214 |     0.22  | 99.8% | 0%         |         0.03  |       0.135 |   0.279 |  0.215 | +0.925 [+0.802, +1.093] |                  1     |
| bc L=0                              |       3 |    2172 |       -1.314 |    -0.929 | 94.5% | 33%        |         2.26  |      -1.495 |  -1.167 | -1.292 | -0.603 [-0.807, -0.349] |                 -0.652 |
| bc L=2                              |       3 |    2172 |       -0.877 |    -0.539 | 98.3% | 34%        |         1.985 |      -0.991 |  -0.784 | -0.863 | -0.359 [-0.526, -0.177] |                 -0.491 |
| bc_ppo L=0                          |       3 |    2172 |       -0.562 |    -0.47  | 95.6% | 13%        |         0.538 |      -0.565 |  -0.559 | -0.553 | +0.148 [+0.062, +0.269] |                  0.161 |
| bc_ppo L=2                          |       3 |    2172 |       -0.382 |    -0.302 | 96.8% | 12%        |         0.468 |      -0.372 |  -0.39  | -0.377 | +0.136 [+0.087, +0.201] |                  0.186 |
| bc_ppo_lag L=0                      |       3 |    2172 |       -0.588 |    -0.535 | 94.5% | 8%         |         0.31  |      -0.554 |  -0.616 | -0.579 | +0.122 [+0.050, +0.227] |                  0.132 |
| bc_ppo_lag L=2                      |       3 |    2172 |       -0.4   |    -0.351 | 96.0% | 7%         |         0.292 |      -0.373 |  -0.423 | -0.399 | +0.117 [+0.070, +0.176] |                  0.16  |
| ppo L=0                             |       3 |    2172 |       -0.561 |    -0.442 | 96.0% | 16%        |         0.704 |      -0.502 |  -0.61  | -0.55  | +0.149 [+0.087, +0.228] |                  0.161 |
| ppo L=2                             |       3 |    2172 |       -0.378 |    -0.273 | 97.4% | 15%        |         0.618 |      -0.32  |  -0.424 | -0.375 | +0.140 [+0.106, +0.177] |                  0.191 |
