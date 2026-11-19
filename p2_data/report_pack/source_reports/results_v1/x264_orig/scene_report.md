# Scene intelligence and dynamic lookahead (x264)

## Lookahead modes

'seen' = mean future frames visible per decision (the cost of lookahead).

| policy             | mode        |   k cap |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |   score_ci |   over_pct |
|:-------------------|:------------|--------:|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|-----------:|-----------:|
| dedicated CQL->PPO | fixed       |       5 | 530 |   3.75  |   0.618 |    3.315 |    4.667 |   13.836 |  4.5   |       3 |                  0.696 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      10 | 530 |   3.253 |   0.678 |    3.03  |    4.549 |   17.862 |  8.167 |       3 |                  0.668 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      29 | 530 |   2.089 |   0.647 |    1.793 |    4.023 |   27.421 | 14.5   |       3 |                  0.601 |    nan     |    nan     |
| la_rule            | scene_trunc |       5 | 530 |  -0.971 | nan     |   -0.476 |    0.832 |  nan     |  4.434 |     nan |                nan     |      0.685 |     54.34  |
| la_rule            | scene_trunc |      10 | 530 |  -0.998 | nan     |   -0.447 |    0.494 |  nan     |  7.965 |     nan |                nan     |      0.653 |     54.151 |
| la_rule            | scene_trunc |      29 | 530 |  -1.231 | nan     |   -0.422 |   -0.015 |  nan     | 13.803 |     nan |                nan     |      0.598 |     50.943 |
| la_rule            | scene_ext   |       5 | 530 |  -0.777 | nan     |   -0.243 |    0.966 |  nan     |  4.846 |     nan |                nan     |      0.669 |     52.83  |
| la_rule            | scene_ext   |      10 | 530 |  -0.889 | nan     |   -0.371 |    0.658 |  nan     |  8.202 |     nan |                nan     |      0.657 |     52.642 |
| la_rule            | scene_ext   |      29 | 530 |  -1.023 | nan     |   -0.188 |    0.173 |  nan     | 13.87  |     nan |                nan     |      0.591 |     50.377 |
| la_rule            | cut_trig    |       5 | 530 |  -2.631 | nan     |   -1.501 |   -0.318 |  nan     |  0.106 |     nan |                nan     |      0.655 |     56.981 |
| la_rule            | cut_trig    |      10 | 530 |  -2.737 | nan     |   -1.506 |   -0.379 |  nan     |  0.36  |     nan |                nan     |      0.658 |     58.113 |
| la_rule            | cut_trig    |      29 | 530 |  -2.891 | nan     |   -1.502 |   -0.595 |  nan     |  1.307 |     nan |                nan     |      0.681 |     58.868 |
| scene_rule         | fixed       |       0 | 530 |  -3.353 | nan     |   -2.044 |   -0.644 |  nan     |  0     |     nan |                nan     |      0.663 |     65.472 |
| scene_rule         | fixed       |       1 | 530 |  -1.778 | nan     |   -1.17  |    0.794 |  nan     |  0.967 |     nan |                nan     |      0.721 |     63.208 |
| scene_rule         | fixed       |       2 | 530 |  -1.842 | nan     |   -0.972 |    0.752 |  nan     |  1.9   |     nan |                nan     |      0.736 |     63.774 |
| scene_rule         | fixed       |       3 | 530 |  -1.656 | nan     |   -0.883 |    0.729 |  nan     |  2.8   |     nan |                nan     |      0.73  |     58.679 |
| scene_rule         | fixed       |       5 | 530 |  -1.374 | nan     |   -0.86  |    0.762 |  nan     |  4.5   |     nan |                nan     |      0.677 |     58.868 |
| scene_rule         | fixed       |       7 | 530 |  -1.297 | nan     |   -0.859 |    0.592 |  nan     |  6.067 |     nan |                nan     |      0.661 |     61.132 |
| scene_rule         | fixed       |      10 | 530 |  -1.237 | nan     |   -1.053 |    0.42  |  nan     |  8.167 |     nan |                nan     |      0.66  |     55.472 |
| scene_rule         | fixed       |      15 | 530 |  -1.747 | nan     |   -1.009 |   -0.034 |  nan     | 11     |     nan |                nan     |      0.645 |     58.868 |
| scene_rule         | fixed       |      20 | 530 |  -1.799 | nan     |   -0.927 |   -0.195 |  nan     | 13     |     nan |                nan     |      0.636 |     61.132 |
| scene_rule         | fixed       |      29 | 530 |  -2.164 | nan     |   -0.88  |   -0.49  |  nan     | 14.5   |     nan |                nan     |      0.661 |     60.943 |
| scene_rule         | scene_trunc |       5 | 530 |  -1.729 | nan     |   -0.888 |    0.674 |  nan     |  4.434 |     nan |                nan     |      0.724 |     60.943 |
| scene_rule         | scene_trunc |      10 | 530 |  -1.505 | nan     |   -1.106 |    0.354 |  nan     |  7.965 |     nan |                nan     |      0.682 |     57.925 |
| scene_rule         | scene_trunc |      29 | 530 |  -2.357 | nan     |   -1.031 |   -0.397 |  nan     | 13.803 |     nan |                nan     |      0.679 |     63.962 |
| scene_rule         | scene_ext   |       5 | 530 |  -1.212 | nan     |   -0.62  |    0.828 |  nan     |  4.846 |     nan |                nan     |      0.672 |     56.981 |
| scene_rule         | scene_ext   |      10 | 530 |  -1.023 | nan     |   -0.762 |    0.575 |  nan     |  8.202 |     nan |                nan     |      0.653 |     54.151 |
| scene_rule         | scene_ext   |      29 | 530 |  -1.813 | nan     |   -0.767 |   -0.162 |  nan     | 13.87  |     nan |                nan     |      0.649 |     59.623 |
| scene_rule         | cut_trig    |       5 | 530 |  -3.114 | nan     |   -1.849 |   -0.528 |  nan     |  0.106 |     nan |                nan     |      0.651 |     64.528 |
| scene_rule         | cut_trig    |      10 | 530 |  -3.136 | nan     |   -1.889 |   -0.53  |  nan     |  0.36  |     nan |                nan     |      0.647 |     64.528 |
| scene_rule         | cut_trig    |      29 | 530 |  -3.179 | nan     |   -1.849 |   -0.641 |  nan     |  1.307 |     nan |                nan     |      0.663 |     63.774 |

## Per-GOP lookahead gate

Gradient-boosted classifier on whole-GOP analysis features (cut count, cost variability, budget vs cost, motion, texture, budget level, fades/flashes) picks k from [0, 2, 5, 10, 29]; trained on validation outcomes, applied to test. The features need the GOP's pixel/first-pass analysis (not encodes).

| policy                         |   score |   mean k |
|:-------------------------------|--------:|---------:|
| fixed k=0                      |  -0.17  |  nan     |
| fixed k=2                      |   3.285 |  nan     |
| fixed k=5                      |   3.75  |  nan     |
| fixed k=10                     |   3.253 |  nan     |
| fixed k=29                     |   2.089 |  nan     |
| per-GOP k gate (val-trained)   |   3.71  |    5.996 |
| oracle per-GOP k (upper bound) |   5.372 |  nan     |

## Switch (rule vs RL per GOP, k = 5)

RL 3.750, rule -0.912, oracle switch 4.324; RL better on 82.8% of GOPs.

