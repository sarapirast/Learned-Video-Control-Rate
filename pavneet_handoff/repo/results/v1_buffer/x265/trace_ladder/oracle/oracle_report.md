# D41 hindsight oracle, live channel (x265, trace_ladder)

Channel Belgium 4G/LTE throughput traces, cap 1.0 s, 0.5 dB per 1 % stalled. The oracle knows every GOP's curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = (method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.

## v1 test (n = 8) (2172 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed       | cases > oracle   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:-----------------|:-----------------|
| oracle (hindsight) | -       |       -1.707 |     2.805 | +2.959 [+2.564, +3.547] | 100%             | nan              |
| vbv2               | 1       |       -4.667 |     4.805 |                         | 0%               | 0.0%             |
| mpc                | 1       |       -4.61  |     4.797 | +0.057 [-0.239, +0.361] | 2% [-9, 11]      | 0.0%             |
| il                 | 3       |       -7.464 |    11.561 | -2.798 [-3.417, -2.316] | -95% [-115, -76] | 0.0%             |
| il_ppo             | 3       |       -4.312 |     4.7   | +0.355 [+0.162, +0.617] | 12% [6, 19]      | 0.0%             |
| il_ppo_rr          | 1       |       -4.578 |     5.146 | +0.089 [-0.172, +0.381] | 3% [-6, 12]      | 0.0%             |
| ppo_v2             | 3       |       -4.461 |     4.711 | +0.205 [+0.060, +0.396] | 7% [2, 12]       | 0.0%             |

Search check: best DP plan alone -1.825; oracle beats the best seeded method on 98% of cases; start of the winning local search: {'dp': 1937, 'const': 182, 'vbv': 38, 'mpc': 8, 'ppo': 7}.

## test playlists (n = 16) (1800 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed        | cases > oracle   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:------------------|:-----------------|
| oracle (hindsight) | -       |       -2.601 |     3.928 | +2.741 [+2.563, +2.969] | 100%              | nan              |
| vbv2               | 1       |       -5.342 |     5.531 |                         | 0%                | 0.0%             |
| mpc                | 1       |       -5.43  |     5.858 | -0.087 [-0.324, +0.108] | -3% [-12, 4]      | 0.0%             |
| il                 | 3       |       -8.072 |    12.079 | -2.730 [-3.084, -2.243] | -100% [-117, -78] | 0.0%             |
| il_ppo             | 3       |       -5.026 |     5.438 | +0.316 [+0.164, +0.481] | 12% [6, 17]       | 0.0%             |
| il_ppo_rr          | 1       |       -5.391 |     6.117 | -0.049 [-0.553, +0.275] | -2% [-19, 10]     | 0.0%             |
| ppo_v2             | 3       |       -5.138 |     5.409 | +0.204 [+0.117, +0.344] | 7% [4, 12]        | 0.0%             |

Search check: best DP plan alone -2.659; oracle beats the best seeded method on 99% of cases; start of the winning local search: {'dp': 1743, 'const': 32, 'vbv': 19, 'ppo': 5, 'mpc': 1}.
