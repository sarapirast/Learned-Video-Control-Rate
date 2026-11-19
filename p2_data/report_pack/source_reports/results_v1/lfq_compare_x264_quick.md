# Learned rate control on the quality-at-budget metric, x264 (scripts/lfq_compare.py)

Score = dPSNR_B - 0.17 dB per 1% over (dB; 0 = a constant QP spending exactly the budget). Leak-free budgets (4 levels), P1 settings, flat GOPs excluded. bc / cql_ppo / lagr: causal base QP (budgets.csv base_qp_est_k) + ramp + learned offset (+-10); res: residual offset (-3..+3) on the causal controller. ctrl = controller run '-' ; search = lfq hindsight search best plan (ceiling); start = the search's start plan (ramp at the HINDSIGHT base q, not causal). Seeds pooled; CI = 95% bootstrap over clips. gap_closed_% = mean(method - ctrl) / mean(search - ctrl).

## test: method x k

| method       |   k |   n |   seeds |   score |   dpsnr_b |   use |   over_% |   seed_means |   search |   start |   ctrl | vs_search               |
|:-------------|----:|----:|--------:|--------:|----------:|------:|---------:|-------------:|---------:|--------:|-------:|:------------------------|
| bc           |   0 |   8 |       1 | -27.973 |     2.743 | 2.639 |     62.5 |       -27.97 |    0.254 |  -0.651 |    nan | -28.23 [-28.23, -28.23] |
| lagr         |   5 |   8 |       1 |  -5.692 |    -0.152 | 1.187 |     62.5 |        -5.69 |    0.254 |  -0.651 |    nan | -5.95 [-5.95, -5.95]    |
| lagr_lam0.17 |   0 |   8 |       1 |  -9.513 |    -0.396 | 1.336 |     50   |        -9.51 |    0.254 |  -0.651 |    nan | -9.77 [-9.77, -9.77]    |

## test: score by GOP class

| method       |   k |   stable_n |   stable |   stable_ctrl |   stable_search |   cut_n |   cut |   cut_ctrl |   cut_search |   gradual_n |   gradual |   gradual_ctrl |   gradual_search |
|:-------------|----:|-----------:|---------:|--------------:|----------------:|--------:|------:|-----------:|-------------:|------------:|----------:|---------------:|-----------------:|
| bc           |   0 |          8 |  -27.973 |           nan |           0.254 |       0 |   nan |        nan |          nan |           0 |       nan |            nan |              nan |
| lagr         |   5 |          8 |   -5.692 |           nan |           0.254 |       0 |   nan |        nan |          nan |           0 |       nan |            nan |              nan |
| lagr_lam0.17 |   0 |          8 |   -9.513 |           nan |           0.254 |       0 |   nan |        nan |          nan |           0 |       nan |            nan |              nan |

## val: method x k

| method       |   k |   n |   seeds |   score |   dpsnr_b |   use |   over_% |   seed_means |   search |   start |   ctrl | vs_search               |
|:-------------|----:|----:|--------:|--------:|----------:|------:|---------:|-------------:|---------:|--------:|-------:|:------------------------|
| bc           |   0 |   8 |       1 | -26.787 |     3.781 | 2.798 |    100   |       -26.79 |    0.238 |  -0.038 |    nan | -27.03 [-38.26, -15.79] |
| lagr         |   5 |   8 |       1 |  -2.938 |     0.325 | 1.1   |     50   |        -2.94 |    0.238 |  -0.038 |    nan | -3.18 [-5.44, -0.92]    |
| lagr_lam0.17 |   0 |   8 |       1 |  -5.173 |     0.973 | 1.303 |     62.5 |        -5.17 |    0.238 |  -0.038 |    nan | -5.41 [-8.97, -1.85]    |

## val: score by GOP class

| method       |   k |   stable_n |   stable |   stable_ctrl |   stable_search |   cut_n |   cut |   cut_ctrl |   cut_search |   gradual_n |   gradual |   gradual_ctrl |   gradual_search |
|:-------------|----:|-----------:|---------:|--------------:|----------------:|--------:|------:|-----------:|-------------:|------------:|----------:|---------------:|-----------------:|
| bc           |   0 |          8 |  -26.787 |           nan |           0.238 |       0 |   nan |        nan |          nan |           0 |       nan |            nan |              nan |
| lagr         |   5 |          8 |   -2.938 |           nan |           0.238 |       0 |   nan |        nan |          nan |           0 |       nan |            nan |              nan |
| lagr_lam0.17 |   0 |          8 |   -5.173 |           nan |           0.238 |       0 |   nan |        nan |          nan |           0 |       nan |            nan |              nan |
