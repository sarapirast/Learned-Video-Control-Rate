# D41 hindsight oracle, live channel (x264, trace_ladder)

Channel Belgium 4G/LTE throughput traces, cap 1.0 s, 0.5 dB per 1 % stalled. The oracle knows every GOP's curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = (method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.

## v1 test (n = 8) (2172 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed         | cases > oracle   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:-------------------|:-----------------|
| oracle (hindsight) | -       |       -2.684 |     4.422 | +2.922 [+2.614, +3.390] | 100%               | nan              |
| vbv2               | 1       |       -5.606 |     6.321 |                         | 0%                 | 0.0%             |
| mpc                | 1       |       -5.551 |     6.195 | +0.055 [-0.178, +0.306] | 2% [-6, 10]        | 0.0%             |
| il                 | 3       |       -9.412 |    15.372 | -3.806 [-4.773, -3.132] | -130% [-158, -108] | 0.0%             |
| il_ppo             | 3       |       -5.189 |     6.075 | +0.417 [+0.249, +0.622] | 14% [9, 19]        | 0.0%             |
| il_ppo_rr          | 1       |       -5.316 |     6.323 | +0.291 [+0.087, +0.492] | 10% [3, 16]        | 0.0%             |
| ppo_v2             | 3       |       -5.31  |     5.818 | +0.296 [+0.107, +0.549] | 10% [4, 17]        | 0.0%             |

Search check: best DP plan alone -2.800; oracle beats the best seeded method on 97% of cases; start of the winning local search: {'dp': 1892, 'const': 195, 'vbv': 46, 'ppo': 23, 'mpc': 16}.

## test playlists (n = 16) (1800 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed        | cases > oracle   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:------------------|:-----------------|
| oracle (hindsight) | -       |       -3.81  |     6.062 | +3.061 [+2.924, +3.238] | 100%              | nan              |
| vbv2               | 1       |       -6.871 |     8.316 |                         | 0%                | 0.0%             |
| mpc                | 1       |       -6.714 |     7.928 | +0.158 [+0.007, +0.337] | 5% [0, 11]        | 0.0%             |
| il                 | 3       |      -10.496 |    17.193 | -3.624 [-4.014, -3.044] | -118% [-133, -97] | 0.0%             |
| il_ppo             | 3       |       -6.412 |     7.751 | +0.460 [+0.359, +0.683] | 15% [12, 22]      | 0.0%             |
| il_ppo_rr          | 1       |       -6.534 |     7.999 | +0.337 [+0.235, +0.513] | 11% [8, 16]       | 0.0%             |
| ppo_v2             | 3       |       -6.557 |     7.562 | +0.314 [+0.213, +0.546] | 10% [7, 17]       | 0.0%             |

Search check: best DP plan alone -3.874; oracle beats the best seeded method on 98% of cases; start of the winning local search: {'dp': 1726, 'const': 27, 'vbv': 20, 'ppo': 19, 'mpc': 8}.
