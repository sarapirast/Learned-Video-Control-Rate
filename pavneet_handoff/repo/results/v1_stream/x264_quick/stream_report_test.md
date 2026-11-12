# Stream-level rate control, dataset v1 (x264, test)

Streams of 8 IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one budget = s x sum of the GOPs' v1 budgets at level q0, q0 in (24, 30, 36, 42), s in (0.85, 1.0, 1.18). Each step picks one GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).

Margins tuned on val: split L=0: m=0.96; rule L=0: m=0.98; rule L=2: m=0.98.

| method                              |   seeds |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |    s=1 | vs rule (same L)        |   share of ceiling gap |
|:------------------------------------|--------:|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|-------:|:------------------------|-----------------------:|
| equal split per GOP (tuned m)       |       1 |    2172 |       -1.358 |    -1.021 | 94.5%  | 25%        |         1.979 |      -0.895 |  -1.732 | -1.351 | -0.515 [-0.652, -0.414] |                 -0.487 |
| remaining-budget rule (tuned m) L=0 |       1 |    2172 |       -0.843 |    -0.692 | 97.2%  | 17%        |         0.888 |      -0.525 |  -1.1   | -0.837 | nan                     |                  0     |
| remaining-budget rule (tuned m) L=2 |       1 |    2172 |       -0.627 |    -0.487 | 97.6%  | 14%        |         0.824 |      -0.363 |  -0.841 | -0.631 | nan                     |                  0     |
| best constant QP (offline)          |       1 |    2172 |       -0.213 |    -0.134 | 96.9%  | 17%        |         0.46  |      -0.205 |  -0.219 | -0.21  | +0.630 [+0.495, +0.835] |                  0.596 |
| hindsight per-GOP plan (offline)    |       1 |    2172 |        0.214 |     0.22  | 99.8%  | 0%         |         0.03  |       0.135 |   0.279 |  0.215 | +1.057 [+0.897, +1.294] |                  1     |
| bc L=2                              |       1 |    2172 |       -0.586 |    -0.284 | 100.0% | 32%        |         1.777 |      -0.43  |  -0.713 | -0.585 | +0.041 [-0.042, +0.145] |                  0.049 |
| bc_ppo L=2                          |       1 |    2172 |       -0.473 |    -0.325 | 97.8%  | 18%        |         0.871 |      -0.334 |  -0.586 | -0.472 | +0.154 [+0.095, +0.244] |                  0.183 |
| bc_ppo_lag L=2                      |       1 |    2172 |       -0.494 |    -0.409 | 95.6%  | 11%        |         0.5   |      -0.403 |  -0.567 | -0.494 | +0.134 [+0.054, +0.255] |                  0.159 |
| ppo L=2                             |       1 |    2172 |       -0.654 |    -0.57  | 94.7%  | 9%         |         0.495 |      -0.512 |  -0.77  | -0.651 | -0.027 [-0.089, +0.065] |                 -0.032 |
