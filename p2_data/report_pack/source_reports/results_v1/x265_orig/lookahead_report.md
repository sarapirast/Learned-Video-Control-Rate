# Lookahead curve (x265)

Penalised score = % bits saved at equal PSNR vs own constant QP − 2 × % over budget. 'share of search gain' = (policy − STATIC) / (hindsight search − STATIC), summed over test items. 'vs prev k' = paired difference to the previous k in the list (95 % CI).

| policy         |   k | split   |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs prev k      |   score_ci |   over_pct |
|:---------------|----:|:--------|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|-----------:|-----------:|
| CQL->PPO       |   0 | val     | 304 |   2.847 |   1.035 |    1.644 |    3.757 |   16.338 |  0     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   0 | test    | 530 |   3.493 |   0.753 |    2.818 |    4.546 |   15.66  |  0     |       3 |                  0.617 | nan            |    nan     |    nan     |
| CQL->PPO       |   2 | val     | 304 |   3.458 |   0.931 |    2.409 |    4.188 |   11.294 |  1.9   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   2 | test    | 530 |   4.008 |   0.69  |    3.171 |    4.971 |   13.836 |  1.9   |       3 |                  0.649 | +0.515 ± 0.318 |    nan     |    nan     |
| CQL->PPO       |   5 | val     | 304 |   4.317 |   0.852 |    2.841 |    4.877 |   13.158 |  4.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   5 | test    | 530 |   4.526 |   0.637 |    3.694 |    5.563 |   15.283 |  4.5   |       3 |                  0.682 | +0.518 ± 0.336 |    nan     |    nan     |
| CQL->PPO       |  10 | val     | 304 |   3.479 |   0.885 |    2.29  |    4.723 |   22.478 |  8.167 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  10 | test    | 530 |   3.881 |   0.616 |    3.211 |    5.138 |   22.893 |  8.167 |       3 |                  0.642 | -0.645 ± 0.299 |    nan     |    nan     |
| CQL->PPO       |  29 | val     | 304 |   3.766 |   0.926 |    2.577 |    4.723 |   14.254 | 14.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  29 | test    | 530 |   3.819 |   0.682 |    3.505 |    5.143 |   15.849 | 14.5   |       3 |                  0.638 | -0.062 ± 0.342 |    nan     |    nan     |
| lookahead rule |   0 | test    | 530 |  -2.944 | nan     |   -1.84  |   -1.154 |  nan     |  0     |     nan |                nan     | nan            |      0.643 |     40.189 |
| lookahead rule |   1 | test    | 530 |  -0.902 | nan     |   -0.593 |    1.015 |  nan     |  0.967 |     nan |                nan     | nan            |      0.722 |     42.642 |
| lookahead rule |   2 | test    | 530 |  -0.808 | nan     |   -0.607 |    0.88  |  nan     |  1.9   |     nan |                nan     | nan            |      0.688 |     38.868 |
| lookahead rule |   3 | test    | 530 |  -0.9   | nan     |   -0.64  |    0.72  |  nan     |  2.8   |     nan |                nan     | nan            |      0.692 |     38.113 |
| lookahead rule |   5 | test    | 530 |  -0.908 | nan     |   -0.679 |    0.524 |  nan     |  4.5   |     nan |                nan     | nan            |      0.633 |     36.226 |
| lookahead rule |   7 | test    | 530 |  -0.86  | nan     |   -0.603 |    0.337 |  nan     |  6.067 |     nan |                nan     | nan            |      0.59  |     34.906 |
| lookahead rule |  10 | test    | 530 |  -1.1   | nan     |   -0.823 |    0.121 |  nan     |  8.167 |     nan |                nan     | nan            |      0.614 |     35.283 |
| lookahead rule |  15 | test    | 530 |  -1.498 | nan     |   -0.981 |   -0.278 |  nan     | 11     |     nan |                nan     | nan            |      0.666 |     34.717 |
| lookahead rule |  20 | test    | 530 |  -2.043 | nan     |   -1.019 |   -0.739 |  nan     | 13     |     nan |                nan     | nan            |      0.689 |     36.792 |
| lookahead rule |  29 | test    | 530 |  -2.164 | nan     |   -0.84  |   -0.936 |  nan     | 14.5   |     nan |                nan     | nan            |      0.694 |     31.887 |
