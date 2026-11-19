# Scene intelligence and dynamic lookahead (x265)

## Lookahead modes

'seen' = mean future frames visible per decision (the cost of lookahead).

| policy             | mode        |   k cap |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |   score_ci |   over_pct |
|:-------------------|:------------|--------:|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|-----------:|-----------:|
| dedicated CQL->PPO | fixed       |       5 | 530 |   4.526 |   0.637 |    3.694 |    5.563 |   15.283 |  4.5   |       3 |                  0.682 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      10 | 530 |   3.881 |   0.616 |    3.211 |    5.138 |   22.893 |  8.167 |       3 |                  0.642 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      29 | 530 |   3.819 |   0.682 |    3.505 |    5.143 |   15.849 | 14.5   |       3 |                  0.638 |    nan     |    nan     |
| la_rule            | scene_trunc |       5 | 530 |  -0.895 | nan     |   -0.727 |    0.517 |  nan     |  4.434 |     nan |                nan     |      0.619 |     36.792 |
| la_rule            | scene_trunc |      10 | 530 |  -1.045 | nan     |   -0.836 |    0.236 |  nan     |  7.965 |     nan |                nan     |      0.612 |     35.283 |
| la_rule            | scene_trunc |      29 | 530 |  -1.657 | nan     |   -0.878 |   -0.47  |  nan     | 13.803 |     nan |                nan     |      0.617 |     31.132 |
| la_rule            | scene_ext   |       5 | 530 |  -0.731 | nan     |   -0.561 |    0.573 |  nan     |  4.846 |     nan |                nan     |      0.602 |     34.717 |
| la_rule            | scene_ext   |      10 | 530 |  -0.789 | nan     |   -0.72  |    0.376 |  nan     |  8.202 |     nan |                nan     |      0.588 |     33.019 |
| la_rule            | scene_ext   |      29 | 530 |  -1.402 | nan     |   -0.682 |   -0.329 |  nan     | 13.87  |     nan |                nan     |      0.602 |     29.811 |
| la_rule            | cut_trig    |       5 | 530 |  -2.985 | nan     |   -1.854 |   -1.187 |  nan     |  0.106 |     nan |                nan     |      0.649 |     40.566 |
| la_rule            | cut_trig    |      10 | 530 |  -3.072 | nan     |   -1.864 |   -1.287 |  nan     |  0.36  |     nan |                nan     |      0.657 |     41.321 |
| la_rule            | cut_trig    |      29 | 530 |  -3.308 | nan     |   -1.871 |   -1.422 |  nan     |  1.307 |     nan |                nan     |      0.713 |     41.321 |
| scene_rule         | fixed       |       0 | 530 |  -3.604 | nan     |   -2.145 |   -1.061 |  nan     |  0     |     nan |                nan     |      0.711 |     62.453 |
| scene_rule         | fixed       |       1 | 530 |  -1.533 | nan     |   -0.937 |    0.896 |  nan     |  0.967 |     nan |                nan     |      0.755 |     62.264 |
| scene_rule         | fixed       |       2 | 530 |  -1.314 | nan     |   -0.914 |    0.936 |  nan     |  1.9   |     nan |                nan     |      0.714 |     61.509 |
| scene_rule         | fixed       |       3 | 530 |  -1.365 | nan     |   -0.85  |    0.77  |  nan     |  2.8   |     nan |                nan     |      0.706 |     58.302 |
| scene_rule         | fixed       |       5 | 530 |  -1.383 | nan     |   -0.807 |    0.626 |  nan     |  4.5   |     nan |                nan     |      0.661 |     59.434 |
| scene_rule         | fixed       |       7 | 530 |  -1.386 | nan     |   -0.831 |    0.503 |  nan     |  6.067 |     nan |                nan     |      0.646 |     56.226 |
| scene_rule         | fixed       |      10 | 530 |  -1.548 | nan     |   -0.891 |    0.242 |  nan     |  8.167 |     nan |                nan     |      0.663 |     56.604 |
| scene_rule         | fixed       |      15 | 530 |  -1.807 | nan     |   -1.043 |   -0.122 |  nan     | 11     |     nan |                nan     |      0.677 |     55.849 |
| scene_rule         | fixed       |      20 | 530 |  -2.152 | nan     |   -1.089 |   -0.479 |  nan     | 13     |     nan |                nan     |      0.699 |     58.679 |
| scene_rule         | fixed       |      29 | 530 |  -2.517 | nan     |   -1.147 |   -0.863 |  nan     | 14.5   |     nan |                nan     |      0.7   |     59.434 |
| scene_rule         | scene_trunc |       5 | 530 |  -1.562 | nan     |   -0.807 |    0.542 |  nan     |  4.434 |     nan |                nan     |      0.669 |     61.132 |
| scene_rule         | scene_trunc |      10 | 530 |  -1.768 | nan     |   -0.831 |    0.199 |  nan     |  7.965 |     nan |                nan     |      0.683 |     58.113 |
| scene_rule         | scene_trunc |      29 | 530 |  -2.568 | nan     |   -1.241 |   -0.671 |  nan     | 13.803 |     nan |                nan     |      0.687 |     61.698 |
| scene_rule         | scene_ext   |       5 | 530 |  -1.234 | nan     |   -0.677 |    0.668 |  nan     |  4.846 |     nan |                nan     |      0.648 |     56.981 |
| scene_rule         | scene_ext   |      10 | 530 |  -1.38  | nan     |   -0.725 |    0.361 |  nan     |  8.202 |     nan |                nan     |      0.65  |     54.528 |
| scene_rule         | scene_ext   |      29 | 530 |  -2.131 | nan     |   -0.998 |   -0.51  |  nan     | 13.87  |     nan |                nan     |      0.661 |     58.113 |
| scene_rule         | cut_trig    |       5 | 530 |  -3.509 | nan     |   -2.153 |   -0.989 |  nan     |  0.106 |     nan |                nan     |      0.706 |     62.075 |
| scene_rule         | cut_trig    |      10 | 530 |  -3.497 | nan     |   -2.117 |   -1.036 |  nan     |  0.36  |     nan |                nan     |      0.7   |     61.887 |
| scene_rule         | cut_trig    |      29 | 530 |  -3.538 | nan     |   -1.969 |   -1.115 |  nan     |  1.307 |     nan |                nan     |      0.733 |     61.509 |

## Per-GOP lookahead gate

Gradient-boosted classifier on whole-GOP analysis features (cut count, cost variability, budget vs cost, motion, texture, budget level, fades/flashes) picks k from [0, 2, 5, 10, 29]; trained on validation outcomes, applied to test. The features need the GOP's pixel/first-pass analysis (not encodes).

| policy                         |   score |   mean k |
|:-------------------------------|--------:|---------:|
| fixed k=0                      |   3.493 |   nan    |
| fixed k=2                      |   4.008 |   nan    |
| fixed k=5                      |   4.526 |   nan    |
| fixed k=10                     |   3.881 |   nan    |
| fixed k=29                     |   3.819 |   nan    |
| per-GOP k gate (val-trained)   |   4.215 |     9.37 |
| oracle per-GOP k (upper bound) |   6.351 |   nan    |

## Switch (rule vs RL per GOP, k = 5)

RL 4.526, rule -0.908, oracle switch 4.867; RL better on 89.4% of GOPs.

