# Stream-level rate control, dataset v1 (x265, test)

Streams of 8 IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one budget = s x sum of the GOPs' v1 budgets at level q0, q0 in (24, 30, 36, 42), s in (0.85, 1.0, 1.18). Each step picks one GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).

Margins tuned on val: split L=0: margin 0.94, QP/doubling 4.5, prior weight 1.0; rule L=0: margin 0.98, QP/doubling 4.5, prior weight 3.0; rule L=2: margin 0.98, QP/doubling 4.5, prior weight 3.0.

| method                              |   seeds |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   mean over % |   same-clip |   mixed |    s=1 | vs rule (same L)        |   share of ceiling gap |
|:------------------------------------|--------:|--------:|-------------:|----------:|:------|:-----------|--------------:|------------:|--------:|-------:|:------------------------|-----------------------:|
| equal split per GOP (tuned m)       |       1 |    2172 |       -1.059 |    -0.742 | 94.3% | 20%        |         1.869 |      -0.729 |  -1.327 | -1.053 | -0.433 [-0.535, -0.361] |                 -0.512 |
| remaining-budget rule (tuned m) L=0 |       1 |    2172 |       -0.627 |    -0.529 | 96.9% | 12%        |         0.572 |      -0.438 |  -0.779 | -0.624 | nan                     |                  0     |
| remaining-budget rule (tuned m) L=2 |       1 |    2172 |       -0.423 |    -0.328 | 97.8% | 12%        |         0.557 |      -0.33  |  -0.498 | -0.419 | nan                     |                  0     |
| best constant QP (offline)          |       1 |    2172 |       -0.214 |    -0.137 | 96.7% | 17%        |         0.453 |      -0.211 |  -0.217 | -0.212 | +0.413 [+0.318, +0.555] |                  0.488 |
| hindsight per-GOP plan (offline)    |       1 |    2172 |        0.218 |     0.223 | 99.8% | 0%         |         0.028 |       0.13  |   0.29  |  0.22  | +0.845 [+0.723, +1.023] |                  1     |
| bc L=0                              |       3 |    2172 |       -1.136 |    -0.779 | 94.1% | 34%        |         2.097 |      -1.367 |  -0.949 | -1.094 | -0.509 [-0.676, -0.260] |                 -0.603 |
| bc L=2                              |       3 |    2172 |       -0.632 |    -0.349 | 98.9% | 36%        |         1.661 |      -0.751 |  -0.535 | -0.609 | -0.209 [-0.315, -0.065] |                 -0.326 |
| bc_ppo L=0                          |       3 |    2172 |       -0.44  |    -0.376 | 95.8% | 11%        |         0.378 |      -0.484 |  -0.405 | -0.428 | +0.186 [+0.079, +0.334] |                  0.22  |
| bc_ppo L=2                          |       3 |    2172 |       -0.21  |    -0.149 | 97.8% | 10%        |         0.361 |      -0.247 |  -0.181 | -0.205 | +0.213 [+0.152, +0.301] |                  0.332 |
| bc_ppo_lag L=0                      |       3 |    2172 |       -0.486 |    -0.455 | 94.5% | 5%         |         0.182 |      -0.529 |  -0.45  | -0.473 | +0.141 [+0.030, +0.291] |                  0.167 |
| bc_ppo_lag L=2                      |       3 |    2172 |       -0.217 |    -0.183 | 97.0% | 5%         |         0.195 |      -0.254 |  -0.186 | -0.209 | +0.206 [+0.142, +0.300] |                  0.322 |
| ppo L=0                             |       3 |    2172 |       -0.454 |    -0.372 | 96.2% | 14%        |         0.487 |      -0.434 |  -0.471 | -0.447 | +0.172 [+0.094, +0.283] |                  0.204 |
| ppo L=2                             |       3 |    2172 |       -0.222 |    -0.143 | 98.1% | 12%        |         0.46  |      -0.217 |  -0.225 | -0.216 | +0.201 [+0.159, +0.265] |                  0.314 |
| ppo_pid L=0                         |       3 |    2172 |       -0.494 |    -0.461 | 94.0% | 5%         |         0.194 |      -0.484 |  -0.501 | -0.483 | +0.133 [+0.046, +0.257] |                  0.158 |
| ppo_pid L=2                         |       3 |    2172 |       -0.263 |    -0.226 | 96.6% | 5%         |         0.217 |      -0.26  |  -0.265 | -0.255 | +0.160 [+0.113, +0.230] |                  0.25  |
