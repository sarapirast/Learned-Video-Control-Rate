# Stream-level rate control, dataset v1 (x265, val)

Streams of 8 IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one budget = s x sum of the GOPs' v1 budgets at level q0, q0 in (24, 30, 36, 42), s in (0.85, 1.0, 1.18). Each step picks one GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).

Margins tuned on val: split L=0: margin 0.94, QP/doubling 4.5, prior weight 1.0; rule L=0: margin 0.98, QP/doubling 4.5, prior weight 3.0; rule L=2: margin 0.98, QP/doubling 4.5, prior weight 3.0.

| method                              |   seeds |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |    s=1 | vs rule (same L)        |   share of ceiling gap |
|:------------------------------------|--------:|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|-------:|:------------------------|-----------------------:|
| equal split per GOP (tuned m)       |       1 |    1704 |       -1.228 |    -0.918 | 93.8%  | 23%        |         1.824 |      -0.862 |  -1.382 | -1.214 | -0.441 [-0.531, -0.361] |                 -0.398 |
| remaining-budget rule (tuned m) L=0 |       1 |    1704 |       -0.788 |    -0.693 | 96.3%  | 15%        |         0.559 |      -0.616 |  -0.86  | -0.783 | nan                     |                  0     |
| remaining-budget rule (tuned m) L=2 |       1 |    1704 |       -0.512 |    -0.41  | 97.1%  | 14%        |         0.602 |      -0.402 |  -0.559 | -0.513 | nan                     |                  0     |
| best constant QP (offline)          |       1 |    1704 |       -0.227 |    -0.116 | 97.0%  | 22%        |         0.651 |      -0.205 |  -0.236 | -0.229 | +0.561 [+0.431, +0.717] |                  0.506 |
| hindsight per-GOP plan (offline)    |       1 |    1704 |        0.321 |     0.345 | 100.0% | 1%         |         0.138 |       0.142 |   0.397 |  0.326 | +1.109 [+0.945, +1.288] |                  1     |
| bc L=0                              |       3 |    1704 |       -1.073 |    -0.829 | 92.2%  | 26%        |         1.434 |      -1.327 |  -0.966 | -1.039 | -0.285 [-0.478, -0.079] |                 -0.257 |
| bc L=2                              |       3 |    1704 |       -0.572 |    -0.357 | 97.4%  | 26%        |         1.265 |      -0.788 |  -0.481 | -0.552 | -0.060 [-0.212, +0.094] |                 -0.072 |
| bc_ppo L=0                          |       3 |    1704 |       -0.522 |    -0.47  | 94.1%  | 9%         |         0.304 |      -0.608 |  -0.485 | -0.511 | +0.266 [+0.114, +0.414] |                  0.24  |
| bc_ppo L=2                          |       3 |    1704 |       -0.289 |    -0.223 | 96.7%  | 11%        |         0.392 |      -0.373 |  -0.254 | -0.282 | +0.223 [+0.124, +0.326] |                  0.267 |
| bc_ppo_lag L=0                      |       3 |    1704 |       -0.571 |    -0.544 | 93.0%  | 5%         |         0.159 |      -0.624 |  -0.549 | -0.557 | +0.216 [+0.067, +0.361] |                  0.195 |
| bc_ppo_lag L=2                      |       3 |    1704 |       -0.293 |    -0.259 | 95.7%  | 6%         |         0.202 |      -0.377 |  -0.258 | -0.286 | +0.219 [+0.121, +0.322] |                  0.263 |
| ppo L=0                             |       3 |    1704 |       -0.549 |    -0.467 | 95.0%  | 12%        |         0.482 |      -0.582 |  -0.536 | -0.541 | +0.238 [+0.110, +0.369] |                  0.215 |
| ppo L=2                             |       3 |    1704 |       -0.301 |    -0.214 | 97.3%  | 14%        |         0.513 |      -0.373 |  -0.271 | -0.295 | +0.211 [+0.119, +0.306] |                  0.253 |
