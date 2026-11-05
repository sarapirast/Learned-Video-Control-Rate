# Lookahead curve (x265)

Penalised score = % bits saved at equal PSNR vs own constant QP − 2 × % over budget. 'share of search gain' = (policy − STATIC) / (hindsight search − STATIC), summed over test items. 'vs prev k' = paired difference to the previous k in the list (95 % CI).

| policy         |   k | split   |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs prev k      |   score_ci |   over_pct |
|:---------------|----:|:--------|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|-----------:|-----------:|
| CQL->PPO       |   0 | val     | 772 |   2.462 |   0.757 |    2.582 |    4.666 |   23.446 |  0     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   0 | test    | 958 |   0.737 |   0.828 |    1.848 |    3.972 |   27.662 |  0     |       3 |                  0.596 | nan            |    nan     |    nan     |
| CQL->PPO       |   1 | val     | 772 |   3.414 |   0.665 |    2.594 |    4.789 |   14.076 |  0.967 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   1 | test    | 958 |   2.3   |   0.648 |    1.725 |    4.293 |   16.388 |  0.967 |       3 |                  0.66  | +1.564 ± 0.428 |    nan     |    nan     |
| CQL->PPO       |   2 | val     | 772 |   5.025 |   0.573 |    3.789 |    5.834 |   12.176 |  1.9   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   2 | test    | 958 |   3.808 |   0.587 |    3.073 |    5.281 |   15.936 |  1.9   |       3 |                  0.722 | +1.507 ± 0.300 |    nan     |    nan     |
| CQL->PPO       |   3 | val     | 772 |   5.35  |   0.552 |    4.21  |    5.962 |    9.672 |  2.8   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   3 | test    | 958 |   4.095 |   0.54  |    3.394 |    5.341 |   15.275 |  2.8   |       3 |                  0.734 | +0.287 ± 0.252 |    nan     |    nan     |
| CQL->PPO       |   4 | val     | 772 |   4.363 |   0.609 |    3.611 |    5.512 |   14.206 |  3.667 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   4 | test    | 958 |   2.566 |   0.692 |    2.712 |    4.752 |   19.033 |  3.667 |       3 |                  0.671 | -1.529 ± 0.363 |    nan     |    nan     |
| CQL->PPO       |   5 | val     | 772 |   4.479 |   0.602 |    3.33  |    5.61  |   17.832 |  4.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   5 | test    | 958 |   3.482 |   0.601 |    2.657 |    5.112 |   20.181 |  4.5   |       3 |                  0.709 | +0.916 ± 0.373 |    nan     |    nan     |
| CQL->PPO       |   6 | val     | 772 |   4.522 |   0.591 |    3.435 |    5.405 |   10.406 |  5.3   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   6 | test    | 958 |   3.457 |   0.596 |    3.098 |    4.881 |   13.152 |  5.3   |       3 |                  0.708 | -0.025 ± 0.299 |    nan     |    nan     |
| CQL->PPO       |   7 | val     | 772 |   5.078 |   0.577 |    4.002 |    5.528 |    6.174 |  6.067 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   7 | test    | 958 |   4.167 |   0.562 |    3.46  |    4.954 |    8.873 |  6.067 |       3 |                  0.737 | +0.710 ± 0.316 |    nan     |    nan     |
| CQL->PPO       |   8 | val     | 772 |   4.785 |   0.565 |    3.675 |    5.5   |   11.615 |  6.8   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   8 | test    | 958 |   3.013 |   0.657 |    2.787 |    4.985 |   16.493 |  6.8   |       3 |                  0.69  | -1.153 ± 0.416 |    nan     |    nan     |
| CQL->PPO       |   9 | val     | 772 |   5.049 |   0.568 |    4.085 |    5.705 |   12.824 |  7.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |   9 | test    | 958 |   4.451 |   0.538 |    3.389 |    5.468 |   16.319 |  7.5   |       3 |                  0.749 | +1.437 ± 0.390 |    nan     |    nan     |
| CQL->PPO       |  10 | val     | 772 |   4.643 |   0.589 |    3.887 |    5.703 |   15.587 |  8.167 |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  10 | test    | 958 |   3.178 |   0.625 |    2.961 |    5.183 |   21.19  |  8.167 |       3 |                  0.696 | -1.273 ± 0.403 |    nan     |    nan     |
| CQL->PPO       |  15 | val     | 772 |   3.824 |   0.682 |    2.967 |    5.587 |   18.696 | 11     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  15 | test    | 958 |   1.499 |   0.812 |    1.993 |    4.971 |   22.477 | 11     |       3 |                  0.627 | -1.678 ± 0.442 |    nan     |    nan     |
| CQL->PPO       |  20 | val     | 772 |   4.928 |   0.557 |    3.608 |    5.426 |    5.786 | 13     |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  20 | test    | 958 |   3.681 |   0.595 |    3.333 |    4.867 |   10.995 | 13     |       3 |                  0.717 | +2.181 ± 0.547 |    nan     |    nan     |
| CQL->PPO       |  29 | val     | 772 |   3.639 |   0.633 |    2.806 |    4.85  |   12.522 | 14.5   |       3 |                nan     | nan            |    nan     |    nan     |
| CQL->PPO       |  29 | test    | 958 |   2.369 |   0.649 |    2.201 |    4.484 |   16.701 | 14.5   |       3 |                  0.663 | -1.312 ± 0.368 |    nan     |    nan     |
| lookahead rule |   0 | test    | 958 |  -6.003 | nan     |   -2.756 |   -1.98  |  nan     |  0     |     nan |                nan     | nan            |      0.864 |     48.643 |
| lookahead rule |   1 | test    | 958 |  -2.842 | nan     |   -0.904 |    0.599 |  nan     |  0.967 |     nan |                nan     | nan            |      0.895 |     46.451 |
| lookahead rule |   2 | test    | 958 |  -2.891 | nan     |   -0.924 |    0.346 |  nan     |  1.9   |     nan |                nan     | nan            |      0.873 |     43.633 |
| lookahead rule |   3 | test    | 958 |  -2.606 | nan     |   -0.795 |    0.384 |  nan     |  2.8   |     nan |                nan     | nan            |      0.824 |     45.407 |
| lookahead rule |   5 | test    | 958 |  -2.512 | nan     |   -0.845 |    0.049 |  nan     |  4.5   |     nan |                nan     | nan            |      0.781 |     40.919 |
| lookahead rule |   7 | test    | 958 |  -2.585 | nan     |   -1.113 |   -0.175 |  nan     |  6.067 |     nan |                nan     | nan            |      0.756 |     40.814 |
| lookahead rule |  10 | test    | 958 |  -2.724 | nan     |   -1.226 |   -0.353 |  nan     |  8.167 |     nan |                nan     | nan            |      0.745 |     39.353 |
| lookahead rule |  15 | test    | 958 |  -3.081 | nan     |   -1.237 |   -0.739 |  nan     | 11     |     nan |                nan     | nan            |      0.772 |     38.309 |
| lookahead rule |  20 | test    | 958 |  -3.664 | nan     |   -1.279 |   -1.291 |  nan     | 13     |     nan |                nan     | nan            |      0.811 |     37.37  |
| lookahead rule |  29 | test    | 958 |  -3.708 | nan     |   -1.152 |   -1.373 |  nan     | 14.5   |     nan |                nan     | nan            |      0.766 |     38.935 |
