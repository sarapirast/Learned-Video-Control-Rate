# RL approaches (x265)

All trained on the same data / env steps; test split; seed-averaged per GOP and budget.

|   k | method   |   n |   score |    ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |
|----:|:---------|----:|--------:|------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|
|   0 | bc       | 530 |  -1.258 | 1.194 |    0.328 |    2.948 |   28.113 |  0     |       3 |                  0.53  |
|   0 | lagr     | 530 |   3.452 | 0.539 |    3.4   |    4.104 |    6.667 |  0     |       3 |                  0.746 |
|  10 | bc       | 530 |   1.844 | 0.895 |    1.864 |    4.276 |   20.44  |  8.167 |       3 |                  0.672 |
|  10 | lagr     | 530 |   3.265 | 0.654 |    3.289 |    4.302 |    7.799 |  8.167 |       3 |                  0.737 |
