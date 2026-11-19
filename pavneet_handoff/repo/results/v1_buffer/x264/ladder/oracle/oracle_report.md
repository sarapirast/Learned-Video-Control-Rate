# D41 hindsight oracle, live channel (x264, ladder)

Channel AR(1) rho 0.8, sigma 0.3, cap 1.0 s, 0.5 dB per 1 % stalled. The oracle knows every GOP's curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = (method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.

## v1 test (n = 8) (2172 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed       | cases > oracle   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:-----------------|:-----------------|
| oracle (hindsight) | -       |       -1.379 |     1.845 | +1.844 [+1.598, +2.188] | 100%             | nan              |
| vbv2               | 1       |       -3.223 |     2.938 |                         | 0%               | 0.0%             |
| mpc                | 1       |       -3.347 |     3.178 | -0.124 [-0.264, +0.002] | -7% [-13, 0]     | 0.0%             |
| il                 | 3       |       -4.822 |     6.671 | -1.599 [-2.175, -1.203] | -87% [-110, -66] | 0.0%             |
| il_ppo             | 3       |       -2.775 |     2.523 | +0.448 [+0.347, +0.582] | 24% [20, 28]     | 0.0%             |
| il_ppo_rr          | 1       |       -2.793 |     2.567 | +0.430 [+0.321, +0.563] | 23% [18, 28]     | 0.0%             |
| ppo_v2             | 3       |       -2.952 |     2.638 | +0.271 [+0.188, +0.371] | 15% [11, 18]     | 0.0%             |

Search check: best DP plan alone -1.490; oracle beats the best seeded method on 97% of cases; start of the winning local search: {'dp': 1891, 'const': 180, 'vbv': 54, 'ppo': 30, 'mpc': 17}.

## test playlists (n = 16) (1800 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed       | cases > oracle   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:-----------------|:-----------------|
| oracle (hindsight) | -       |       -2.464 |     3.304 | +1.862 [+1.749, +1.975] | 100%             | nan              |
| vbv2               | 1       |       -4.326 |     4.508 |                         | 0%               | 0.0%             |
| mpc                | 1       |       -4.299 |     4.47  | +0.027 [-0.122, +0.133] | 1% [-7, 7]       | 0.0%             |
| il                 | 3       |       -5.98  |     8.555 | -1.654 [-1.927, -1.421] | -89% [-105, -74] | 0.0%             |
| il_ppo             | 3       |       -3.868 |     3.901 | +0.458 [+0.379, +0.538] | 25% [20, 29]     | 0.0%             |
| il_ppo_rr          | 1       |       -3.882 |     3.965 | +0.444 [+0.360, +0.526] | 24% [19, 28]     | 0.0%             |
| ppo_v2             | 3       |       -3.949 |     3.836 | +0.377 [+0.311, +0.473] | 20% [17, 25]     | 0.0%             |

Search check: best DP plan alone -2.520; oracle beats the best seeded method on 98% of cases; start of the winning local search: {'dp': 1723, 'const': 35, 'ppo': 21, 'vbv': 19, 'mpc': 2}.
