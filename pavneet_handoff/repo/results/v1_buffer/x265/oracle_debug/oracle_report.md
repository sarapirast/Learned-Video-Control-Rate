# D41 hindsight oracle, live channel (x265)

Channel AR(1) rho 0.8, sigma 0.3, cap 1.0 s, 0.5 dB per 1 % stalled. The oracle knows every GOP's curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = (method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.

## v1 test (n = 8) (20 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed      |
|:-------------------|:--------|-------------:|----------:|:------------------------|:----------------|
| oracle (hindsight) | -       |       -0.011 |     0.006 | +1.615 [+1.615, +1.615] | 100%            |
| vbv2               | 1       |       -1.626 |     1.137 |                         | 0%              |
| mpc                | 1       |       -2.33  |     2.878 | -0.704 [-0.704, -0.704] | -44% [-44, -44] |
| ppo_v2             | 3       |       -1.393 |     1.124 | +0.233 [+0.233, +0.233] | 14% [14, 14]    |

Search check: best DP plan alone -0.087; oracle beats the best seeded method on 100% of cases; start of the winning local search: {'dp': 20}.

## test playlists (n = 16) (10 cases)

| method             | seeds   |   score (dB) |   stall % | vs vbv2                 | gap closed         |
|:-------------------|:--------|-------------:|----------:|:------------------------|:-------------------|
| oracle (hindsight) | -       |       -0.069 |     0     | +0.587 [+0.587, +0.587] | 100%               |
| vbv2               | 1       |       -0.655 |     0.051 |                         | 0%                 |
| mpc                | 1       |       -1.423 |     0     | -0.767 [-0.767, -0.767] | -131% [-131, -131] |
| ppo_v2             | 3       |       -0.591 |     0.031 | +0.064 [+0.064, +0.064] | 11% [11, 11]       |

Search check: best DP plan alone -0.133; oracle beats the best seeded method on 100% of cases; start of the winning local search: {'dp': 10}.
