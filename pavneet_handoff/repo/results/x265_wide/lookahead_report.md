# Lookahead curve (x265)

Penalised score = % bits saved at equal PSNR vs own constant QP − 2 × % over budget. 'share of search gain' = (policy − STATIC) / (hindsight search − STATIC), summed over test items. 'vs prev k' = paired difference to the previous k in the list (95 % CI).

| policy         |   k | split   |    n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs prev k      |   score_ci |   over_pct |
|:---------------|----:|:--------|-----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|-----------:|-----------:|
| CQL->PPO       |   0 | val     | 1930 |   3.783 |   0.358 |    3.453 |    4.761 |   13.61  |  0     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   0 | test    | 2395 |   2.88  |   0.401 |    2.813 |    4.33  |   15.825 |  0     |       3 |                  0.691 | nan            |    nan     |    nan     |
| CQL->PPO       |   1 | val     | 1930 |   3.697 |   0.353 |    2.823 |    4.495 |   12.608 |  0.967 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   1 | test    | 2395 |   3.169 |   0.352 |    2.537 |    4.129 |   13.305 |  0.967 |       3 |                  0.703 | +0.289 ± 0.244 |    nan     |    nan     |
| CQL->PPO       |   2 | val     | 1930 |   3.632 |   0.371 |    2.94  |    5.018 |   20.397 |  1.9   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   2 | test    | 2395 |   2.67  |   0.39  |    2.368 |    4.533 |   23.493 |  1.9   |       3 |                  0.682 | -0.499 ± 0.197 |    nan     |    nan     |
| CQL->PPO       |   3 | val     | 1930 |   4.379 |   0.373 |    3.327 |    5.29  |   14.767 |  2.8   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   3 | test    | 2395 |   3.615 |   0.386 |    2.974 |    4.611 |   14.558 |  2.8   |       3 |                  0.722 | +0.944 ± 0.227 |    nan     |    nan     |
| CQL->PPO       |   4 | val     | 1930 |   4.087 |   0.368 |    3.203 |    5.12  |   12.055 |  3.667 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   4 | test    | 2395 |   3.431 |   0.372 |    2.787 |    4.827 |   15.017 |  3.667 |       3 |                  0.714 | -0.184 ± 0.195 |    nan     |    nan     |
| CQL->PPO       |   5 | val     | 1930 |   4.702 |   0.373 |    3.712 |    5.663 |   14.663 |  4.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   5 | test    | 2395 |   3.993 |   0.367 |    3.34  |    5.223 |   14.836 |  4.5   |       3 |                  0.738 | +0.563 ± 0.175 |    nan     |    nan     |
| CQL->PPO       |   6 | val     | 1930 |   3.569 |   0.373 |    2.561 |    4.929 |   21.503 |  5.3   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   6 | test    | 2395 |   2.671 |   0.382 |    2.197 |    4.548 |   23.786 |  5.3   |       3 |                  0.682 | -1.322 ± 0.177 |    nan     |    nan     |
| CQL->PPO       |   7 | val     | 1930 |   4.469 |   0.366 |    3.348 |    5.157 |   10.967 |  6.067 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   7 | test    | 2395 |   3.604 |   0.367 |    2.941 |    4.834 |   14.836 |  6.067 |       3 |                  0.722 | +0.933 ± 0.188 |    nan     |    nan     |
| CQL->PPO       |   8 | val     | 1930 |   5.178 |   0.365 |    4.077 |    5.748 |    8.325 |  6.8   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   8 | test    | 2395 |   4.217 |   0.366 |    3.464 |    5.2   |   11.608 |  6.8   |       3 |                  0.748 | +0.613 ± 0.155 |    nan     |    nan     |
| CQL->PPO       |   9 | val     | 1930 |   4.46  |   0.379 |    3.596 |    5.459 |   14.819 |  7.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   9 | test    | 2395 |   3.233 |   0.395 |    2.82  |    4.897 |   16.966 |  7.5   |       3 |                  0.706 | -0.984 ± 0.200 |    nan     |    nan     |
| CQL->PPO       |  10 | val     | 1930 |   3.614 |   0.41  |    2.893 |    5.286 |   23.351 |  8.167 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  10 | test    | 2395 |   2.171 |   0.423 |    1.968 |    4.699 |   27.891 |  8.167 |       3 |                  0.661 | -1.062 ± 0.183 |    nan     |    nan     |
| CQL->PPO       |  15 | val     | 1930 |   4.44  |   0.363 |    3.515 |    5.716 |   19.724 | 11     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  15 | test    | 2395 |   3.72  |   0.351 |    2.939 |    5.123 |   18.232 | 11     |       3 |                  0.727 | +1.550 ± 0.237 |    nan     |    nan     |
| CQL->PPO       |  20 | val     | 1930 |   2.345 |   0.445 |    2.346 |    5.202 |   30     | 13     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  20 | test    | 2395 |   0.454 |   0.521 |    1.314 |    4.687 |   34.085 | 13     |       3 |                  0.589 | -3.266 ± 0.352 |    nan     |    nan     |
| CQL->PPO       |  29 | val     | 1930 |   3.651 |   0.404 |    2.79  |    4.871 |   15.613 | 14.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  29 | test    | 2395 |   2.66  |   0.416 |    2.122 |    4.492 |   19.123 | 14.5   |       3 |                  0.682 | +2.206 ± 0.280 |    nan     |    nan     |
| lookahead rule |   0 | test    | 2395 |  -6.119 | nan     |   -2.637 |   -2.01  |  nan     |  0     |     nan |                nan     | nan            |      0.568 |     48.601 |
| lookahead rule |   1 | test    | 2395 |  -3.294 | nan     |   -0.996 |    0.302 |  nan     |  0.967 |     nan |                nan     | nan            |      0.578 |     47.474 |
| lookahead rule |   2 | test    | 2395 |  -3.058 | nan     |   -0.943 |    0.27  |  nan     |  1.9   |     nan |                nan     | nan            |      0.554 |     44.551 |
| lookahead rule |   3 | test    | 2395 |  -3     | nan     |   -0.808 |    0.139 |  nan     |  2.8   |     nan |                nan     | nan            |      0.547 |     43.758 |
| lookahead rule |   5 | test    | 2395 |  -2.803 | nan     |   -0.879 |   -0.036 |  nan     |  4.5   |     nan |                nan     | nan            |      0.522 |     41.712 |
| lookahead rule |   7 | test    | 2395 |  -2.774 | nan     |   -0.98  |   -0.207 |  nan     |  6.067 |     nan |                nan     | nan            |      0.514 |     39.875 |
| lookahead rule |  10 | test    | 2395 |  -2.97  | nan     |   -1.075 |   -0.444 |  nan     |  8.167 |     nan |                nan     | nan            |      0.515 |     39.749 |
| lookahead rule |  15 | test    | 2395 |  -3.238 | nan     |   -1.143 |   -0.726 |  nan     | 11     |     nan |                nan     | nan            |      0.508 |     38.789 |
| lookahead rule |  20 | test    | 2395 |  -3.807 | nan     |   -1.157 |   -1.252 |  nan     | 13     |     nan |                nan     | nan            |      0.539 |     37.704 |
| lookahead rule |  29 | test    | 2395 |  -4.119 | nan     |   -1.089 |   -1.618 |  nan     | 14.5   |     nan |                nan     | nan            |      0.535 |     38.038 |
