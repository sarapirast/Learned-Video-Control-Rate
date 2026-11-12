# Lookahead curve (x264)

Penalised score = % bits saved at equal PSNR vs own constant QP − 2 × % over budget. 'share of search gain' = (policy − STATIC) / (hindsight search − STATIC), summed over test items. 'vs prev k' = paired difference to the previous k in the list (95 % CI).

| policy         |   k | split   |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs prev k      |   score_ci |   over_pct |
|:---------------|----:|:--------|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|-----------:|-----------:|
| CQL->PPO       |   0 | val     | 772 |   0.611 |   0.814 |    1.397 |    3.662 |   31.39  |  0     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   0 | test    | 958 |  -1.171 |   0.938 |    1.306 |    2.939 |   31.454 |  0     |       3 |                  0.571 | nan            |    nan     |    nan     |
| CQL->PPO       |   1 | val     | 772 |   3.859 |   0.701 |    3.861 |    5.48  |   17.53  |  0.967 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   1 | test    | 958 |   2.677 |   0.694 |    3.511 |    5.214 |   21.781 |  0.967 |       3 |                  0.719 | +3.848 ± 0.562 |    nan     |    nan     |
| CQL->PPO       |   2 | val     | 772 |   3.251 |   0.719 |    3.195 |    4.458 |   19.344 |  1.9   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   2 | test    | 958 |   1.74  |   0.695 |    2.539 |    4.011 |   25.226 |  1.9   |       3 |                  0.683 | -0.936 ± 0.378 |    nan     |    nan     |
| CQL->PPO       |   3 | val     | 772 |   3.006 |   0.725 |    2.978 |    5.269 |   25.907 |  2.8   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   3 | test    | 958 |   1.883 |   0.705 |    2.506 |    5.027 |   30.237 |  2.8   |       3 |                  0.689 | +0.142 ± 0.366 |    nan     |    nan     |
| CQL->PPO       |   4 | val     | 772 |   4.21  |   0.646 |    3.68  |    5.456 |   17.703 |  3.667 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   4 | test    | 958 |   3.143 |   0.625 |    3.12  |    5.267 |   24.426 |  3.667 |       3 |                  0.737 | +1.260 ± 0.376 |    nan     |    nan     |
| CQL->PPO       |   5 | val     | 772 |   1.864 |   0.778 |    2.407 |    4.823 |   28.152 |  4.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   5 | test    | 958 |   0.426 |   0.786 |    1.763 |    4.453 |   29.819 |  4.5   |       3 |                  0.632 | -2.717 ± 0.472 |    nan     |    nan     |
| CQL->PPO       |   6 | val     | 772 |   4.031 |   0.603 |    3.389 |    4.946 |   15.976 |  5.3   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   6 | test    | 958 |   3.035 |   0.559 |    2.982 |    4.635 |   20.39  |  5.3   |       3 |                  0.733 | +2.610 ± 0.473 |    nan     |    nan     |
| CQL->PPO       |   7 | val     | 772 |   3.939 |   0.597 |    3.437 |    5.266 |   14.724 |  6.067 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   7 | test    | 958 |   2.857 |   0.587 |    3.117 |    4.998 |   19.276 |  6.067 |       3 |                  0.726 | -0.178 ± 0.366 |    nan     |    nan     |
| CQL->PPO       |   8 | val     | 772 |   2.282 |   0.708 |    2.385 |    5.046 |   35.017 |  6.8   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   8 | test    | 958 |   0.697 |   0.707 |    1.361 |    4.591 |   36.534 |  6.8   |       3 |                  0.643 | -2.160 ± 0.462 |    nan     |    nan     |
| CQL->PPO       |   9 | val     | 772 |   3.819 |   0.681 |    3.602 |    5.534 |   16.235 |  7.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   9 | test    | 958 |   2.684 |   0.666 |    2.989 |    5.279 |   20.981 |  7.5   |       3 |                  0.719 | +1.987 ± 0.414 |    nan     |    nan     |
| CQL->PPO       |  10 | val     | 772 |   4.007 |   0.622 |    3.707 |    4.969 |   15.587 |  8.167 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  10 | test    | 958 |   2.903 |   0.626 |    2.764 |    4.598 |   19.589 |  8.167 |       3 |                  0.728 | +0.219 ± 0.443 |    nan     |    nan     |
| CQL->PPO       |  15 | val     | 772 |   3.702 |   0.658 |    3.312 |    5.292 |   21.071 | 11     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  15 | test    | 958 |   2.422 |   0.645 |    2.695 |    4.859 |   23.834 | 11     |       3 |                  0.709 | -0.481 ± 0.416 |    nan     |    nan     |
| CQL->PPO       |  20 | val     | 772 |   3.873 |   0.621 |    3.736 |    4.998 |   17.358 | 13     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  20 | test    | 958 |   2.973 |   0.569 |    2.849 |    4.616 |   19.833 | 13     |       3 |                  0.731 | +0.550 ± 0.364 |    nan     |    nan     |
| CQL->PPO       |  29 | val     | 772 |   3.123 |   0.712 |    3.026 |    4.787 |   17.142 | 14.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  29 | test    | 958 |   2.233 |   0.67  |    2.586 |    4.495 |   20.424 | 14.5   |       3 |                  0.702 | -0.739 ± 0.357 |    nan     |    nan     |
| lookahead rule |   0 | test    | 958 |  -5.393 | nan     |   -2.056 |   -1.627 |  nan     |  0     |     nan |                nan     | nan            |      0.908 |     48.017 |
| lookahead rule |   1 | test    | 958 |  -2.74  | nan     |   -0.75  |    0.725 |  nan     |  0.967 |     nan |                nan     | nan            |      0.916 |     46.138 |
| lookahead rule |   2 | test    | 958 |  -2.484 | nan     |   -0.626 |    0.429 |  nan     |  1.9   |     nan |                nan     | nan            |      0.871 |     41.858 |
| lookahead rule |   3 | test    | 958 |  -2.421 | nan     |   -0.694 |    0.263 |  nan     |  2.8   |     nan |                nan     | nan            |      0.841 |     39.77  |
| lookahead rule |   5 | test    | 958 |  -1.945 | nan     |   -0.562 |    0.325 |  nan     |  4.5   |     nan |                nan     | nan            |      0.809 |     35.804 |
| lookahead rule |   7 | test    | 958 |  -1.98  | nan     |   -0.691 |    0.18  |  nan     |  6.067 |     nan |                nan     | nan            |      0.811 |     35.699 |
| lookahead rule |  10 | test    | 958 |  -2.224 | nan     |   -0.722 |    0.052 |  nan     |  8.167 |     nan |                nan     | nan            |      0.817 |     35.804 |
| lookahead rule |  15 | test    | 958 |  -2.47  | nan     |   -0.731 |   -0.368 |  nan     | 11     |     nan |                nan     | nan            |      0.787 |     35.177 |
| lookahead rule |  20 | test    | 958 |  -2.971 | nan     |   -0.827 |   -0.808 |  nan     | 13     |     nan |                nan     | nan            |      0.831 |     36.013 |
| lookahead rule |  29 | test    | 958 |  -3.449 | nan     |   -0.86  |   -1.214 |  nan     | 14.5   |     nan |                nan     | nan            |      0.827 |     34.342 |
