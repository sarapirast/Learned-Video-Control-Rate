# Stream-level rate control, dataset v1 (x264, val)

Streams of 8 IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one budget = s x sum of the GOPs' v1 budgets at level q0, q0 in (24, 30, 36, 42), s in (0.85, 1.0, 1.18). Each step picks one GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).

Margins tuned on val: split L=0: margin 0.9, QP/doubling 4.5, prior weight 0.5; rule L=0: margin 0.98, QP/doubling 4.5, prior weight 3.0; rule L=2: margin 0.98, QP/doubling 4.5, prior weight 3.0.

| method                              |   seeds |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |    s=1 | vs rule (same L)        |   share of ceiling gap |
|:------------------------------------|--------:|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|-------:|:------------------------|-----------------------:|
| equal split per GOP (tuned m)       |       1 |    1704 |       -1.338 |    -1.052 | 91.8%  | 20%        |         1.678 |      -1.009 |  -1.476 | -1.325 | -0.472 [-0.580, -0.367] |                 -0.395 |
| remaining-budget rule (tuned m) L=0 |       1 |    1704 |       -0.865 |    -0.742 | 95.9%  | 16%        |         0.724 |      -0.769 |  -0.906 | -0.859 | nan                     |                  0     |
| remaining-budget rule (tuned m) L=2 |       1 |    1704 |       -0.655 |    -0.523 | 96.5%  | 15%        |         0.776 |      -0.623 |  -0.669 | -0.652 | nan                     |                  0     |
| best constant QP (offline)          |       1 |    1704 |       -0.218 |    -0.107 | 97.4%  | 23%        |         0.653 |      -0.195 |  -0.227 | -0.204 | +0.648 [+0.510, +0.812] |                  0.542 |
| hindsight per-GOP plan (offline)    |       1 |    1704 |        0.33  |     0.353 | 100.0% | 1%         |         0.134 |       0.147 |   0.407 |  0.332 | +1.195 [+1.020, +1.384] |                  1     |
| bc L=0                              |       3 |    1704 |       -1.176 |    -0.852 | 93.7%  | 31%        |         1.908 |      -1.428 |  -1.071 | -1.146 | -0.311 [-0.514, -0.088] |                 -0.26  |
| bc L=2                              |       3 |    1704 |       -0.67  |    -0.394 | 97.5%  | 29%        |         1.624 |      -0.849 |  -0.594 | -0.649 | -0.014 [-0.181, +0.167] |                 -0.015 |
| bc_ppo L=0                          |       3 |    1704 |       -0.562 |    -0.487 | 94.6%  | 11%        |         0.439 |      -0.622 |  -0.537 | -0.547 | +0.304 [+0.164, +0.444] |                  0.254 |
| bc_ppo L=2                          |       3 |    1704 |       -0.396 |    -0.318 | 95.8%  | 11%        |         0.459 |      -0.469 |  -0.365 | -0.389 | +0.259 [+0.158, +0.367] |                  0.263 |
| bc_ppo_lag L=0                      |       3 |    1704 |       -0.603 |    -0.556 | 93.4%  | 7%         |         0.277 |      -0.659 |  -0.579 | -0.592 | +0.262 [+0.114, +0.413] |                  0.22  |
| bc_ppo_lag L=2                      |       3 |    1704 |       -0.425 |    -0.373 | 94.9%  | 7%         |         0.306 |      -0.49  |  -0.398 | -0.416 | +0.230 [+0.132, +0.337] |                  0.233 |
| ppo L=0                             |       3 |    1704 |       -0.606 |    -0.483 | 95.4%  | 16%        |         0.721 |      -0.649 |  -0.588 | -0.596 | +0.260 [+0.145, +0.385] |                  0.217 |
| ppo L=2                             |       3 |    1704 |       -0.411 |    -0.302 | 96.9%  | 15%        |         0.637 |      -0.482 |  -0.381 | -0.405 | +0.244 [+0.162, +0.335] |                  0.248 |
| ppo_pid L=0                         |       3 |    1704 |       -0.687 |    -0.635 | 92.8%  | 7%         |         0.308 |      -0.702 |  -0.681 | -0.68  | +0.178 [+0.055, +0.311] |                  0.149 |
| ppo_pid L=2                         |       3 |    1704 |       -0.447 |    -0.398 | 94.9%  | 7%         |         0.284 |      -0.53  |  -0.412 | -0.439 | +0.208 [+0.117, +0.314] |                  0.212 |
