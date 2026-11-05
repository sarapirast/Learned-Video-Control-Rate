# Scene intelligence and dynamic lookahead (x264)

## Lookahead modes

'seen' = mean future frames visible per decision (the cost of lookahead).

| policy             | mode        |   k cap |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |   score_ci |   over_pct |
|:-------------------|:------------|--------:|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|-----------:|-----------:|
| dedicated CQL->PPO | cut_trig    |       5 | 958 |   1.67  |   0.622 |    2.312 |    3.995 |   21.329 |  0.202 |       3 |                  0.68  |    nan     |    nan     |
| dedicated CQL->PPO | cut_trig    |      10 | 958 |   2.034 |   0.642 |    2.744 |    4.025 |   17.258 |  0.645 |       3 |                  0.694 |    nan     |    nan     |
| dedicated CQL->PPO | cut_trig    |      29 | 958 |   2.726 |   0.635 |    3.056 |    4.338 |   17.015 |  2.007 |       3 |                  0.721 |    nan     |    nan     |
| any-k CQL->PPO     | cut_trig    |       5 | 958 |   0.43  |   0.778 |    1.582 |    1.246 |    3.305 |  0.202 |       3 |                  0.632 |    nan     |    nan     |
| any-k CQL->PPO     | cut_trig    |      10 | 958 |   0.368 |   0.813 |    1.57  |    1.2   |    3.445 |  0.645 |       3 |                  0.63  |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       0 | 958 |   0.399 |   0.773 |    1.549 |    1.209 |    3.201 |  0     |       3 |                  0.631 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       1 | 958 |   1.984 |   0.667 |    2.261 |    2.521 |    3.027 |  0.967 |       3 |                  0.692 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       2 | 958 |   3.14  |   0.57  |    2.904 |    3.418 |    2.958 |  1.9   |       3 |                  0.737 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       3 | 958 |   3.79  |   0.55  |    3.442 |    4.128 |    4.454 |  2.8   |       3 |                  0.762 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |       5 | 958 |   0.426 |   0.786 |    1.763 |    4.453 |   29.819 |  4.5   |       3 |                  0.632 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       5 | 958 |   3.8   |   0.488 |    3.572 |    4.424 |    6.576 |  4.5   |       3 |                  0.763 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |       7 | 958 |   3.998 |   0.486 |    3.796 |    4.477 |    5.776 |  6.067 |       3 |                  0.77  |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      10 | 958 |   2.903 |   0.626 |    2.764 |    4.598 |   19.589 |  8.167 |       3 |                  0.728 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |      10 | 958 |   3.355 |   0.524 |    3.61  |    4.587 |    8.594 |  8.167 |       3 |                  0.745 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |      15 | 958 |   0.268 |   0.737 |    2.03  |    4.296 |   20.981 | 11     |       3 |                  0.626 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |      20 | 958 |   1.825 |   0.601 |    2.54  |    4.256 |   20.981 | 13     |       3 |                  0.686 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      29 | 958 |   2.233 |   0.67  |    2.586 |    4.495 |   20.424 | 14.5   |       3 |                  0.702 |    nan     |    nan     |
| any-k CQL->PPO     | fixed       |      29 | 958 |   3.196 |   0.614 |    3.708 |    4.692 |   11.552 | 14.5   |       3 |                  0.739 |    nan     |    nan     |
| any-k CQL->PPO     | scene_ext   |      29 | 958 |   3.462 |   0.593 |    3.872 |    4.644 |    9.673 | 13.395 |       3 |                  0.75  |    nan     |    nan     |
| any-k CQL->PPO     | scene_trunc |       5 | 958 |   3.917 |   0.465 |    3.634 |    4.54  |    6.437 |  4.374 |       3 |                  0.767 |    nan     |    nan     |
| any-k CQL->PPO     | scene_trunc |      10 | 958 |   3.478 |   0.507 |    3.72  |    4.675 |    8.142 |  7.782 |       3 |                  0.75  |    nan     |    nan     |
| any-k CQL->PPO     | scene_trunc |      29 | 958 |   3.68  |   0.562 |    3.93  |    4.739 |    9.151 | 13.292 |       3 |                  0.758 |    nan     |    nan     |
| dedicated CQL->PPO | scene_ext   |       5 | 958 |   2.57  |   0.696 |    2.974 |    4.932 |   20.459 |  4.889 |       3 |                  0.715 |    nan     |    nan     |
| dedicated CQL->PPO | scene_ext   |      10 | 958 |   2.845 |   0.615 |    2.742 |    4.89  |   20.251 |  8.071 |       3 |                  0.726 |    nan     |    nan     |
| dedicated CQL->PPO | scene_ext   |      29 | 958 |   0.937 |   0.717 |    1.742 |    4.483 |   28.845 | 13.395 |       3 |                  0.652 |    nan     |    nan     |
| dedicated CQL->PPO | scene_trunc |       5 | 958 |   3.066 |   0.592 |    2.981 |    4.665 |   18.998 |  4.374 |       3 |                  0.734 |    nan     |    nan     |
| dedicated CQL->PPO | scene_trunc |      10 | 958 |   3.557 |   0.57  |    3.221 |    5.345 |   22.791 |  7.782 |       3 |                  0.753 |    nan     |    nan     |
| dedicated CQL->PPO | scene_trunc |      29 | 958 |   1.592 |   0.693 |    1.931 |    4.061 |   23.312 | 13.292 |       3 |                  0.677 |    nan     |    nan     |
| la_rule            | scene_trunc |       5 | 958 |  -2.201 | nan     |   -0.613 |    0.291 |  nan     |  4.374 |     nan |                nan     |      0.842 |     36.952 |
| la_rule            | scene_trunc |      10 | 958 |  -2.171 | nan     |   -0.624 |    0.235 |  nan     |  7.782 |     nan |                nan     |      0.808 |     36.848 |
| la_rule            | scene_trunc |      29 | 958 |  -2.446 | nan     |   -0.705 |   -0.118 |  nan     | 13.292 |     nan |                nan     |      0.798 |     34.342 |
| la_rule            | scene_ext   |       5 | 958 |  -1.626 | nan     |   -0.368 |    0.336 |  nan     |  4.889 |     nan |                nan     |      0.752 |     33.507 |
| la_rule            | scene_ext   |      10 | 958 |  -1.515 | nan     |   -0.52  |    0.379 |  nan     |  8.071 |     nan |                nan     |      0.695 |     33.403 |
| la_rule            | scene_ext   |      29 | 958 |  -1.773 | nan     |   -0.554 |    0.097 |  nan     | 13.395 |     nan |                nan     |      0.687 |     31.315 |
| la_rule            | cut_trig    |       5 | 958 |  -5.064 | nan     |   -2.175 |   -1.535 |  nan     |  0.202 |     nan |                nan     |      0.849 |     47.599 |
| la_rule            | cut_trig    |      10 | 958 |  -5.299 | nan     |   -2.19  |   -1.757 |  nan     |  0.645 |     nan |                nan     |      0.905 |     47.912 |
| la_rule            | cut_trig    |      29 | 958 |  -5.638 | nan     |   -2.131 |   -2.051 |  nan     |  2.007 |     nan |                nan     |      0.92  |     48.747 |
| scene_rule         | fixed       |       0 | 958 |  -5.833 | nan     |   -2.689 |   -1.355 |  nan     |  0     |     nan |                nan     |      0.919 |     63.987 |
| scene_rule         | fixed       |       1 | 958 |  -3.402 | nan     |   -1.167 |    0.679 |  nan     |  0.967 |     nan |                nan     |      0.927 |     64.092 |
| scene_rule         | fixed       |       2 | 958 |  -3.106 | nan     |   -1.042 |    0.457 |  nan     |  1.9   |     nan |                nan     |      0.891 |     59.29  |
| scene_rule         | fixed       |       3 | 958 |  -2.634 | nan     |   -0.782 |    0.654 |  nan     |  2.8   |     nan |                nan     |      0.841 |     57.62  |
| scene_rule         | fixed       |       5 | 958 |  -2.395 | nan     |   -0.81  |    0.521 |  nan     |  4.5   |     nan |                nan     |      0.825 |     57.62  |
| scene_rule         | fixed       |       7 | 958 |  -2.149 | nan     |   -0.838 |    0.53  |  nan     |  6.067 |     nan |                nan     |      0.802 |     56.263 |
| scene_rule         | fixed       |      10 | 958 |  -2.413 | nan     |   -0.791 |    0.391 |  nan     |  8.167 |     nan |                nan     |      0.821 |     55.95  |
| scene_rule         | fixed       |      15 | 958 |  -2.455 | nan     |   -0.825 |    0.057 |  nan     | 11     |     nan |                nan     |      0.767 |     53.758 |
| scene_rule         | fixed       |      20 | 958 |  -2.729 | nan     |   -0.858 |   -0.245 |  nan     | 13     |     nan |                nan     |      0.762 |     52.401 |
| scene_rule         | fixed       |      29 | 958 |  -3.173 | nan     |   -0.9   |   -0.616 |  nan     | 14.5   |     nan |                nan     |      0.742 |     53.027 |
| scene_rule         | scene_trunc |       5 | 958 |  -2.751 | nan     |   -0.988 |    0.445 |  nan     |  4.374 |     nan |                nan     |      0.837 |     58.768 |
| scene_rule         | scene_trunc |      10 | 958 |  -2.878 | nan     |   -1.017 |    0.312 |  nan     |  7.782 |     nan |                nan     |      0.833 |     57.933 |
| scene_rule         | scene_trunc |      29 | 958 |  -3.216 | nan     |   -1.128 |   -0.108 |  nan     | 13.292 |     nan |                nan     |      0.801 |     56.785 |
| scene_rule         | scene_ext   |       5 | 958 |  -1.667 | nan     |   -0.541 |    0.768 |  nan     |  4.889 |     nan |                nan     |      0.713 |     53.967 |
| scene_rule         | scene_ext   |      10 | 958 |  -1.761 | nan     |   -0.589 |    0.634 |  nan     |  8.071 |     nan |                nan     |      0.711 |     53.132 |
| scene_rule         | scene_ext   |      29 | 958 |  -2.082 | nan     |   -0.708 |    0.248 |  nan     | 13.395 |     nan |                nan     |      0.669 |     52.192 |
| scene_rule         | cut_trig    |       5 | 958 |  -5.507 | nan     |   -2.602 |   -1.338 |  nan     |  0.202 |     nan |                nan     |      0.88  |     62.63  |
| scene_rule         | cut_trig    |      10 | 958 |  -5.653 | nan     |   -2.56  |   -1.518 |  nan     |  0.645 |     nan |                nan     |      0.914 |     61.587 |
| scene_rule         | cut_trig    |      29 | 958 |  -5.718 | nan     |   -2.551 |   -1.67  |  nan     |  2.007 |     nan |                nan     |      0.884 |     61.169 |

