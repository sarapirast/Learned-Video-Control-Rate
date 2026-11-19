# D41 hindsight oracle, live channel (x265, ladder)

Channel AR(1) rho 0.8, sigma 0.3, cap 1.0 s, 0.5 dB per 1 % stalled. The oracle knows every GOP's curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = (method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.

## v1 test (n = 8) (2172 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed      | cases > oracle   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:----------------|:-----------------|
| oracle (hindsight) | -       |       -0.807 |     1.032 | +1.844 [+1.552, +2.269] | 100%            | nan              |
| vbv2               | 1       |       -2.651 |     2.353 |                         | 0%              | 0.0%             |
| mpc                | 1       |       -2.606 |     2.275 | +0.045 [-0.092, +0.209] | 2% [-5, 10]     | 0.0%             |
| il                 | 3       |       -3.607 |     4.758 | -0.956 [-1.288, -0.718] | -52% [-69, -37] | 0.0%             |
| il_ppo             | 3       |       -2.041 |     1.49  | +0.610 [+0.401, +0.903] | 33% [26, 40]    | 0.0%             |
| il_ppo_rr          | 1       |       -2.03  |     1.424 | +0.621 [+0.399, +0.946] | 34% [25, 42]    | 0.0%             |
| ppo_v2             | 3       |       -2.263 |     1.603 | +0.388 [+0.234, +0.608] | 21% [15, 27]    | 0.0%             |

Search check: best DP plan alone -0.915; oracle beats the best seeded method on 98% of cases; start of the winning local search: {'dp': 1941, 'const': 158, 'vbv': 46, 'ppo': 15, 'mpc': 12}.

## test playlists (n = 16) (1800 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed      | cases > oracle   |
|:-------------------|:--------|-------------:|----------:|:------------------------|:----------------|:-----------------|
| oracle (hindsight) | -       |       -1.679 |     2.034 | +1.686 [+1.539, +1.886] | 100%            | nan              |
| vbv2               | 1       |       -3.366 |     3.02  |                         | 0%              | 0.0%             |
| mpc                | 1       |       -3.36  |     3.198 | +0.006 [-0.156, +0.132] | 0% [-9, 7]      | 0.0%             |
| il                 | 3       |       -4.519 |     5.897 | -1.154 [-1.271, -0.948] | -68% [-77, -53] | 0.0%             |
| il_ppo             | 3       |       -2.924 |     2.459 | +0.442 [+0.305, +0.633] | 26% [20, 34]    | 0.0%             |
| il_ppo_rr          | 1       |       -2.919 |     2.43  | +0.447 [+0.299, +0.646] | 27% [19, 35]    | 0.0%             |
| ppo_v2             | 3       |       -3.041 |     2.42  | +0.324 [+0.226, +0.479] | 19% [15, 26]    | 0.0%             |

Search check: best DP plan alone -1.728; oracle beats the best seeded method on 99% of cases; start of the winning local search: {'dp': 1746, 'const': 27, 'vbv': 19, 'ppo': 7, 'mpc': 1}.
