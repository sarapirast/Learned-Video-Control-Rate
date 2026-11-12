# Stream-level rate control, dataset v1 (x264, val)

Streams of 8 IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one budget = s x sum of the GOPs' v1 budgets at level q0, q0 in (24, 30, 36, 42), s in (0.85, 1.0, 1.18). Each step picks one GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).

Margins tuned on val: split L=0: m=0.96; rule L=0: m=0.98; rule L=2: m=0.98.

| method                              |   seeds |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |    s=1 | vs rule (same L)        |   share of ceiling gap |
|:------------------------------------|--------:|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|-------:|:------------------------|-----------------------:|
| equal split per GOP (tuned m)       |       1 |    1704 |       -1.513 |    -1.153 | 95.3%  | 27%        |         2.12  |      -0.953 |  -1.749 | -1.511 | -0.524 [-0.649, -0.421] |                 -0.398 |
| remaining-budget rule (tuned m) L=0 |       1 |    1704 |       -0.989 |    -0.844 | 96.6%  | 19%        |         0.851 |      -0.683 |  -1.117 | -0.982 | nan                     |                  0     |
| remaining-budget rule (tuned m) L=2 |       1 |    1704 |       -0.768 |    -0.63  | 96.8%  | 16%        |         0.814 |      -0.557 |  -0.857 | -0.76  | nan                     |                  0     |
| best constant QP (offline)          |       1 |    1704 |       -0.218 |    -0.107 | 97.4%  | 23%        |         0.653 |      -0.195 |  -0.227 | -0.204 | +0.771 [+0.602, +0.963] |                  0.585 |
| hindsight per-GOP plan (offline)    |       1 |    1704 |        0.33  |     0.353 | 100.0% | 1%         |         0.134 |       0.147 |   0.407 |  0.332 | +1.319 [+1.108, +1.537] |                  1     |
| bc L=2                              |       1 |    1704 |       -0.63  |    -0.272 | 100.2% | 37%        |         2.11  |      -0.569 |  -0.656 | -0.601 | +0.138 [+0.052, +0.239] |                  0.126 |
| bc_ppo L=2                          |       1 |    1704 |       -0.545 |    -0.367 | 97.7%  | 23%        |         1.049 |      -0.503 |  -0.563 | -0.542 | +0.223 [+0.141, +0.320] |                  0.203 |
| bc_ppo_lag L=2                      |       1 |    1704 |       -0.584 |    -0.476 | 95.3%  | 14%        |         0.631 |      -0.596 |  -0.578 | -0.566 | +0.185 [+0.070, +0.315] |                  0.168 |
| ppo L=2                             |       1 |    1704 |       -0.825 |    -0.751 | 93.5%  | 12%        |         0.437 |      -0.654 |  -0.897 | -0.826 | -0.057 [-0.132, +0.040] |                 -0.052 |
