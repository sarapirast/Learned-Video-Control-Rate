# D41 hindsight oracle, live channel (x265, trace)

Channel Belgium 4G/LTE throughput traces, cap 1.0 s, 0.5 dB per 1 % stalled. The oracle knows every GOP's curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = (method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.

## v1 test (n = 8) (20 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:-------------|
| oracle (hindsight) | -       |        0.138 |     0     | +1.739 [+1.739, +1.739] | 100%         |
| vbv2               | 1       |       -1.601 |     0.08  |                         | 0%           |
| mpc                | 1       |       -1.583 |     0.021 | +0.018 [+0.018, +0.018] | 1% [1, 1]    |
| ppo_v2             | 3       |       -1.267 |     0.126 | +0.334 [+0.334, +0.334] | 19% [19, 19] |

Search check: best DP plan alone -0.022; oracle beats the best seeded method on 100% of cases; start of the winning local search: {'dp': 18, 'const': 2}.
