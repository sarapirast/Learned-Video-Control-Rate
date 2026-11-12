# Stream RL vs the encoder's own rate control (x264, v1 test streams, dB metric)

724 cases = 181 streams of 8 GOPs x 4 budget levels at s = 1 (budget = sum of the GOPs' budgets.csv budgets). The encoder codes each stream as one encode told the budget as an average bitrate and picks a QP per frame; RL and the rule pick one QP per GOP (curve lookups). Score = dPSNR_B - 0.17 dB per 1 % over on the stream's pooled PSNR. CIs: cluster bootstrap over source groups (mixed streams: each its own cluster). Failed encodes (left out): {'abr': 0, 'abr_vbv': 0, 'abr_tree': 0, 'abr_aq': 0, '2pass': 0, '2pass_aq': 0}.

| method                     |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |
|:---------------------------|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|
| equal split per GOP        |     724 |       -1.189 |    -0.968 | 90.8%  | 16%        |         1.3   |      -0.857 |  -1.457 |
| rule (tuned), L=0          |     724 |       -0.701 |    -0.589 | 96.3%  | 13%        |         0.662 |      -0.512 |  -0.855 |
| rule (tuned), L=2          |     724 |       -0.511 |    -0.403 | 97.1%  | 12%        |         0.636 |      -0.411 |  -0.592 |
| best constant QP (offline) |     724 |       -0.21  |    -0.126 | 97.0%  | 19%        |         0.494 |      -0.196 |  -0.221 |
| hindsight per-GOP plan     |     724 |        0.215 |     0.22  | 99.8%  | 0%         |         0.031 |       0.135 |   0.28  |
| RL bc_ppo, L=0             |     724 |       -0.553 |    -0.466 | 95.7%  | 13%        |         0.51  |      -0.563 |  -0.545 |
| RL bc_ppo, L=2             |     724 |       -0.377 |    -0.297 | 96.9%  | 12%        |         0.47  |      -0.369 |  -0.384 |
| RL ppo, L=0                |     724 |       -0.55  |    -0.434 | 96.1%  | 16%        |         0.683 |      -0.489 |  -0.601 |
| RL ppo, L=2                |     724 |       -0.375 |    -0.27  | 97.4%  | 15%        |         0.619 |      -0.314 |  -0.425 |
| RL bc_ppo_lag, L=0         |     724 |       -0.579 |    -0.527 | 94.6%  | 8%         |         0.303 |      -0.549 |  -0.603 |
| RL bc_ppo_lag, L=2         |     724 |       -0.399 |    -0.347 | 96.1%  | 8%         |         0.306 |      -0.369 |  -0.423 |
| x264 abr                   |     724 |       -1.243 |    -0.182 | 103.5% | 59%        |         6.237 |      -1.047 |  -1.401 |
| x264 abr_vbv               |     724 |       -0.55  |    -0.235 | 101.3% | 56%        |         1.851 |      -0.494 |  -0.595 |
| x264 abr_tree              |     724 |       -0.949 |    -0.258 | 98.0%  | 40%        |         4.065 |      -1.074 |  -0.848 |
| x264 abr_aq                |     724 |       -1.175 |    -0.62  | 97.1%  | 38%        |         3.269 |      -1.311 |  -1.066 |
| x264 2pass                 |     724 |       -0.106 |    -0.052 | 98.7%  | 12%        |         0.315 |      -0.166 |  -0.058 |
| x264 2pass_aq              |     724 |       -0.13  |    -0.062 | 99.2%  | 15%        |         0.399 |      -0.241 |  -0.041 |

## Paired differences

| A                      | B             | comparison                                |   cases | score A-B (dB)          |   >1% over A-B (pts) |
|:-----------------------|:--------------|:------------------------------------------|--------:|:------------------------|---------------------:|
| RL bc_ppo, L=2         | x264 abr_tree | causal RL vs causal encoder ABR (+cutree) |     724 | +0.572 [+0.331, +0.840] |                -28.3 |
| RL ppo, L=2            | x264 abr_tree | causal RL vs causal encoder ABR (+cutree) |     724 | +0.574 [+0.323, +0.858] |                -25.9 |
| RL bc_ppo, L=2         | x264 abr_vbv  | causal RL vs ABR+VBV                      |     724 | +0.173 [+0.094, +0.256] |                -44.1 |
| RL bc_ppo, L=0         | x264 abr      | causal, no lookahead each                 |     724 | +0.690 [+0.551, +0.881] |                -45.4 |
| rule (tuned), L=2      | x264 abr_tree | non-learned vs encoder                    |     724 | +0.438 [+0.180, +0.727] |                -28   |
| RL bc_ppo, L=2         | x264 2pass    | causal RL vs non-causal two-pass          |     724 | -0.271 [-0.367, -0.191] |                 -0   |
| hindsight per-GOP plan | x264 2pass    | both non-causal                           |     724 | +0.321 [+0.240, +0.414] |                -12.2 |

## Check (stream encode vs v1 per-GOP curves)

- clip QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip QP38: per-GOP bits rel. diff max 0.0001, PSNR diff max 0.0000 dB
- mixed QP30: per-GOP bits rel. diff max 0.0002, PSNR diff max 0.0000 dB
- mixed QP38: per-GOP bits rel. diff max 0.0005, PSNR diff max 0.0000 dB
- mixed QP30: per-GOP bits rel. diff max 0.0001, PSNR diff max 0.0000 dB
- mixed QP38: per-GOP bits rel. diff max 0.0002, PSNR diff max 0.0000 dB
