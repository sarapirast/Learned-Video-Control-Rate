# Lookahead curve (x265)

Penalised score = % bits saved at equal PSNR vs own constant QP − 2 × % over budget. 'share of search gain' = (policy − STATIC) / (hindsight search − STATIC), summed over test items. 'vs prev k' = paired difference to the previous k in the list (95 % CI).

| policy         |   k | split   |   n |   score |      ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |   score_ci |   over_pct |
|:---------------|----:|:--------|----:|--------:|--------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|-----------:|-----------:|
| CQL->PPO       |   5 | val     |  16 | -15.309 |   8.18  |  -19.675 |    0.835 |    56.25 |    4.5 |       1 |                nan     |    nan     |     nan    |
| CQL->PPO       |   5 | test    |  16 |  -8.223 |   9.171 |   -5.115 |    3.563 |    62.5  |    4.5 |       1 |                  0.153 |    nan     |     nan    |
| lookahead rule |   0 | test    |  16 |  -6.981 | nan     |   -5.269 |   -2.675 |   nan    |    0   |     nan |                nan     |      5.679 |      81.25 |
| lookahead rule |   5 | test    |  16 |   0.714 | nan     |    2.815 |    2.761 |   nan    |    4.5 |     nan |                nan     |      3.233 |      68.75 |
