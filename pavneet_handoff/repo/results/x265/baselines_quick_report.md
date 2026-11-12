# Baselines (x265)

Rules chosen on validation: {'rule': {'gain': 2}, 'la_rule': {'gain': 0.5, 'sens': 5.0}, 'scene_rule': {'cut_boost': 1.0, 'gain': 0.75, 'sens': 5.0}}

| method                     |   n |   score |     ci |   saving |   over % |   encoder failed |   frames seen |
|:---------------------------|----:|--------:|-------:|---------:|---------:|-----------------:|--------------:|
| STATIC @QP30               |   8 |  -7.498 | 13.095 |    3.084 |    50    |              nan |       nan     |
| STATIC @QP38               |   8 | -13.791 | 15.398 |    3.093 |    87.5  |              nan |       nan     |
| own abr @QP30              |   8 | -36.688 | 16.275 |  -33.979 |    37.5  |                0 |       nan     |
| own abr +AQ @QP30          |   8 |  -7.16  |  7.095 |   -7.16  |     0    |                0 |       nan     |
| own 2pass @QP30            |   8 | -18.597 |  8.57  |  -15.486 |    37.5  |                0 |       nan     |
| own 2pass +AQ @QP30        |   8 |  -6.024 | 10.496 |    0.419 |    50    |                0 |       nan     |
| own abr_vbv @QP30          |   8 | -41.032 | 16.357 |  -25.581 |    87.5  |                0 |       nan     |
| own abr_vbv +AQ @QP30      |   8 | -28.84  | 22.467 |  -28.432 |    25    |                0 |       nan     |
| own abr @QP38              |   8 | -31.477 | 21.479 |  -13.158 |    87.5  |                0 |       nan     |
| own abr +AQ @QP38          |   8 | -32.114 | 35.087 |  -10.804 |    37.5  |                0 |       nan     |
| own 2pass @QP38            |   8 | -26.263 | 14.831 |  -11.224 |    75    |                0 |       nan     |
| own 2pass +AQ @QP38        |   8 | -36.954 | 23.617 |    2.748 |   100    |                0 |       nan     |
| own abr_vbv @QP38          |   8 | -58.633 | 20.439 |  -37.574 |   100    |                0 |       nan     |
| own abr_vbv +AQ @QP38      |   8 | -36.987 | 23.557 |  -32.809 |    75    |                0 |       nan     |
| rule k=0 fixed             |  16 |  -3.696 |  7.24  |    4.134 |    68.75 |              nan |         0     |
| la_rule k=0 fixed          |  16 |  -6.981 |  5.679 |   -2.675 |    81.25 |              nan |         0     |
| la_rule k=5 fixed          |  16 |   0.714 |  3.233 |    2.761 |    68.75 |              nan |         4.5   |
| la_rule k=5 scene_trunc    |  16 |  -0.899 |  3.283 |    1.617 |    75    |              nan |         4.304 |
| la_rule k=5 scene_ext      |  16 |   0.671 |  4.275 |    2.409 |    68.75 |              nan |         5.946 |
| la_rule k=5 cut_trig       |  16 |  -6.99  |  6.717 |   -2.063 |    75    |              nan |         0.333 |
| scene_rule k=0 fixed       |  16 |  -9.11  |  6.257 |   -3.993 |    81.25 |              nan |         0     |
| scene_rule k=5 fixed       |  16 |  -0.02  |  4.443 |    3.411 |    75    |              nan |         4.5   |
| scene_rule k=5 scene_trunc |  16 |  -2.718 |  4.017 |    1.338 |    81.25 |              nan |         4.304 |
| scene_rule k=5 scene_ext   |  16 |   1.04  |  4.669 |    3.371 |    62.5  |              nan |         5.946 |
| scene_rule k=5 cut_trig    |  16 |  -7.811 |  6.941 |   -2.557 |    68.75 |              nan |         0.333 |

Fixed-pattern refit on train (mean penalised score over both budgets):

| rank | (I, early, late, split) | score |
|---|---|---|
| 1 | (-6, -3, 3, 10) | -22.405 |
| 2 | (-9, -4, 1, 5) | -29.944 |
| 3 | (-9, -4, 0, 5) | -49.335 |
| 4 | (-9, -4, 0, 10) | -82.843 |
| 5 | (-9, -4, 0, 15) | -109.465 |
| used | (-6, -3, 3, 10) | -22.405 |

Average STATIC cumulative spend share at frames 1, 5, 10, 20: 0.238, 0.390, 0.624, 0.814
