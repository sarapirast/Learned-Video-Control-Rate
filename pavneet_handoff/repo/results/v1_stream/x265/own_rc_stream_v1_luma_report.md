# Stream RL vs the encoder's own rate control (x265, v1 test streams, dB metric, luma PSNR of pooled MSE (D50))

724 cases = 181 streams of 8 GOPs x 4 budget levels at s = 1 (budget = sum of the GOPs' budgets.csv budgets). The encoder codes each stream as one encode told the budget as an average bitrate and picks a QP per frame; RL and the rule pick one QP per GOP (curve lookups). Score = dPSNR_B - 0.17 dB per 1 % over on the stream's pooled PSNR. CIs: cluster bootstrap over source groups (mixed streams: each its own cluster). Failed encodes (left out): {'abr': 0, 'abr_vbv': 0, 'abr_tree': 0, 'abr_aq': 0, '2pass': 0, '2pass_aq': 0}.

| method                     |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   mean over % |   same-clip |   mixed |
|:---------------------------|--------:|-------------:|----------:|:-------|:-----------|--------------:|------------:|--------:|
| equal split per GOP        |     724 |       -1.236 |    -0.92  | 94.3%  | 21%        |         1.857 |      -0.774 |  -1.61  |
| rule (tuned), L=0          |     724 |       -0.773 |    -0.676 | 96.9%  | 11%        |         0.571 |      -0.496 |  -0.998 |
| rule (tuned), L=2          |     724 |       -0.506 |    -0.417 | 97.7%  | 11%        |         0.519 |      -0.351 |  -0.631 |
| best constant QP (offline) |     724 |       -0.228 |    -0.153 | 96.7%  | 17%        |         0.442 |      -0.227 |  -0.229 |
| hindsight per-GOP plan     |     724 |       -0.083 |    -0.078 | 99.8%  | 0%         |         0.03  |      -0.045 |  -0.113 |
| RL bc_ppo, L=0             |     724 |       -0.542 |    -0.478 | 96.0%  | 11%        |         0.375 |      -0.557 |  -0.53  |
| RL bc_ppo, L=2             |     724 |       -0.265 |    -0.203 | 97.9%  | 10%        |         0.362 |      -0.268 |  -0.262 |
| RL ppo, L=0                |     724 |       -0.564 |    -0.48  | 96.3%  | 14%        |         0.494 |      -0.498 |  -0.617 |
| RL ppo, L=2                |     724 |       -0.267 |    -0.188 | 98.2%  | 12%        |         0.465 |      -0.23  |  -0.297 |
| RL bc_ppo_lag, L=0         |     724 |       -0.601 |    -0.57  | 94.7%  | 6%         |         0.183 |      -0.606 |  -0.597 |
| RL bc_ppo_lag, L=2         |     724 |       -0.273 |    -0.239 | 97.0%  | 5%         |         0.199 |      -0.279 |  -0.268 |
| x265 abr                   |     724 |       -2.548 |    -0.079 | 111.7% | 61%        |        14.527 |      -1.777 |  -3.174 |
| x265 abr_vbv               |     724 |       -0.875 |    -0.721 | 97.9%  | 27%        |         0.905 |      -0.826 |  -0.914 |
| x265 abr_tree              |     724 |       -3.011 |    -0.827 | 102.7% | 34%        |        12.844 |      -2.21  |  -3.659 |
| x265 abr_aq                |     724 |       -3.327 |    -0.88  | 106.4% | 40%        |        14.393 |      -2.352 |  -4.116 |
| x265 2pass                 |     724 |       -0.289 |    -0.058 | 100.6% | 35%        |         1.362 |      -0.273 |  -0.302 |
| x265 2pass_aq              |     724 |       -0.358 |    -0.073 | 100.5% | 36%        |         1.675 |      -0.457 |  -0.277 |

## Paired differences

| A                      | B             | comparison                                |   cases | score A-B (dB)          |   >1% over A-B (pts) |
|:-----------------------|:--------------|:------------------------------------------|--------:|:------------------------|---------------------:|
| RL bc_ppo, L=2         | x265 abr_tree | causal RL vs causal encoder ABR (+cutree) |     724 | +2.746 [+2.204, +3.577] |                -23.5 |
| RL ppo, L=2            | x265 abr_tree | causal RL vs causal encoder ABR (+cutree) |     724 | +2.744 [+2.209, +3.558] |                -21.9 |
| RL bc_ppo, L=2         | x265 abr_vbv  | causal RL vs ABR+VBV                      |     724 | +0.610 [+0.488, +0.743] |                -17   |
| RL bc_ppo, L=0         | x265 abr      | causal, no lookahead each                 |     724 | +2.006 [+1.450, +2.838] |                -50.4 |
| rule (tuned), L=2      | x265 abr_tree | non-learned vs encoder                    |     724 | +2.505 [+1.990, +3.284] |                -22.7 |
| RL bc_ppo, L=2         | x265 2pass    | causal RL vs non-causal two-pass          |     724 | +0.025 [-0.018, +0.078] |                -24.2 |
| hindsight per-GOP plan | x265 2pass    | both non-causal                           |     724 | +0.206 [+0.104, +0.288] |                -34.7 |
