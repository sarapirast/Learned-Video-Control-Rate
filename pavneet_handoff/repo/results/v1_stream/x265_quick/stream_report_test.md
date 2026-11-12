# Stream-level rate control, dataset v1 (x265, test)

Streams of 8 IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one budget = s x sum of the GOPs' v1 budgets at level q0, q0 in (24, 30, 36, 42), s in (0.85, 1.0, 1.18). Each step picks one GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).

Margins tuned on val: split L=0: m=0.94; rule L=0: m=0.98; rule L=2: m=0.98.

| method                              |   seeds |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |    s=1 | vs rule (same L)        |   share of ceiling gap |
|:------------------------------------|--------:|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|-------:|:------------------------|-----------------------:|
| equal split per GOP (tuned m)       |       1 |    2172 |       -1.338 |    -1.057 | 93.6%  | 19%        |         1.651 |      -0.78  |  -1.79  | -1.336 | -0.525 [-0.679, -0.418] |                 -0.509 |
| remaining-budget rule (tuned m) L=0 |       1 |    2172 |       -0.813 |    -0.641 | 97.9%  | 17%        |         1.012 |      -0.488 |  -1.076 | -0.821 | nan                     |                  0     |
| remaining-budget rule (tuned m) L=2 |       1 |    2172 |       -0.529 |    -0.416 | 98.0%  | 12%        |         0.665 |      -0.298 |  -0.717 | -0.529 | nan                     |                  0     |
| best constant QP (offline)          |       1 |    2172 |       -0.214 |    -0.137 | 96.7%  | 17%        |         0.453 |      -0.211 |  -0.217 | -0.212 | +0.599 [+0.450, +0.814] |                  0.581 |
| hindsight per-GOP plan (offline)    |       1 |    2172 |        0.218 |     0.223 | 99.8%  | 0%         |         0.028 |       0.13  |   0.29  |  0.22  | +1.031 [+0.866, +1.278] |                  1     |
| bc L=2                              |       1 |    2172 |       -0.471 |    -0.217 | 100.1% | 28%        |         1.493 |      -0.351 |  -0.567 | -0.452 | +0.059 [-0.033, +0.167] |                  0.079 |
| bc_ppo L=2                          |       1 |    2172 |       -0.336 |    -0.236 | 98.1%  | 14%        |         0.593 |      -0.253 |  -0.404 | -0.326 | +0.193 [+0.122, +0.299] |                  0.258 |
| bc_ppo_lag L=2                      |       1 |    2172 |       -0.345 |    -0.282 | 96.9%  | 9%         |         0.372 |      -0.282 |  -0.396 | -0.34  | +0.185 [+0.106, +0.302] |                  0.247 |
| ppo L=2                             |       1 |    2172 |       -0.463 |    -0.325 | 98.2%  | 16%        |         0.809 |      -0.306 |  -0.589 | -0.467 | +0.067 [+0.027, +0.126] |                  0.089 |
