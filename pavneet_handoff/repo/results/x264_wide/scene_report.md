# Scene intelligence and dynamic lookahead (x264)

## Lookahead modes

'seen' = mean future frames visible per decision (the cost of lookahead).

| policy             | mode        |   k cap |    n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |   score_ci |   over_pct |
|:-------------------|:------------|--------:|-----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|-----------:|-----------:|
| dedicated CQL->PPO | fixed       |       5 | 2395 |   2.787 |   0.431 |    3.023 |    4.394 |   17.411 |  4.5   |       3 |                  0.727 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      10 | 2395 |   3.464 |   0.373 |    3.198 |    4.884 |   17.481 |  8.167 |       3 |                  0.753 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      29 | 2395 |  -0.42  |   0.448 |    0.252 |    3.748 |   35.63  | 14.5   |       3 |                  0.602 |    nan     |    nan     |
| la_rule            | scene_trunc |       5 | 2395 |  -2.677 | nan     |   -0.9   |   -0.058 |  nan     |  4.374 |     nan |                nan     |      0.563 |     37.662 |
| la_rule            | scene_trunc |      10 | 2395 |  -2.705 | nan     |   -0.819 |   -0.203 |  nan     |  7.782 |     nan |                nan     |      0.551 |     35.908 |
| la_rule            | scene_trunc |      29 | 2395 |  -2.897 | nan     |   -0.895 |   -0.517 |  nan     | 13.292 |     nan |                nan     |      0.537 |     33.528 |
| la_rule            | scene_ext   |       5 | 2395 |  -1.881 | nan     |   -0.616 |    0.202 |  nan     |  4.889 |     nan |                nan     |      0.477 |     34.071 |
| la_rule            | scene_ext   |      10 | 2395 |  -1.83  | nan     |   -0.552 |    0.158 |  nan     |  8.071 |     nan |                nan     |      0.458 |     32.61  |
| la_rule            | scene_ext   |      29 | 2395 |  -1.992 | nan     |   -0.643 |   -0.087 |  nan     | 13.395 |     nan |                nan     |      0.438 |     30.397 |
| la_rule            | cut_trig    |       5 | 2395 |  -5.201 | nan     |   -2.232 |   -1.663 |  nan     |  0.202 |     nan |                nan     |      0.579 |     45.386 |
| la_rule            | cut_trig    |      10 | 2395 |  -5.359 | nan     |   -2.211 |   -1.796 |  nan     |  0.645 |     nan |                nan     |      0.605 |     45.762 |
| la_rule            | cut_trig    |      29 | 2395 |  -5.573 | nan     |   -2.19  |   -2.026 |  nan     |  2.007 |     nan |                nan     |      0.582 |     46.555 |
| scene_rule         | fixed       |       0 | 2395 |  -6.035 | nan     |   -2.941 |   -1.582 |  nan     |  0     |     nan |                nan     |      0.606 |     65.177 |
| scene_rule         | fixed       |       1 | 2395 |  -3.971 | nan     |   -1.496 |    0.329 |  nan     |  0.967 |     nan |                nan     |      0.629 |     63.716 |
| scene_rule         | fixed       |       2 | 2395 |  -3.755 | nan     |   -1.318 |    0.129 |  nan     |  1.9   |     nan |                nan     |      0.614 |     59.916 |
| scene_rule         | fixed       |       3 | 2395 |  -3.275 | nan     |   -1.164 |    0.304 |  nan     |  2.8   |     nan |                nan     |      0.591 |     58.58  |
| scene_rule         | fixed       |       5 | 2395 |  -3.068 | nan     |   -1.102 |    0.144 |  nan     |  4.5   |     nan |                nan     |      0.571 |     57.035 |
| scene_rule         | fixed       |       7 | 2395 |  -2.874 | nan     |   -1.078 |    0.138 |  nan     |  6.067 |     nan |                nan     |      0.565 |     57.495 |
| scene_rule         | fixed       |      10 | 2395 |  -3.147 | nan     |   -1.019 |   -0.089 |  nan     |  8.167 |     nan |                nan     |      0.574 |     56.743 |
| scene_rule         | fixed       |      15 | 2395 |  -3.08  | nan     |   -1.041 |   -0.36  |  nan     | 11     |     nan |                nan     |      0.513 |     54.739 |
| scene_rule         | fixed       |      20 | 2395 |  -3.296 | nan     |   -1.076 |   -0.556 |  nan     | 13     |     nan |                nan     |      0.511 |     53.946 |
| scene_rule         | fixed       |      29 | 2395 |  -3.532 | nan     |   -1.036 |   -0.802 |  nan     | 14.5   |     nan |                nan     |      0.504 |     53.904 |
| scene_rule         | scene_trunc |       5 | 2395 |  -3.398 | nan     |   -1.237 |    0.083 |  nan     |  4.374 |     nan |                nan     |      0.583 |     58.163 |
| scene_rule         | scene_trunc |      10 | 2395 |  -3.563 | nan     |   -1.271 |   -0.132 |  nan     |  7.782 |     nan |                nan     |      0.582 |     58.789 |
| scene_rule         | scene_trunc |      29 | 2395 |  -3.831 | nan     |   -1.356 |   -0.519 |  nan     | 13.292 |     nan |                nan     |      0.57  |     57.411 |
| scene_rule         | scene_ext   |       5 | 2395 |  -2.221 | nan     |   -0.701 |    0.456 |  nan     |  4.889 |     nan |                nan     |      0.484 |     53.152 |
| scene_rule         | scene_ext   |      10 | 2395 |  -2.337 | nan     |   -0.769 |    0.266 |  nan     |  8.071 |     nan |                nan     |      0.481 |     53.737 |
| scene_rule         | scene_ext   |      29 | 2395 |  -2.564 | nan     |   -0.821 |   -0.072 |  nan     | 13.395 |     nan |                nan     |      0.465 |     52.568 |
| scene_rule         | cut_trig    |       5 | 2395 |  -5.649 | nan     |   -2.781 |   -1.482 |  nan     |  0.202 |     nan |                nan     |      0.58  |     63.257 |
| scene_rule         | cut_trig    |      10 | 2395 |  -5.791 | nan     |   -2.763 |   -1.641 |  nan     |  0.645 |     nan |                nan     |      0.601 |     62.63  |
| scene_rule         | cut_trig    |      29 | 2395 |  -5.636 | nan     |   -2.648 |   -1.602 |  nan     |  2.007 |     nan |                nan     |      0.555 |     62.004 |

## Per-GOP lookahead gate

Gradient-boosted classifier on whole-GOP analysis features (cut count, cost variability, budget vs cost, motion, texture, budget level, fades/flashes) picks k from [0, 2, 5, 10, 29]; trained on validation outcomes, applied to test. The features need the GOP's pixel/first-pass analysis (not encodes).

| policy                         |   score |   mean k |
|:-------------------------------|--------:|---------:|
| fixed k=0                      |   1.822 |  nan     |
| fixed k=2                      |   2.717 |  nan     |
| fixed k=5                      |   2.787 |  nan     |
| fixed k=10                     |   3.464 |  nan     |
| fixed k=29                     |  -0.42  |  nan     |
| per-GOP k gate (val-trained)   |   3.548 |    7.199 |
| oracle per-GOP k (upper bound) |   5.692 |  nan     |

## Switch (rule vs RL per GOP, k = 5)

RL 2.787, rule -2.477, oracle switch 3.924; RL better on 79.7% of GOPs.

