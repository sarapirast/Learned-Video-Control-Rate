# Stream RL vs the encoder's own rate control (x264, v1 test streams, dB metric, luma PSNR of pooled MSE (D50))

724 cases = 181 streams of 8 GOPs x 4 budget levels at s = 1 (budget = sum of the GOPs' budgets.csv budgets). The encoder codes each stream as one encode told the budget as an average bitrate and picks a QP per frame; RL and the rule pick one QP per GOP (curve lookups). Score = dPSNR_B - 0.17 dB per 1 % over on the stream's pooled PSNR. CIs: cluster bootstrap over source groups (mixed streams: each its own cluster). Failed encodes (left out): {'abr': 0, 'abr_vbv': 0, 'abr_tree': 0, 'abr_aq': 0, '2pass': 0, '2pass_aq': 0}.

| method                     |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |
|:---------------------------|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|
| equal split per GOP        |     724 |       -1.405 |    -1.184 | 90.8%  | 16%        |         1.3   |      -0.961 |  -1.765 |
| rule (tuned), L=0          |     724 |       -0.865 |    -0.752 | 96.3%  | 13%        |         0.662 |      -0.62  |  -1.063 |
| rule (tuned), L=2          |     724 |       -0.611 |    -0.503 | 97.1%  | 12%        |         0.636 |      -0.468 |  -0.726 |
| best constant QP (offline) |     724 |       -0.23  |    -0.146 | 97.0%  | 19%        |         0.494 |      -0.216 |  -0.242 |
| hindsight per-GOP plan     |     724 |       -0.132 |    -0.127 | 99.8%  | 0%         |         0.031 |      -0.1   |  -0.158 |
| RL bc_ppo, L=0             |     724 |       -0.692 |    -0.605 | 95.7%  | 13%        |         0.51  |      -0.696 |  -0.688 |
| RL bc_ppo, L=2             |     724 |       -0.464 |    -0.384 | 96.9%  | 12%        |         0.47  |      -0.429 |  -0.493 |
| RL ppo, L=0                |     724 |       -0.674 |    -0.558 | 96.1%  | 16%        |         0.683 |      -0.581 |  -0.75  |
| RL ppo, L=2                |     724 |       -0.439 |    -0.334 | 97.4%  | 15%        |         0.619 |      -0.349 |  -0.512 |
| RL bc_ppo_lag, L=0         |     724 |       -0.731 |    -0.679 | 94.6%  | 8%         |         0.303 |      -0.686 |  -0.767 |
| RL bc_ppo_lag, L=2         |     724 |       -0.492 |    -0.44  | 96.1%  | 8%         |         0.306 |      -0.435 |  -0.538 |
| x264 abr                   |     724 |       -1.492 |    -0.431 | 103.5% | 59%        |         6.237 |      -1.249 |  -1.688 |
| x264 abr_vbv               |     724 |       -0.759 |    -0.444 | 101.3% | 56%        |         1.851 |      -0.605 |  -0.883 |
| x264 abr_tree              |     724 |       -1.208 |    -0.517 | 98.0%  | 40%        |         4.065 |      -1.354 |  -1.089 |
| x264 abr_aq                |     724 |       -1.672 |    -1.116 | 97.1%  | 38%        |         3.269 |      -1.827 |  -1.547 |
| x264 2pass                 |     724 |       -0.159 |    -0.105 | 98.7%  | 12%        |         0.315 |      -0.204 |  -0.123 |
| x264 2pass_aq              |     724 |       -0.427 |    -0.359 | 99.2%  | 15%        |         0.399 |      -0.529 |  -0.345 |

## Paired differences

| A                      | B             | comparison                                |   cases | score A-B (dB)          |   >1% over A-B (pts) |
|:-----------------------|:--------------|:------------------------------------------|--------:|:------------------------|---------------------:|
| RL bc_ppo, L=2         | x264 abr_tree | causal RL vs causal encoder ABR (+cutree) |     724 | +0.743 [+0.444, +1.118] |                -28.3 |
| RL ppo, L=2            | x264 abr_tree | causal RL vs causal encoder ABR (+cutree) |     724 | +0.769 [+0.449, +1.174] |                -25.9 |
| RL bc_ppo, L=2         | x264 abr_vbv  | causal RL vs ABR+VBV                      |     724 | +0.294 [+0.209, +0.400] |                -44.1 |
| RL bc_ppo, L=0         | x264 abr      | causal, no lookahead each                 |     724 | +0.800 [+0.651, +0.996] |                -45.4 |
| rule (tuned), L=2      | x264 abr_tree | non-learned vs encoder                    |     724 | +0.597 [+0.271, +0.996] |                -28   |
| RL bc_ppo, L=2         | x264 2pass    | causal RL vs non-causal two-pass          |     724 | -0.305 [-0.412, -0.223] |                 -0   |
| hindsight per-GOP plan | x264 2pass    | both non-causal                           |     724 | +0.027 [-0.092, +0.107] |                -12.2 |
