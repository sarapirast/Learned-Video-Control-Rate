# Fair head-to-head: learned vs the encoder's own rate control (x265, multi-GOP test streams)

912 cases = 152 streams of 8 GOPs x budgets (q0 (30, 38) x s (0.85, 1.0, 1.18)). No method gets an oracle QP: each is given the stream's bit budget. The encoder codes the stream as one 240-frame encode (IDR every 30; plain = AQ/cutree off, tree = cutree on, aq = encoder defaults), picking a QP per frame; the RL controllers and our rule pick one QP per GOP. Score = % bits saved at equal pooled PSNR vs the stream's constant-QP curve - 2 x % over budget.

Failed encodes (left out): {'abr': 0, 'abr_tree_la30': 0, 'abr_tree_la90': 0, '2pass': 0, 'abr_aq_la30': 0, '2pass_aq': 0}. 95 % CIs: bootstrap over 138 clusters (source clip for same-clip streams, the stream for mixed streams).

| method                       |   cases |   score |   saving | >1% over   |   mean % over |   score same-clip |   score mixed |
|:-----------------------------|--------:|--------:|---------:|:-----------|--------------:|------------------:|--------------:|
| our rule (model QP), L=0     |     912 |  -20.68 |   -17.66 | 27%        |          1.51 |            -15.68 |        -23.28 |
| our rule (model QP), L=2     |     912 |  -10.37 |    -8.6  | 27%        |          0.88 |             -5.14 |        -13.09 |
| best constant QP (hindsight) |     912 |    0    |     0    | 0%         |          0    |              0    |          0    |
| hindsight per-GOP plan       |     912 |   12.54 |    12.54 | 0%         |          0    |              8.36 |         14.71 |
| RL bc, L=0                   |     912 |  -16.99 |   -14.74 | 10%        |          1.12 |            -15.6  |        -17.71 |
| RL bc, L=2                   |     912 |  -19.56 |   -18.09 | 7%         |          0.74 |            -14.99 |        -21.94 |
| RL bc_ppo, L=0               |     912 |    1.65 |     1.7  | 1%         |          0.03 |             -1.32 |          3.19 |
| RL bc_ppo, L=2               |     912 |    3.23 |     3.28 | 1%         |          0.03 |              0.52 |          4.64 |
| RL ppo, L=0                  |     912 |    0.96 |     1.05 | 2%         |          0.04 |             -1.55 |          2.26 |
| RL ppo, L=2                  |     912 |    3.04 |     3.13 | 1%         |          0.04 |              0.23 |          4.51 |
| x265 abr                     |     912 |  -37.53 |   -13.35 | 64%        |         12.09 |            -24.5  |        -44.31 |
| x265 abr_tree_la30           |     912 |  -21.65 |    -0.73 | 34%        |         10.46 |            -18.06 |        -23.52 |
| x265 abr_tree_la90           |     912 |  -21.65 |    -0.73 | 34%        |         10.46 |            -18.06 |        -23.52 |
| x265 2pass                   |     912 |   -2.3  |    -0.38 | 30%        |          0.96 |             -3.96 |         -1.44 |
| x265 abr_aq_la30             |     912 |  -23.52 |    -2.51 | 34%        |         10.5  |            -21.34 |        -24.65 |
| x265 2pass_aq                |     912 |    3.83 |     7.03 | 45%        |          1.6  |              0.25 |          5.69 |

## Paired differences

| A                        | B                  | comparison                               |   cases | score A-B               | saving A-B              | >1% over A-B (pts)      |
|:-------------------------|:-------------------|:-----------------------------------------|--------:|:------------------------|:------------------------|:------------------------|
| RL bc_ppo, L=0           | x265 abr           | causal; encoder ABR (uses no lookahead)  |     912 | +39.17 [+33.57, +45.82] | +15.05 [+12.78, +17.45] | -62.65 [-69.01, -56.55] |
| RL bc_ppo, L=0           | x265 abr_tree_la30 | causal, 30-frame lookahead each          |     912 | +23.30 [+18.68, +28.48] | +2.43 [+1.26, +3.74]    | -32.60 [-37.95, -27.78] |
| RL bc_ppo, L=2           | x265 abr_tree_la90 | causal, 90-frame lookahead each          |     912 | +24.88 [+20.38, +29.94] | +4.01 [+2.88, +5.25]    | -32.82 [-38.16, -27.98] |
| RL ppo, L=2              | x265 abr_tree_la90 | causal, 90-frame lookahead each          |     912 | +24.69 [+20.21, +29.79] | +3.85 [+2.72, +5.13]    | -32.38 [-37.73, -27.52] |
| our rule (model QP), L=0 | x265 abr_tree_la30 | non-learned vs encoder, same information |     912 | +0.97 [-5.65, +7.47]    | -16.93 [-22.89, -12.09] | -6.69 [-13.93, +0.23]   |
| RL bc_ppo, L=0           | x265 abr_aq_la30   | encoder with its default AQ/cutree       |     912 | +25.16 [+20.27, +30.59] | +4.22 [+2.87, +5.70]    | -33.26 [-39.17, -27.88] |
| RL bc_ppo, L=2           | x265 2pass         | causal RL vs non-causal encoder          |     912 | +5.53 [+4.46, +6.54]    | +3.66 [+2.58, +4.80]    | -29.09 [-35.75, -22.02] |
| hindsight per-GOP plan   | x265 2pass         | both non-causal                          |     912 | +14.84 [+13.56, +16.35] | +12.92 [+11.60, +14.47] | -29.82 [-36.43, -22.95] |

## Check (stream encode vs per-GOP curves)

- clip QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip ABR (plain) at QP38 budget: bits/budget la30 1.021, la90 1.021, identical=True
- clip ABR (tree) at QP38 budget: bits/budget la30 0.885, la90 0.885, identical=True
- clip QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- clip ABR (plain) at QP38 budget: bits/budget la30 1.021, la90 1.021, identical=True
- clip ABR (tree) at QP38 budget: bits/budget la30 1.355, la90 1.355, identical=True
- mixed QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- mixed QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- mixed ABR (plain) at QP38 budget: bits/budget la30 1.162, la90 1.162, identical=True
- mixed ABR (tree) at QP38 budget: bits/budget la30 1.391, la90 1.391, identical=True
- mixed QP30: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- mixed QP38: per-GOP bits rel. diff max 0.0000, PSNR diff max 0.0000 dB
- mixed ABR (plain) at QP38 budget: bits/budget la30 0.898, la90 0.898, identical=True
- mixed ABR (tree) at QP38 budget: bits/budget la30 0.708, la90 0.708, identical=True
