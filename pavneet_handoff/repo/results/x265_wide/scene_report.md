# Scene intelligence and dynamic lookahead (x265)

## Lookahead modes

'seen' = mean future frames visible per decision (the cost of lookahead).

| policy             | mode        |   k cap |    n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |   score_ci |   over_pct |
|:-------------------|:------------|--------:|-----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|-----------:|-----------:|
| dedicated CQL->PPO | fixed       |       5 | 2395 |   3.993 |   0.367 |    3.34  |    5.223 |   14.836 |  4.5   |       3 |                  0.738 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      10 | 2395 |   2.171 |   0.423 |    1.968 |    4.699 |   27.891 |  8.167 |       3 |                  0.661 |    nan     |    nan     |
| dedicated CQL->PPO | fixed       |      29 | 2395 |   2.66  |   0.416 |    2.122 |    4.492 |   19.123 | 14.5   |       3 |                  0.682 |    nan     |    nan     |
| la_rule            | scene_trunc |       5 | 2395 |  -2.854 | nan     |   -0.874 |    0.055 |  nan     |  4.373 |     nan |                nan     |      0.528 |     42.129 |
| la_rule            | scene_trunc |      10 | 2395 |  -2.651 | nan     |   -0.972 |   -0.045 |  nan     |  7.78  |     nan |                nan     |      0.48  |     40.376 |
| la_rule            | scene_trunc |      29 | 2395 |  -3.059 | nan     |   -0.94  |   -0.497 |  nan     | 13.286 |     nan |                nan     |      0.494 |     37.578 |
| la_rule            | scene_ext   |       5 | 2395 |  -2.172 | nan     |   -0.753 |    0.325 |  nan     |  4.888 |     nan |                nan     |      0.472 |     38.998 |
| la_rule            | scene_ext   |      10 | 2395 |  -2.062 | nan     |   -0.809 |    0.165 |  nan     |  8.069 |     nan |                nan     |      0.453 |     37.161 |
| la_rule            | scene_ext   |      29 | 2395 |  -2.414 | nan     |   -0.773 |   -0.232 |  nan     | 13.389 |     nan |                nan     |      0.457 |     34.614 |
| la_rule            | cut_trig    |       5 | 2395 |  -6.024 | nan     |   -2.682 |   -2.055 |  nan     |  0.204 |     nan |                nan     |      0.556 |     47.683 |
| la_rule            | cut_trig    |      10 | 2395 |  -6.237 | nan     |   -2.832 |   -2.224 |  nan     |  0.647 |     nan |                nan     |      0.567 |     48.518 |
| la_rule            | cut_trig    |      29 | 2395 |  -6.597 | nan     |   -2.801 |   -2.541 |  nan     |  2.014 |     nan |                nan     |      0.6   |     49.436 |
| scene_rule         | fixed       |       0 | 2395 |  -6.792 | nan     |   -3.173 |   -2.085 |  nan     |  0     |     nan |                nan     |      0.614 |     65.846 |
| scene_rule         | fixed       |       1 | 2395 |  -4.162 | nan     |   -1.542 |    0.301 |  nan     |  0.967 |     nan |                nan     |      0.603 |     65.136 |
| scene_rule         | fixed       |       2 | 2395 |  -3.835 | nan     |   -1.303 |    0.207 |  nan     |  1.9   |     nan |                nan     |      0.582 |     63.674 |
| scene_rule         | fixed       |       3 | 2395 |  -3.609 | nan     |   -1.256 |    0.23  |  nan     |  2.8   |     nan |                nan     |      0.567 |     60.292 |
| scene_rule         | fixed       |       5 | 2395 |  -3.348 | nan     |   -1.314 |    0.175 |  nan     |  4.5   |     nan |                nan     |      0.555 |     59.29  |
| scene_rule         | fixed       |       7 | 2395 |  -3.222 | nan     |   -1.129 |    0.076 |  nan     |  6.067 |     nan |                nan     |      0.534 |     58.038 |
| scene_rule         | fixed       |      10 | 2395 |  -3.244 | nan     |   -1.149 |   -0.038 |  nan     |  8.167 |     nan |                nan     |      0.522 |     57.62  |
| scene_rule         | fixed       |      15 | 2395 |  -3.434 | nan     |   -1.182 |   -0.427 |  nan     | 11     |     nan |                nan     |      0.505 |     55.324 |
| scene_rule         | fixed       |      20 | 2395 |  -3.704 | nan     |   -1.232 |   -0.706 |  nan     | 13     |     nan |                nan     |      0.524 |     55.825 |
| scene_rule         | fixed       |      29 | 2395 |  -4.004 | nan     |   -1.205 |   -1.113 |  nan     | 14.5   |     nan |                nan     |      0.511 |     54.823 |
| scene_rule         | scene_trunc |       5 | 2395 |  -3.661 | nan     |   -1.357 |    0.101 |  nan     |  4.373 |     nan |                nan     |      0.585 |     61.002 |
| scene_rule         | scene_trunc |      10 | 2395 |  -3.572 | nan     |   -1.378 |   -0.078 |  nan     |  7.78  |     nan |                nan     |      0.553 |     60.251 |
| scene_rule         | scene_trunc |      29 | 2395 |  -3.846 | nan     |   -1.407 |   -0.514 |  nan     | 13.286 |     nan |                nan     |      0.549 |     59.207 |
| scene_rule         | scene_ext   |       5 | 2395 |  -2.775 | nan     |   -1.096 |    0.338 |  nan     |  4.888 |     nan |                nan     |      0.498 |     56.242 |
| scene_rule         | scene_ext   |      10 | 2395 |  -2.733 | nan     |   -0.96  |    0.163 |  nan     |  8.069 |     nan |                nan     |      0.476 |     55.157 |
| scene_rule         | scene_ext   |      29 | 2395 |  -2.947 | nan     |   -1.007 |   -0.225 |  nan     | 13.389 |     nan |                nan     |      0.455 |     54.53  |
| scene_rule         | cut_trig    |       5 | 2395 |  -6.375 | nan     |   -3.056 |   -1.899 |  nan     |  0.204 |     nan |                nan     |      0.572 |     63.382 |
| scene_rule         | cut_trig    |      10 | 2395 |  -6.37  | nan     |   -3.113 |   -1.986 |  nan     |  0.647 |     nan |                nan     |      0.589 |     63.173 |
| scene_rule         | cut_trig    |      29 | 2395 |  -6.376 | nan     |   -3.006 |   -2.038 |  nan     |  2.014 |     nan |                nan     |      0.579 |     61.921 |

## Per-GOP lookahead gate

Gradient-boosted classifier on whole-GOP analysis features (cut count, cost variability, budget vs cost, motion, texture, budget level, fades/flashes) picks k from [0, 2, 5, 10, 29]; trained on validation outcomes, applied to test. The features need the GOP's pixel/first-pass analysis (not encodes).

| policy                         |   score |   mean k |
|:-------------------------------|--------:|---------:|
| fixed k=0                      |   2.88  |  nan     |
| fixed k=2                      |   2.67  |  nan     |
| fixed k=5                      |   3.993 |  nan     |
| fixed k=10                     |   2.171 |  nan     |
| fixed k=29                     |   2.66  |  nan     |
| per-GOP k gate (val-trained)   |   3.631 |    7.104 |
| oracle per-GOP k (upper bound) |   5.886 |  nan     |

## Switch (rule vs RL per GOP, k = 5)

RL 3.993, rule -2.803, oracle switch 4.649; RL better on 85.9% of GOPs.

