# D41 hindsight oracle, live channel (x264)

Channel AR(1) rho 0.8, sigma 0.3, cap 1.0 s, 0.5 dB per 1 % stalled. The oracle knows every GOP's curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = (method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.

## v1 test (n = 8) (20 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed      |
|:-------------------|:--------|-------------:|----------:|:------------------------|:----------------|
| oracle (hindsight) | -       |        0.053 |     0.005 | +2.727 [+2.727, +2.727] | 100%            |
| vbv2               | 1       |       -2.674 |     3.25  |                         | 0%              |
| mpc                | 1       |       -3.006 |     3.936 | -0.332 [-0.332, -0.332] | -12% [-12, -12] |
| ppo_v2             | 3       |       -2.822 |     3.423 | -0.148 [-0.148, -0.148] | -5% [-5, -5]    |

Search check: best DP plan alone -0.040; oracle beats the best seeded method on 100% of cases; start of the winning local search: {'dp': 20}.

## test playlists (n = 16) (10 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:-------------|
| oracle (hindsight) | -       |       -0.072 |     0     | +1.105 [+1.105, +1.105] | 100%         |
| vbv2               | 1       |       -1.176 |     0.544 |                         | 0%           |
| mpc                | 1       |       -0.998 |     0     | +0.178 [+0.178, +0.178] | 16% [16, 16] |
| ppo_v2             | 3       |       -0.794 |     0     | +0.382 [+0.382, +0.382] | 35% [35, 35] |

Search check: best DP plan alone -0.186; oracle beats the best seeded method on 100% of cases; start of the winning local search: {'dp': 10}.
