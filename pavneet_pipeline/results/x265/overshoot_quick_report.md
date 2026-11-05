# Overshoot (x265, CQL->PPO, test)

By k and budget:

|         |   over |   mean_over_pct |   p95_over_pct |
|:--------|-------:|----------------:|---------------:|
| (5, 30) |   0.5  |           5.187 |         18.14  |
| (5, 38) |   0.75 |           6.6   |         19.147 |

By family:

| family    |   over |   score |
|:----------|-------:|--------:|
| film_long |  0.25  |   5.317 |
| splice    |  0.5   | -10.98  |
| ugc       |  0.875 | -13.615 |

GOPs with/without a detected cut:

| has_cut   |   over |   score |
|:----------|-------:|--------:|
| False     |    0.7 | -11.083 |
| True      |    0.5 |  -3.456 |
