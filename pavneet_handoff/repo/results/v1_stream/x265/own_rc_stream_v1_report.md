# Stream RL vs the encoder's own rate control (x265, v1 test streams, dB metric)

724 cases = 181 streams of 8 GOPs x 4 budget levels at s = 1 (budget = sum of the GOPs' budgets.csv budgets). The encoder codes each stream as one encode told the budget as an average bitrate and picks a QP per frame; RL and the rule pick one QP per GOP (curve lookups). Score = dPSNR_B - 0.17 dB per 1 % over on the stream's pooled PSNR. CIs: cluster bootstrap over source groups (mixed streams: each its own cluster). Failed encodes (left out): {'abr': 0, 'abr_vbv': 0, 'abr_tree': 0, 'abr_aq': 0, '2pass': 0, '2pass_aq': 0}.

| method                     |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |
|:---------------------------|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|
| equal split per GOP        |     724 |       -1.053 |    -0.737 | 94.3%  | 21%        |         1.857 |      -0.729 |  -1.315 |
| rule (tuned), L=0          |     724 |       -0.624 |    -0.527 | 96.9%  | 11%        |         0.571 |      -0.433 |  -0.779 |
| rule (tuned), L=2          |     724 |       -0.419 |    -0.331 | 97.7%  | 11%        |         0.519 |      -0.32  |  -0.499 |
| best constant QP (offline) |     724 |       -0.212 |    -0.137 | 96.7%  | 17%        |         0.442 |      -0.209 |  -0.214 |
| hindsight per-GOP plan     |     724 |        0.22  |     0.225 | 99.8%  | 0%         |         0.03  |       0.132 |   0.292 |
| RL bc_ppo, L=0             |     724 |       -0.428 |    -0.364 | 96.0%  | 11%        |         0.375 |      -0.478 |  -0.387 |
| RL bc_ppo, L=2             |     724 |       -0.205 |    -0.143 | 97.9%  | 10%        |         0.362 |      -0.241 |  -0.175 |
| RL ppo, L=0                |     724 |       -0.447 |    -0.363 | 96.3%  | 14%        |         0.494 |      -0.428 |  -0.461 |
| RL ppo, L=2                |     724 |       -0.216 |    -0.136 | 98.2%  | 12%        |         0.465 |      -0.208 |  -0.222 |
| RL bc_ppo_lag, L=0         |     724 |       -0.473 |    -0.442 | 94.7%  | 6%         |         0.183 |      -0.519 |  -0.437 |
| RL bc_ppo_lag, L=2         |     724 |       -0.209 |    -0.175 | 97.0%  | 5%         |         0.199 |      -0.248 |  -0.178 |
| x265 abr                   |     724 |       -2.417 |     0.053 | 111.7% | 61%        |        14.527 |      -1.695 |  -3.002 |
| x265 abr_vbv               |     724 |       -0.646 |    -0.492 | 97.9%  | 27%        |         0.905 |      -0.656 |  -0.638 |
| x265 abr_tree              |     724 |       -2.743 |    -0.559 | 102.7% | 34%        |        12.844 |      -1.995 |  -3.348 |
| x265 abr_aq                |     724 |       -3.036 |    -0.59  | 106.4% | 40%        |        14.393 |      -2.103 |  -3.793 |
| x265 2pass                 |     724 |       -0.215 |     0.017 | 100.6% | 35%        |         1.362 |      -0.263 |  -0.175 |
| x265 2pass_aq              |     724 |       -0.269 |     0.015 | 100.5% | 36%        |         1.675 |      -0.371 |  -0.187 |

## Paired differences

| A                      | B             | comparison                                |   cases | score A-B (dB)          |   >1% over A-B (pts) |
|:-----------------------|:--------------|:------------------------------------------|--------:|:------------------------|---------------------:|
| RL bc_ppo, L=2         | x265 abr_tree | causal RL vs causal encoder ABR (+cutree) |     724 | +2.538 [+1.991, +3.381] |                -23.5 |
| RL ppo, L=2            | x265 abr_tree | causal RL vs causal encoder ABR (+cutree) |     724 | +2.527 [+1.988, +3.357] |                -21.9 |
| RL bc_ppo, L=2         | x265 abr_vbv  | causal RL vs ABR+VBV                      |     724 | +0.441 [+0.350, +0.541] |                -17   |
| RL bc_ppo, L=0         | x265 abr      | causal, no lookahead each                 |     724 | +1.989 [+1.434, +2.816] |                -50.4 |
| rule (tuned), L=2      | x265 abr_tree | non-learned vs encoder                    |     724 | +2.324 [+1.802, +3.117] |                -22.7 |
| RL bc_ppo, L=2         | x265 2pass    | causal RL vs non-causal two-pass          |     724 | +0.010 [-0.041, +0.055] |                -24.2 |
| hindsight per-GOP plan | x265 2pass    | both non-causal                           |     724 | +0.435 [+0.359, +0.515] |                -34.7 |

## Check (stream encode vs v1 per-GOP curves)

- clip QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- mixed QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- mixed QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- mixed QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- mixed QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