## Per-GOP lookahead gate

Gradient-boosted classifier on whole-GOP analysis features (cut count, cost variability, budget vs cost, motion, texture, budget level, fades/flashes) picks k from [0, 2, 5, 10, 29]; trained on validation outcomes, applied to test. The features need the GOP's pixel/first-pass analysis (not encodes).

| policy                         |   score |   mean k |
|:-------------------------------|--------:|---------:|
| fixed k=0                      |  -1.171 |  nan     |
| fixed k=2                      |   1.74  |  nan     |
| fixed k=5                      |   0.426 |  nan     |
| fixed k=10                     |   2.903 |  nan     |
| fixed k=29                     |   2.233 |  nan     |
| per-GOP k gate (val-trained)   |   2.799 |    9.601 |
| oracle per-GOP k (upper bound) |   5.392 |  nan     |

## Cut specialist (cutspec)

| policy                          |   n |   score |    ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |
|:--------------------------------|----:|--------:|------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|
| general k=5                     | 958 |   0.426 | 0.786 |    1.763 |    4.453 |   29.819 |    4.5 |       3 |                  0.632 |
| general k=5, GOPs with cut      | 176 |   0.456 | 2.629 |   -0.451 |    7.913 |   39.583 |    4.5 |       3 |                  0.534 |
| cut specialist, GOPs with cut   | 176 |   0.639 | 2.558 |    1.845 |    5.588 |   27.652 |    4.5 |       3 |                  0.54  |
| routed (specialist on cut GOPs) | 958 |   0.459 | 0.778 |    1.976 |    4.026 |   27.627 |    4.5 |       3 |                  0.634 |

## Switch (rule vs RL per GOP, k = 5)

RL 0.426, rule -1.945, oracle switch 2.901; RL better on 71.9% of GOPs.

