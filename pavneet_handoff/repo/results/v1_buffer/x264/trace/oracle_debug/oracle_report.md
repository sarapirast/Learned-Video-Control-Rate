# D41 hindsight oracle, live channel (x264, trace)

Channel Belgium 4G/LTE throughput traces, cap 1.0 s, 0.5 dB per 1 % stalled. The oracle knows every GOP's curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = (method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.

## v1 test (n = 8) (20 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:-------------|
| oracle (hindsight) | -       |        0.213 |     0     | +2.967 [+2.967, +2.967] | 100%         |
| vbv2               | 1       |       -2.754 |     0.058 |                         | 0%           |
| mpc                | 1       |       -2.341 |     1.575 | +0.413 [+0.413, +0.413] | 14% [14, 14] |
| ppo_v2             | 3       |       -2.283 |     0.669 | +0.471 [+0.471, +0.471] | 16% [16, 16] |

Search check: best DP plan alone +0.082; oracle beats the best seeded method on 100% of cases; start of the winning local search: {'dp': 19, 'mpc': 1}.
