# Day-1 offline architecture test, x265 (tracker 36; repo-pavneet tools/arch_offline.py)

BC imitation of the search's best HELD-OUT plans (a quarter of the natural train clips, seed 0; the val split's search results lack per-frame bits) (lfqp data: offsets -10..+10 around the previous-GOP base). Steps 20000, seeds 0,1, top 4 plans per GOP x budget. MAE = |offset - search offset| (QP), per GOP then averaged; diff = arch - mlp(per-k), paired by GOP, 95% bootstrap over clips (negative MAE diff = better). Gate 1: a set_* net beats mlp per-k on pooled MAE (CI < 0) on both encoders, not worse on cut GOPs.

## Val imitation

| arch     | train   |   params |   MAE k0 |   MAE k2 |   MAE k5 |   MAE k10 |   MAE k29 |   MAE pooled |   acc pooled |   NLL pooled | MAE diff pooled         | MAE diff stable         | MAE diff cut            |
|:---------|:--------|---------:|---------:|---------:|---------:|----------:|----------:|-------------:|-------------:|-------------:|:------------------------|:------------------------|:------------------------|
| mlp      | anyk    |   160021 |    1.142 |    1.14  |    1.135 |     1.124 |     1.086 |        1.125 |        0.313 |        1.762 | -0.059 [-0.093, -0.029] | -0.057 [-0.094, -0.026] | -0.079 [-0.123, -0.036] |
| mlp      | per-k   |   160021 |    1.178 |    1.195 |    1.19  |     1.201 |     1.158 |        1.184 |        0.302 |        1.842 | nan                     | nan                     | nan                     |
| set_attn | anyk    |    34773 |    1.129 |    1.136 |    1.111 |     1.087 |     1.05  |        1.103 |        0.317 |        1.735 | -0.081 [-0.138, -0.034] | -0.073 [-0.125, -0.029] | -0.097 [-0.182, -0.030] |
| set_attn | per-k   |    34773 |    1.166 |    1.166 |    1.157 |     1.125 |     1.091 |        1.141 |        0.308 |        1.771 | -0.043 [-0.082, -0.010] | -0.038 [-0.077, -0.007] | -0.031 [-0.066, +0.004] |
| set_mm   | anyk    |    35189 |    1.127 |    1.137 |    1.12  |     1.096 |     1.073 |        1.111 |        0.313 |        1.746 | -0.073 [-0.119, -0.031] | -0.069 [-0.111, -0.029] | -0.078 [-0.155, -0.029] |
| set_mm   | per-k   |    35189 |    1.157 |    1.164 |    1.159 |     1.117 |     1.071 |        1.134 |        0.308 |        1.76  | -0.050 [-0.099, -0.012] | -0.044 [-0.092, -0.009] | -0.050 [-0.138, +0.005] |

