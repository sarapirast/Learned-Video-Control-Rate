# Exp 5b BC-only rung, fold (exp_next/exp5/bc_report.py)

final4 + mean[t] + BC (argmax, 13 offsets), bit cap. Seeds 0/1/2 averaged per episode (per-seed means listed). Paired, 95% clip bootstrap over the 8 fold clips ('*' excludes 0), hole excluded. mean-only = Exp 5a pooled:bit (same mean[t] and cap, offset 0). Caveat: final4's rate model saw the fold clips.

## x264

- k0+k5: BC - final4 -0.327 [-0.510, -0.165] *; BC - mean-only -0.324 [-0.513, -0.148] *; mean-only - final4 -0.003 [-0.021, +0.010] (n 582)
- k0: BC - final4 -0.549 [-0.888, -0.243] *; BC - mean-only -0.501 [-0.824, -0.224] *; mean-only - final4 -0.047 [-0.098, -0.007] * (n 291)
- k5: BC - final4 -0.105 [-0.180, -0.045] *; BC - mean-only -0.147 [-0.241, -0.063] *; mean-only - final4 +0.042 [+0.008, +0.084] * (n 291)
- per seed (BC - final4, k0+k5): s0 -0.290; s1 -0.371; s2 -0.319
- cut/gradual vs stable (BC - final4): cut/gradual +0.010 [-0.065, +0.111] (n 48); stable -0.357 [-0.596, -0.171] * (n 534)
- share of frames with BC offset 0: 0.18

## x265

- k0+k5: BC - final4 -0.193 [-0.329, -0.079] *; BC - mean-only -0.230 [-0.390, -0.098] *; mean-only - final4 +0.037 [+0.003, +0.077] * (n 584)
- k0: BC - final4 -0.426 [-0.679, -0.212] *; BC - mean-only -0.424 [-0.676, -0.211] *; mean-only - final4 -0.002 [-0.032, +0.032] (n 292)
- k5: BC - final4 +0.040 [-0.042, +0.108]; BC - mean-only -0.035 [-0.103, +0.019]; mean-only - final4 +0.076 [+0.024, +0.143] * (n 292)
- per seed (BC - final4, k0+k5): s0 -0.195; s1 -0.168; s2 -0.215
- cut/gradual vs stable (BC - final4): cut/gradual +0.149 [-0.044, +0.374] (n 48); stable -0.224 [-0.373, -0.093] * (n 536)
- share of frames with BC offset 0: 0.19

## Decomposition (seed-level episodes)

| enc   |   k | method             |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:------|----:|:-------------------|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| x264  |   0 | final4 + mean + BC |  -0.908 |  0.019 | -0.927 |         15.024 |        48.939 |        -13.085 |   32.532 |
| x264  |   0 | final4             |  -0.36  | -0.049 | -0.311 |          3.61  |         8.565 |         -1.649 |   46.392 |
| x264  |   5 | final4 + mean + BC |  -0.217 |  0.104 | -0.321 |          4.684 |        16.717 |         -3.281 |   46.85  |
| x264  |   5 | final4             |  -0.113 |  0.081 | -0.194 |          1.928 |         2.55  |         -0.209 |   51.89  |
| x265  |   0 | final4 + mean + BC |  -0.887 | -0.162 | -0.725 |         11.491 |        38.864 |         -8.707 |   42.466 |
| x265  |   0 | final4             |  -0.461 | -0.154 | -0.307 |          3.699 |         7.814 |         -1.774 |   51.37  |
| x265  |   5 | final4 + mean + BC |  -0.204 |  0.043 | -0.247 |          3.49  |         7.749 |         -2.078 |   50.457 |
| x265  |   5 | final4             |  -0.244 | -0.031 | -0.213 |          2.146 |         3.59  |         -0.053 |   55.822 |

