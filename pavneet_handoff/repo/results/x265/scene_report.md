# Scene intelligence and dynamic lookahead (x265)

## Lookahead modes

'seen' = mean future frames visible per decision (the cost of lookahead).

| policy             | mode        |   k cap |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |   score_ci |   over_pct |
|:-------------------|:------------|--------:|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|-----------:|-----------:|
| dedicated CQL->PPO | cut_trig    |       5 | 958 |   3.319 |   0.646 |    3.318 |    4.842 |   14.718 |  0.204 |       3 |                  0.702 |    nan     |    nan     |
| dedicated CQL->PPO | cut_trig    |      10 | 958 |   2.007 |   0.716 |    2.297 |    4.449 |   24.635 |  0.647 |       3 |                  0.648 |    nan     |    nan     |
| dedicated CQL->PPO | cut_trig    |      29 | 958 |   2.75  |   0.711 |    2.744 |    4.569 |   17.049 |  2.014 |       3 |                  0.679 |    nan     |    nan     |
| any-k CQL->PPO     | cut_trig    |       5 | 958 |   1.571 |   0.54  |    1.547 |    1.604 |    1.322 |  0.204 |       3 |                  0.63  |    nan     |    nan     |
| any-k CQL->PPO     | cut_trig    |      10 | 958 |   1.534 |   0.558 |    1.504 |    1.624 |    1.531 |  0.647 |       3 |                  0.629 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       0 | 958 |   1.577 |   0.551 |    1.682 |    1.592 |    1.113 |  0     |       3 |                  0.63  |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       1 | 958 |   3.193 |   0.44  |    2.639 |    3.255 |    2.088 |  0.967 |       3 |                  0.697 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       2 | 958 |   3.621 |   0.46  |    2.87  |    3.816 |    3.862 |  1.9   |       3 |                  0.715 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       3 | 958 |   4.017 |   0.454 |    3.336 |    4.462 |    5.637 |  2.8   |       3 |                  0.731 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |       5 | 958 |   3.482 |   0.601 |    2.657 |    5.112 |   20.181 |  4.5   |       3 |                  0.709 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       5 | 958 |   4.503 |   0.415 |    3.664 |    4.866 |    5.324 |  4.5   |       3 |                  0.751 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       7 | 958 |   3.743 |   0.438 |    3.345 |    4.455 |    7.481 |  6.067 |       3 |                  0.72  |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      10 | 958 |   3.178 |   0.625 |    2.961 |    5.183 |   21.19  |  8.167 |       3 |                  0.696 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |      10 | 958 |   2.806 |   0.564 |    3.208 |    4.497 |   11.9   |  8.167 |       3 |                  0.681 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |      15 | 958 |   2.328 |   0.577 |    2.711 |    3.988 |   17.189 | 11     |       3 |                  0.661 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |      20 | 958 |   1.875 |   0.577 |    2.441 |    3.867 |   19.763 | 13     |       3 |                  0.643 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      29 | 958 |   2.369 |   0.649 |    2.201 |    4.484 |   16.701 | 14.5   |       3 |                  0.663 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |      29 | 958 |   1.511 |   0.694 |    2.682 |    4.175 |   23.486 | 14.5   |       3 |                  0.628 |    nan     |    nan     |
| any-k CQL->PPO     | scene_ext   |      29 | 958 |   2.462 |   0.612 |    3.044 |    4.503 |   20.251 | 13.389 |       3 |                  0.667 |    nan     |    nan     |
| any-k CQL->PPO     | scene_trunc |       5 | 958 |   4.56  |   0.414 |    3.795 |    4.933 |    5.358 |  4.373 |       3 |                  0.754 |    nan     |    nan     |
| any-k CQL->PPO     | scene_trunc |      10 | 958 |   3.032 |   0.551 |    3.327 |    4.674 |   11.447 |  7.78  |       3 |                  0.69  |    nan     |    nan     |
| any-k CQL->PPO     | scene_trunc |      29 | 958 |   2.579 |   0.589 |    3.103 |    4.528 |   20.077 | 13.286 |       3 |                  0.672 |    nan     |    nan     |
| dedicated CQL->PPO | scene_ext   |       5 | 958 |   3.189 |   0.712 |    3.064 |    5.17  |   18.546 |  4.888 |       3 |                  0.697 |    nan     |    nan     |
| dedicated CQL->PPO | scene_ext   |      10 | 958 |   4.063 |   0.597 |    3.825 |    5.079 |    9.047 |  8.069 |       3 |                  0.733 |    nan     |    nan     |
| dedicated CQL->PPO | scene_ext   |      29 | 958 |   3.477 |   0.597 |    3.07  |    5.006 |   14.823 | 13.389 |       3 |                  0.709 |    nan     |    nan     |
| dedicated CQL->PPO | scene_trunc |       5 | 958 |   3.911 |   0.612 |    3.192 |    5.312 |   19.729 |  4.373 |       3 |                  0.727 |    nan     |    nan     |
| dedicated CQL->PPO | scene_trunc |      10 | 958 |   2.998 |   0.719 |    3.379 |    5.627 |   20.703 |  7.78  |       3 |                  0.689 |    nan     |    nan     |
| dedicated CQL->PPO | scene_trunc |      29 | 958 |   3.357 |   0.577 |    2.769 |    4.814 |   16.214 | 13.286 |       3 |                  0.704 |    nan     |    nan     |
| la_rule            | scene_trunc |       5 | 958 |  -2.686 | nan     |   -0.811 |    0.072 |  nan     |  4.373 |     nan |                nan     |      0.831 |     41.023 |
| la_rule            | scene_trunc |      10 | 958 |  -2.463 | nan     |   -1.101 |   -0.011 |  nan     |  7.78  |     nan |                nan     |      0.746 |     39.353 |
| la_rule            | scene_trunc |      29 | 958 |  -2.79  | nan     |   -1.085 |   -0.402 |  nan     | 13.286 |     nan |                nan     |      0.748 |     37.787 |
| la_rule            | scene_ext   |       5 | 958 |  -1.792 | nan     |   -0.705 |    0.458 |  nan     |  4.888 |     nan |                nan     |      0.681 |     37.787 |
| la_rule            | scene_ext   |      10 | 958 |  -1.869 | nan     |   -0.856 |    0.202 |  nan     |  8.069 |     nan |                nan     |      0.714 |     36.326 |
| la_rule            | scene_ext   |      29 | 958 |  -2.26  | nan     |   -0.932 |   -0.241 |  nan     | 13.389 |     nan |                nan     |      0.704 |     35.282 |
| la_rule            | cut_trig    |       5 | 958 |  -5.762 | nan     |   -2.707 |   -1.888 |  nan     |  0.204 |     nan |                nan     |      0.838 |     46.868 |
| la_rule            | cut_trig    |      10 | 958 |  -6.037 | nan     |   -2.913 |   -2.096 |  nan     |  0.647 |     nan |                nan     |      0.866 |     48.225 |
| la_rule            | cut_trig    |      29 | 958 |  -6.253 | nan     |   -2.892 |   -2.31  |  nan     |  2.014 |     nan |                nan     |      0.903 |     48.434 |
| scene_rule         | fixed       |       0 | 958 |  -6.542 | nan     |   -3.154 |   -1.952 |  nan     |  0     |     nan |                nan     |      0.954 |     65.449 |
| scene_rule         | fixed       |       1 | 958 |  -3.564 | nan     |   -1.205 |    0.55  |  nan     |  0.967 |     nan |                nan     |      0.922 |     64.614 |
| scene_rule         | fixed       |       2 | 958 |  -3.394 | nan     |   -1.317 |    0.362 |  nan     |  1.9   |     nan |                nan     |      0.903 |     62.735 |
| scene_rule         | fixed       |       3 | 958 |  -3.103 | nan     |   -1     |    0.443 |  nan     |  2.8   |     nan |                nan     |      0.861 |     58.768 |
| scene_rule         | fixed       |       5 | 958 |  -2.857 | nan     |   -1.234 |    0.299 |  nan     |  4.5   |     nan |                nan     |      0.832 |     60.23  |
| scene_rule         | fixed       |       7 | 958 |  -2.943 | nan     |   -1.083 |    0.052 |  nan     |  6.067 |     nan |                nan     |      0.83  |     58.038 |
| scene_rule         | fixed       |      10 | 958 |  -2.97  | nan     |   -1.307 |    0.044 |  nan     |  8.167 |     nan |                nan     |      0.786 |     57.62  |
| scene_rule         | fixed       |      15 | 958 |  -3.144 | nan     |   -1.199 |   -0.42  |  nan     | 11     |     nan |                nan     |      0.752 |     54.28  |
| scene_rule         | fixed       |      20 | 958 |  -3.285 | nan     |   -1.258 |   -0.599 |  nan     | 13     |     nan |                nan     |      0.768 |     54.697 |
| scene_rule         | fixed       |      29 | 958 |  -3.704 | nan     |   -1.275 |   -1.075 |  nan     | 14.5   |     nan |                nan     |      0.755 |     53.34  |
| scene_rule         | scene_trunc |       5 | 958 |  -3.344 | nan     |   -1.303 |    0.092 |  nan     |  4.373 |     nan |                nan     |      0.92  |     62.004 |
| scene_rule         | scene_trunc |      10 | 958 |  -3.419 | nan     |   -1.43  |   -0.106 |  nan     |  7.78  |     nan |                nan     |      0.879 |     60.438 |
| scene_rule         | scene_trunc |      29 | 958 |  -3.625 | nan     |   -1.388 |   -0.512 |  nan     | 13.286 |     nan |                nan     |      0.858 |     57.724 |
| scene_rule         | scene_ext   |       5 | 958 |  -2.212 | nan     |   -0.991 |    0.494 |  nan     |  4.888 |     nan |                nan     |      0.715 |     56.367 |
| scene_rule         | scene_ext   |      10 | 958 |  -2.553 | nan     |   -1.147 |    0.13  |  nan     |  8.069 |     nan |                nan     |      0.76  |     54.906 |
| scene_rule         | scene_ext   |      29 | 958 |  -2.646 | nan     |   -1.013 |   -0.173 |  nan     | 13.389 |     nan |                nan     |      0.672 |     53.236 |
| scene_rule         | cut_trig    |       5 | 958 |  -6.142 | nan     |   -3.007 |   -1.79  |  nan     |  0.204 |     nan |                nan     |      0.86  |     62.63  |
| scene_rule         | cut_trig    |      10 | 958 |  -6.019 | nan     |   -3.074 |   -1.738 |  nan     |  0.647 |     nan |                nan     |      0.885 |     62.735 |
| scene_rule         | cut_trig    |      29 | 958 |  -6.047 | nan     |   -2.918 |   -1.858 |  nan     |  2.014 |     nan |                nan     |      0.872 |     61.587 |

