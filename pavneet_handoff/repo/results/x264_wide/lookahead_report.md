# Lookahead curve (x264)

Penalised score = % bits saved at equal PSNR vs own constant QP − 2 × % over budget. 'share of search gain' = (policy − STATIC) / (hindsight search − STATIC), summed over test items. 'vs prev k' = paired difference to the previous k in the list (95 % CI).

| policy         |   k | split   |    n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs prev k      |   score_ci |   over_pct |
|:---------------|----:|:--------|-----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|-----------:|-----------:|
| CQL->PPO       |   0 | val     | 1930 |   2.965 |   0.399 |    3.108 |    4.035 |   13.938 |  0     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   0 | test    | 2395 |   1.822 |   0.449 |    2.578 |    3.588 |   17.801 |  0     |       3 |                  0.689 | nan            |    nan     |    nan     |
| CQL->PPO       |   1 | val     | 1930 |   3.088 |   0.393 |    2.846 |    4.406 |   13.23  |  0.967 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   1 | test    | 2395 |   1.984 |   0.46  |    2.602 |    3.796 |   14.781 |  0.967 |       3 |                  0.696 | +0.161 ± 0.282 |    nan     |    nan     |
| CQL->PPO       |   2 | val     | 1930 |   3.607 |   0.381 |    3.227 |    4.848 |   15.423 |  1.9   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   2 | test    | 2395 |   2.717 |   0.434 |    2.788 |    4.319 |   18.079 |  1.9   |       3 |                  0.724 | +0.733 ± 0.235 |    nan     |    nan     |
| CQL->PPO       |   3 | val     | 1930 |   4.198 |   0.364 |    3.562 |    5.352 |   17.392 |  2.8   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   3 | test    | 2395 |   3.12  |   0.398 |    3.019 |    4.72  |   19.986 |  2.8   |       3 |                  0.74  | +0.403 ± 0.189 |    nan     |    nan     |
| CQL->PPO       |   4 | val     | 1930 |   4.002 |   0.405 |    3.468 |    5.066 |   14.94  |  3.667 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   4 | test    | 2395 |   2.831 |   0.441 |    3.04  |    4.413 |   18.121 |  3.667 |       3 |                  0.729 | -0.289 ± 0.204 |    nan     |    nan     |
| CQL->PPO       |   5 | val     | 1930 |   3.943 |   0.402 |    3.606 |    4.883 |   13.851 |  4.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   5 | test    | 2395 |   2.787 |   0.431 |    3.023 |    4.394 |   17.411 |  4.5   |       3 |                  0.727 | -0.043 ± 0.184 |    nan     |    nan     |
| CQL->PPO       |   6 | val     | 1930 |   3.27  |   0.389 |    2.974 |    4.945 |   23.282 |  5.3   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   6 | test    | 2395 |   1.87  |   0.431 |    2.126 |    4.533 |   28.462 |  5.3   |       3 |                  0.691 | -0.918 ± 0.262 |    nan     |    nan     |
| CQL->PPO       |   7 | val     | 1930 |   3.546 |   0.374 |    3.14  |    4.832 |   19.188 |  6.067 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   7 | test    | 2395 |   2.612 |   0.44  |    2.794 |    4.479 |   21.614 |  6.067 |       3 |                  0.72  | +0.743 ± 0.247 |    nan     |    nan     |
| CQL->PPO       |   8 | val     | 1930 |   3.156 |   0.385 |    2.857 |    4.951 |   19.948 |  6.8   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   8 | test    | 2395 |   2.452 |   0.446 |    2.801 |    4.655 |   21.1   |  6.8   |       3 |                  0.714 | -0.161 ± 0.244 |    nan     |    nan     |
| CQL->PPO       |   9 | val     | 1930 |   4.174 |   0.367 |    3.451 |    5.213 |   15.06  |  7.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   9 | test    | 2395 |   2.985 |   0.425 |    2.976 |    4.552 |   16.868 |  7.5   |       3 |                  0.735 | +0.533 ± 0.267 |    nan     |    nan     |
| CQL->PPO       |  10 | val     | 1930 |   4.507 |   0.332 |    3.588 |    5.244 |   13.903 |  8.167 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  10 | test    | 2395 |   3.464 |   0.373 |    3.198 |    4.884 |   17.481 |  8.167 |       3 |                  0.753 | +0.480 ± 0.188 |    nan     |    nan     |
| CQL->PPO       |  15 | val     | 1930 |   3.873 |   0.378 |    3.419 |    4.75  |   13.644 | 11     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  15 | test    | 2395 |   2.91  |   0.41  |    3.028 |    4.33  |   16.576 | 11     |       3 |                  0.732 | -0.555 ± 0.239 |    nan     |    nan     |
| CQL->PPO       |  20 | val     | 1930 |   3.833 |   0.357 |    3.294 |    4.978 |   12.504 | 13     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  20 | test    | 2395 |   3.044 |   0.387 |    3.097 |    4.34  |   12.401 | 13     |       3 |                  0.737 | +0.134 ± 0.240 |    nan     |    nan     |
| CQL->PPO       |  29 | val     | 1930 |   0.154 |   0.434 |    0.569 |    3.963 |   34.387 | 14.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  29 | test    | 2395 |  -0.42  |   0.448 |    0.252 |    3.748 |   35.63  | 14.5   |       3 |                  0.602 | -3.464 ± 0.291 |    nan     |    nan     |
| lookahead rule |   0 | test    | 2395 |  -5.422 | nan     |   -2.138 |   -1.703 |  nan     |  0     |     nan |                nan     | nan            |      0.599 |     46.18  |
| lookahead rule |   1 | test    | 2395 |  -3.282 | nan     |   -0.989 |    0.232 |  nan     |  0.967 |     nan |                nan     | nan            |      0.622 |     45.804 |
| lookahead rule |   2 | test    | 2395 |  -3.008 | nan     |   -0.916 |    0.062 |  nan     |  1.9   |     nan |                nan     | nan            |      0.596 |     41.169 |
| lookahead rule |   3 | test    | 2395 |  -2.829 | nan     |   -0.96  |   -0.046 |  nan     |  2.8   |     nan |                nan     | nan            |      0.57  |     38.789 |
| lookahead rule |   5 | test    | 2395 |  -2.477 | nan     |   -0.831 |   -0.04  |  nan     |  4.5   |     nan |                nan     | nan            |      0.543 |     36.618 |
| lookahead rule |   7 | test    | 2395 |  -2.505 | nan     |   -0.835 |   -0.144 |  nan     |  6.067 |     nan |                nan     | nan            |      0.55  |     35.282 |
| lookahead rule |  10 | test    | 2395 |  -2.687 | nan     |   -0.828 |   -0.342 |  nan     |  8.167 |     nan |                nan     | nan            |      0.548 |     35.031 |
| lookahead rule |  15 | test    | 2395 |  -2.783 | nan     |   -0.912 |   -0.589 |  nan     | 11     |     nan |                nan     | nan            |      0.503 |     34.447 |
| lookahead rule |  20 | test    | 2395 |  -3.16  | nan     |   -0.988 |   -0.932 |  nan     | 13     |     nan |                nan     | nan            |      0.517 |     34.99  |
| lookahead rule |  29 | test    | 2395 |  -3.636 | nan     |   -0.939 |   -1.355 |  nan     | 14.5   |     nan |                nan     | nan            |      0.52  |     33.862 |
