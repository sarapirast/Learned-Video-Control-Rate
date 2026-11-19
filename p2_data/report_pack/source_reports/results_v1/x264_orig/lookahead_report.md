# Lookahead curve (x264)

Penalised score = % bits saved at equal PSNR vs own constant QP − 2 × % over budget. 'share of search gain' = (policy − STATIC) / (hindsight search − STATIC), summed over test items. 'vs prev k' = paired difference to the previous k in the list (95 % CI).

| policy         |   k | split   |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs prev k      |   score_ci |   over_pct |
|:---------------|----:|:--------|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|-----------:|-----------:|
| CQL->PPO       |   0 | val     | 304 |   0.08  |   1.199 |    0.821 |    2.881 |   33.443 |  0     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   0 | test    | 530 |  -0.17  |   0.975 |    0.631 |    3.11  |   37.484 |  0     |       3 |                  0.473 | nan            |    nan     |    nan     |
| CQL->PPO       |   2 | val     | 304 |   2.906 |   1.003 |    2.753 |    4.5   |   25.987 |  1.9   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   2 | test    | 530 |   3.285 |   0.691 |    2.995 |    4.971 |   22.893 |  1.9   |       3 |                  0.669 | +3.455 ± 0.572 |    nan     |    nan     |
| CQL->PPO       |   5 | val     | 304 |   3.566 |   0.818 |    3.122 |    4.252 |   18.86  |  4.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   5 | test    | 530 |   3.75  |   0.618 |    3.315 |    4.667 |   13.836 |  4.5   |       3 |                  0.696 | +0.465 ± 0.331 |    nan     |    nan     |
| CQL->PPO       |  10 | val     | 304 |   2.943 |   0.941 |    3.373 |    4.067 |   19.627 |  8.167 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  10 | test    | 530 |   3.253 |   0.678 |    3.03  |    4.549 |   17.862 |  8.167 |       3 |                  0.668 | -0.497 ± 0.311 |    nan     |    nan     |
| CQL->PPO       |  29 | val     | 304 |   1.995 |   0.904 |    2.1   |    3.869 |   28.838 | 14.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  29 | test    | 530 |   2.089 |   0.647 |    1.793 |    4.023 |   27.421 | 14.5   |       3 |                  0.601 | -1.164 ± 0.333 |    nan     |    nan     |
| lookahead rule |   0 | test    | 530 |  -2.604 | nan     |   -1.501 |   -0.272 |  nan     |  0     |     nan |                nan     | nan            |      0.66  |     57.358 |
| lookahead rule |   1 | test    | 530 |  -1.062 | nan     |   -0.688 |    0.98  |  nan     |  0.967 |     nan |                nan     | nan            |      0.695 |     56.792 |
| lookahead rule |   2 | test    | 530 |  -1.013 | nan     |   -0.554 |    1.016 |  nan     |  1.9   |     nan |                nan     | nan            |      0.728 |     53.774 |
| lookahead rule |   3 | test    | 530 |  -0.991 | nan     |   -0.521 |    0.854 |  nan     |  2.8   |     nan |                nan     | nan            |      0.684 |     55.283 |
| lookahead rule |   5 | test    | 530 |  -0.912 | nan     |   -0.349 |    0.84  |  nan     |  4.5   |     nan |                nan     | nan            |      0.671 |     53.396 |
| lookahead rule |   7 | test    | 530 |  -0.885 | nan     |   -0.335 |    0.734 |  nan     |  6.067 |     nan |                nan     | nan            |      0.667 |     53.019 |
| lookahead rule |  10 | test    | 530 |  -1.166 | nan     |   -0.555 |    0.412 |  nan     |  8.167 |     nan |                nan     | nan            |      0.665 |     54.151 |
| lookahead rule |  15 | test    | 530 |  -1.218 | nan     |   -0.634 |    0.242 |  nan     | 11     |     nan |                nan     | nan            |      0.646 |     53.019 |
| lookahead rule |  20 | test    | 530 |  -1.333 | nan     |   -0.487 |    0.005 |  nan     | 13     |     nan |                nan     | nan            |      0.618 |     53.774 |
| lookahead rule |  29 | test    | 530 |  -1.653 | nan     |   -0.507 |   -0.385 |  nan     | 14.5   |     nan |                nan     | nan            |      0.619 |     51.698 |
