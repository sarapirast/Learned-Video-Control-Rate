# Day-1 offline architecture test, x264 (tracker 36; repo-pavneet tools/arch_offline.py)

BC imitation of the search's best HELD-OUT plans (a quarter of the natural train clips, seed 0; the val split's search results lack per-frame bits) (lfqp data: offsets -10..+10 around the previous-GOP base). Steps 20000, seeds 0,1, top 4 plans per GOP x budget. MAE = |offset - search offset| (QP), per GOP then averaged; diff = arch - mlp(per-k), paired by GOP, 95% bootstrap over clips (negative MAE diff = better). Gate 1: a set_* net beats mlp per-k on pooled MAE (CI < 0) on both encoders, not worse on cut GOPs.

## Val imitation

| arch     | train   |   params |   MAE k0 |   MAE k2 |   MAE k5 |   MAE k10 |   MAE k29 |   MAE pooled |   acc pooled |   NLL pooled | MAE diff pooled         | MAE diff stable         | MAE diff cut            |
|:---------|:--------|---------:|---------:|---------:|---------:|----------:|----------:|-------------:|-------------:|-------------:|:------------------------|:------------------------|:------------------------|
| mlp      | anyk    |   160021 |    1.173 |    1.162 |    1.14  |     1.122 |     1.117 |        1.143 |        0.306 |        1.798 | -0.054 [-0.080, -0.031] | -0.054 [-0.083, -0.029] | -0.070 [-0.101, -0.045] |
| mlp      | per-k   |   160021 |    1.202 |    1.207 |    1.187 |     1.196 |     1.192 |        1.197 |        0.296 |        1.891 | nan                     | nan                     | nan                     |
| set_attn | anyk    |    34773 |    1.165 |    1.152 |    1.12  |     1.101 |     1.1   |        1.128 |        0.306 |        1.766 | -0.069 [-0.115, -0.032] | -0.060 [-0.100, -0.026] | -0.124 [-0.195, -0.087] |
| set_attn | per-k   |    34773 |    1.192 |    1.189 |    1.153 |     1.165 |     1.139 |        1.168 |        0.297 |        1.807 | -0.029 [-0.058, -0.004] | -0.020 [-0.048, +0.002] | -0.065 [-0.100, -0.037] |
| set_mm   | anyk    |    35189 |    1.161 |    1.164 |    1.127 |     1.107 |     1.109 |        1.133 |        0.305 |        1.773 | -0.063 [-0.103, -0.028] | -0.055 [-0.092, -0.023] | -0.105 [-0.162, -0.071] |
| set_mm   | per-k   |    35189 |    1.194 |    1.195 |    1.149 |     1.161 |     1.15  |        1.17  |        0.297 |        1.804 | -0.027 [-0.060, -0.000] | -0.019 [-0.050, +0.005] | -0.068 [-0.097, -0.052] |

