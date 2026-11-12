# Stream-level rate control, dataset v1 (x265, val)

Streams of 8 IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one budget = s x sum of the GOPs' v1 budgets at level q0, q0 in (24, 30, 36, 42), s in (0.85, 1.0, 1.18). Each step picks one GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).

Margins tuned on val: split L=0: m=0.94; rule L=0: m=0.98; rule L=2: m=0.98.

| method                              |   seeds |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |    s=1 | vs rule (same L)        |   share of ceiling gap |
|:------------------------------------|--------:|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|-------:|:------------------------|-----------------------:|
| equal split per GOP (tuned m)       |       1 |    1704 |       -1.541 |    -1.283 | 93.4%  | 20%        |         1.518 |      -0.878 |  -1.819 | -1.541 | -0.511 [-0.632, -0.407] |                 -0.378 |
| remaining-budget rule (tuned m) L=0 |       1 |    1704 |       -1.03  |    -0.834 | 97.4%  | 20%        |         1.148 |      -0.596 |  -1.212 | -1.029 | nan                     |                  0     |
| remaining-budget rule (tuned m) L=2 |       1 |    1704 |       -0.657 |    -0.531 | 97.5%  | 15%        |         0.746 |      -0.357 |  -0.783 | -0.674 | nan                     |                  0     |
| best constant QP (offline)          |       1 |    1704 |       -0.227 |    -0.116 | 97.0%  | 22%        |         0.651 |      -0.205 |  -0.236 | -0.229 | +0.803 [+0.630, +1.009] |                  0.594 |
| hindsight per-GOP plan (offline)    |       1 |    1704 |        0.321 |     0.345 | 100.0% | 1%         |         0.138 |       0.142 |   0.397 |  0.326 | +1.351 [+1.137, +1.588] |                  1     |
| bc L=2                              |       1 |    1704 |       -0.544 |    -0.237 | 100.2% | 34%        |         1.807 |      -0.517 |  -0.556 | -0.533 | +0.113 [+0.015, +0.222] |                  0.115 |
| bc_ppo L=2                          |       1 |    1704 |       -0.471 |    -0.323 | 97.9%  | 21%        |         0.871 |      -0.397 |  -0.502 | -0.463 | +0.186 [+0.106, +0.277] |                  0.19  |
| bc_ppo_lag L=2                      |       1 |    1704 |       -0.47  |    -0.366 | 96.6%  | 15%        |         0.612 |      -0.439 |  -0.483 | -0.467 | +0.187 [+0.087, +0.299] |                  0.191 |
| ppo L=2                             |       1 |    1704 |       -0.633 |    -0.476 | 97.4%  | 22%        |         0.927 |      -0.373 |  -0.743 | -0.632 | +0.024 [-0.017, +0.073] |                  0.024 |
