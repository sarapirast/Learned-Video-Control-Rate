# Scene intelligence and dynamic lookahead (x265)

## Lookahead modes

'seen' = mean future frames visible per decision (the cost of lookahead).

| policy             | mode        |   k cap |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |   score_ci |   over_pct |
|:-------------------|:------------|--------:|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|-----------:|-----------:|
| dedicated CQL->PPO | cut_trig    |       5 |  16 |  -9.894 |   9.411 |   -8.271 |    3.183 |    68.75 |  0.333 |       1 |                  0.048 |    nan     |     nan    |
| any-k CQL->PPO     | cut_trig    |       5 |  16 |  -7.42  |   8.657 |   -4.774 |    3.037 |    62.5  |  0.333 |       1 |                  0.204 |    nan     |     nan    |
| any-k CQL->PPO     | cut_trig    |      10 |  16 |  -7.635 |   8.72  |   -4.774 |    2.999 |    62.5  |  1.146 |       1 |                  0.191 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |       0 |  16 |  -7.844 |   8.601 |   -4.774 |    2.956 |    62.5  |  0     |       1 |                  0.177 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |       1 |  16 |  -7.218 |   8.817 |   -3.549 |    2.81  |    50    |  0.967 |       1 |                  0.217 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |       2 |  16 |  -9.12  |   9.36  |   -6.271 |    2.5   |    62.5  |  1.9   |       1 |                  0.097 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |       3 |  16 |  -9.213 |   9.255 |   -6.27  |    2.428 |    62.5  |  2.8   |       1 |                  0.091 |    nan     |     nan    |
| dedicated CQL->PPO | fixed       |       5 |  16 |  -8.223 |   9.171 |   -5.115 |    3.563 |    62.5  |  4.5   |       1 |                  0.153 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |       5 |  16 |  -7.013 |   8.3   |   -4.959 |    3.054 |    56.25 |  4.5   |       1 |                  0.23  |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |       7 |  16 |  -9.008 |   9.603 |   -6.27  |    3.295 |    62.5  |  6.067 |       1 |                  0.104 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |      10 |  16 |  -9.207 |   9.645 |   -6.27  |    3.251 |    62.5  |  8.167 |       1 |                  0.091 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |      15 |  16 |  -9.194 |   9.645 |   -6.27  |    3.265 |    62.5  | 11     |       1 |                  0.092 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |      20 |  16 |  -8.57  |   8.933 |   -6.27  |    3.099 |    62.5  | 13     |       1 |                  0.131 |    nan     |     nan    |
| any-k CQL->PPO     | fixed       |      29 |  16 |  -8.94  |   9.254 |   -8.717 |    3.079 |    62.5  | 14.5   |       1 |                  0.108 |    nan     |     nan    |
| any-k CQL->PPO     | scene_ext   |      29 |  16 |  -9.432 |   9.327 |   -9.072 |    3.155 |    62.5  | 12.758 |       1 |                  0.077 |    nan     |     nan    |
| any-k CQL->PPO     | scene_trunc |       5 |  16 |  -6.221 |   8.301 |   -3.091 |    2.959 |    50    |  4.304 |       1 |                  0.28  |    nan     |     nan    |
| any-k CQL->PPO     | scene_trunc |      10 |  16 |  -9.255 |   9.645 |   -6.27  |    3.204 |    62.5  |  7.558 |       1 |                  0.088 |    nan     |     nan    |
| any-k CQL->PPO     | scene_trunc |      29 |  16 |  -9.555 |   9.413 |   -9.124 |    3.184 |    56.25 | 12.521 |       1 |                  0.069 |    nan     |     nan    |
| dedicated CQL->PPO | scene_ext   |       5 |  16 |  -9.074 |   9.12  |   -5.115 |    3.405 |    68.75 |  5.946 |       1 |                  0.1   |    nan     |     nan    |
| dedicated CQL->PPO | scene_trunc |       5 |  16 | -10.51  |   9.906 |   -7.193 |    3.105 |    68.75 |  4.304 |       1 |                  0.009 |    nan     |     nan    |
| la_rule            | scene_trunc |       5 |  16 |  -0.899 | nan     |    0.769 |    1.617 |   nan    |  4.304 |     nan |                nan     |      3.283 |      75    |
| la_rule            | scene_ext   |       5 |  16 |   0.671 | nan     |    2.815 |    2.409 |   nan    |  5.946 |     nan |                nan     |      4.275 |      68.75 |
| la_rule            | cut_trig    |       5 |  16 |  -6.99  | nan     |   -3.103 |   -2.063 |   nan    |  0.333 |     nan |                nan     |      6.717 |      75    |
| scene_rule         | fixed       |       0 |  16 |  -9.11  | nan     |   -6.965 |   -3.993 |   nan    |  0     |     nan |                nan     |      6.257 |      81.25 |
| scene_rule         | fixed       |       5 |  16 |  -0.02  | nan     |    0.142 |    3.411 |   nan    |  4.5   |     nan |                nan     |      4.443 |      75    |
| scene_rule         | scene_trunc |       5 |  16 |  -2.718 | nan     |   -1.515 |    1.338 |   nan    |  4.304 |     nan |                nan     |      4.017 |      81.25 |
| scene_rule         | scene_ext   |       5 |  16 |   1.04  | nan     |    0.142 |    3.371 |   nan    |  5.946 |     nan |                nan     |      4.669 |      62.5  |
| scene_rule         | cut_trig    |       5 |  16 |  -7.811 | nan     |   -3.003 |   -2.557 |   nan    |  0.333 |     nan |                nan     |      6.941 |      68.75 |

## Cut specialist (cutspec)

| policy                          |   n |   score |     ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |
|:--------------------------------|----:|--------:|-------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|
| general k=5                     |  16 |  -8.223 |  9.171 |   -5.115 |    3.563 |   62.5   |    4.5 |       1 |                  0.153 |
| general k=5, GOPs with cut      |   6 |  -3.456 | 10.939 |   -3.853 |    3.882 |   50     |    4.5 |       1 |                  0.156 |
| cut specialist, GOPs with cut   |   6 |  -6.936 | 12.061 |   -8.559 |    2.806 |   83.333 |    4.5 |       1 |                 -0.139 |
| routed (specialist on cut GOPs) |  16 |  -9.528 |  9.213 |   -5.134 |    3.16  |   75     |    4.5 |       1 |                  0.071 |

## Switch (rule vs RL per GOP, k = 5)

RL -8.223, rule 0.714, oracle switch 2.902; RL better on 37.5% of GOPs.