## Per-GOP lookahead gate

Gradient-boosted classifier on whole-GOP analysis features (cut count, cost variability, budget vs cost, motion, texture, budget level, fades/flashes) picks k from [0, 2, 5, 10, 29]; trained on validation outcomes, applied to test. The features need the GOP's pixel/first-pass analysis (not encodes).

| policy                         |   score |   mean k |
|:-------------------------------|--------:|---------:|
| fixed k=0                      |   0.737 |  nan     |
| fixed k=2                      |   3.808 |  nan     |
| fixed k=5                      |   3.482 |  nan     |
| fixed k=10                     |   3.178 |  nan     |
| fixed k=29                     |   2.369 |  nan     |
| per-GOP k gate (val-trained)   |   3.338 |    7.565 |
| oracle per-GOP k (upper bound) |   6.241 |  nan     |

## Cut specialist (cutspec)

| policy                          |   n |   score |    ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |
|:--------------------------------|----:|--------:|------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|
| general k=5                     | 958 |   3.482 | 0.601 |    2.657 |    5.112 |   20.181 |    4.5 |       3 |                  0.709 |
| general k=5, GOPs with cut      | 178 |   3.974 | 2.298 |    2.897 |    7.592 |   30.15  |    4.5 |       3 |                  0.619 |
| cut specialist, GOPs with cut   | 178 |   1.934 | 2.632 |    2.357 |    5.458 |   26.966 |    4.5 |       3 |                  0.549 |
| routed (specialist on cut GOPs) | 958 |   3.103 | 0.647 |    2.565 |    4.715 |   19.589 |    4.5 |       3 |                  0.693 |

## Switch (rule vs RL per GOP, k = 5)

RL 3.482, rule -2.512, oracle switch 4.362; RL better on 83.3% of GOPs.

