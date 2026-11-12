# Fair head-to-head: learned vs the encoder's own rate control (x264, multi-GOP test streams)

912 cases = 152 streams of 8 GOPs x budgets (q0 (30, 38) x s (0.85, 1.0, 1.18)). No method gets an oracle QP: each is given the stream's bit budget. The encoder codes the stream as one 240-frame encode (IDR every 30; plain = AQ/cutree off, tree = cutree on, aq = encoder defaults), picking a QP per frame; the RL controllers and our rule pick one QP per GOP. Score = % bits saved at equal pooled PSNR vs the stream's constant-QP curve - 2 x % over budget.

Failed encodes (left out): {'abr': 0, 'abr_tree_la30': 0, 'abr_tree_la90': 0, '2pass': 0, 'abr_aq_la30': 0, '2pass_aq': 0}. 95 % CIs: bootstrap over 138 clusters (source clip for same-clip streams, the stream for mixed streams).

| method                       |   cases |   score |   saving | >1% over   |   mean % over |   score same-clip |   score mixed |
|:-----------------------------|--------:|--------:|---------:|:-----------|--------------:|------------------:|--------------:|
| our rule (model QP), L=0     |     912 |  -44.86 |   -37.75 | 33%        |          3.55 |            -16.32 |        -59.7  |
| our rule (model QP), L=2     |     912 |  -14.08 |   -11.24 | 34%        |          1.42 |             -7.57 |        -17.47 |
| best constant QP (hindsight) |     912 |    0    |     0    | 0%         |          0    |              0    |          0    |
| hindsight per-GOP plan       |     912 |   12.45 |    12.46 | 0%         |          0    |              8.67 |         14.42 |
| RL bc, L=0                   |     912 |  -16.06 |   -13.9  | 9%         |          1.08 |            -13.43 |        -17.43 |
| RL bc, L=2                   |     912 |  -19.63 |   -18.1  | 7%         |          0.76 |            -15.27 |        -21.9  |
| RL bc_ppo, L=0               |     912 |    0.11 |     0.47 | 2%         |          0.18 |             -1.76 |          1.07 |
| RL bc_ppo, L=2               |     912 |    1.86 |     2.06 | 1%         |          0.1  |             -0.11 |          2.89 |
| RL ppo, L=0                  |     912 |   -0.77 |    -0.33 | 2%         |          0.22 |             -2.04 |         -0.12 |
| RL ppo, L=2                  |     912 |    1.87 |     2.05 | 1%         |          0.09 |              0.12 |          2.78 |
| x264 abr                     |     912 |  -29.61 |   -10.24 | 70%        |          9.68 |            -28.94 |        -29.95 |
| x264 abr_tree_la30           |     912 |  -13.42 |    -0.61 | 45%        |          6.41 |            -16.52 |        -11.82 |
| x264 abr_tree_la90           |     912 |  -13.42 |    -0.61 | 45%        |          6.41 |            -16.52 |        -11.82 |
| x264 2pass                   |     912 |    0.57 |     1.94 | 22%        |          0.69 |             -0.94 |          1.35 |
| x264 abr_aq_la30             |     912 |  -18.81 |    -8.37 | 41%        |          5.22 |            -21.61 |        -17.35 |
| x264 2pass_aq                |     912 |    3.18 |     4.49 | 22%        |          0.66 |             -1.02 |          5.36 |

## Paired differences

| A                        | B                  | comparison                               |   cases | score A-B               | saving A-B              | >1% over A-B (pts)      |
|:-------------------------|:-------------------|:-----------------------------------------|--------:|:------------------------|:------------------------|:------------------------|
| RL bc_ppo, L=0           | x264 abr           | causal; encoder ABR (uses no lookahead)  |     912 | +29.71 [+25.79, +34.09] | +10.72 [+8.89, +12.64]  | -67.65 [-74.81, -60.90] |
| RL bc_ppo, L=0           | x264 abr_tree_la30 | causal, 30-frame lookahead each          |     912 | +13.53 [+9.79, +17.48]  | +1.08 [-0.71, +2.95]    | -42.43 [-49.73, -36.05] |
| RL bc_ppo, L=2           | x264 abr_tree_la90 | causal, 90-frame lookahead each          |     912 | +15.29 [+11.67, +19.13] | +2.67 [+0.86, +4.54]    | -43.49 [-50.93, -36.86] |
| RL ppo, L=2              | x264 abr_tree_la90 | causal, 90-frame lookahead each          |     912 | +15.29 [+11.67, +19.14] | +2.66 [+0.85, +4.55]    | -43.46 [-50.94, -36.77] |
| our rule (model QP), L=0 | x264 abr_tree_la30 | non-learned vs encoder, same information |     912 | -31.44 [-56.38, -12.45] | -37.14 [-59.42, -19.38] | -11.40 [-20.47, -2.66]  |
| RL bc_ppo, L=0           | x264 abr_aq_la30   | encoder with its default AQ/cutree       |     912 | +18.91 [+15.35, +22.73] | +8.85 [+6.63, +11.19]   | -38.71 [-45.94, -32.41] |
| RL bc_ppo, L=2           | x264 2pass         | causal RL vs non-causal encoder          |     912 | +1.30 [+0.25, +2.35]    | +0.12 [-0.75, +1.03]    | -20.25 [-25.36, -15.24] |
| hindsight per-GOP plan   | x264 2pass         | both non-causal                          |     912 | +11.89 [+10.55, +13.44] | +10.52 [+9.30, +11.96]  | -21.60 [-26.83, -16.55] |

## Check (stream encode vs per-GOP curves)

- clip QP30: per-GOP bits rel. diff max 0.0001, PSNR diff max 0.0000 dB
- clip QP38: per-GOP bits rel. diff max 0.0002, PSNR diff max 0.0000 dB
- clip ABR (plain) at QP38 budget: bits/budget la30 1.202, la90 1.202, identical=True
- clip ABR (tree) at QP38 budget: bits/budget la30 1.117, la90 1.117, identical=True
- clip QP30: per-GOP bits rel. diff max 0.0012, PSNR diff max 0.0000 dB
- clip QP38: per-GOP bits rel. diff max 0.0027, PSNR diff max 0.0000 dB
- clip ABR (plain) at QP38 budget: bits/budget la30 0.871, la90 0.871, identical=True
- clip ABR (tree) at QP38 budget: bits/budget la30 0.731, la90 0.731, identical=True
- mixed QP30: per-GOP bits rel. diff max 0.0003, PSNR diff max 0.0000 dB
- mixed QP38: per-GOP bits rel. diff max 0.0007, PSNR diff max 0.0000 dB
- mixed ABR (plain) at QP38 budget: bits/budget la30 1.075, la90 1.075, identical=True
- mixed ABR (tree) at QP38 budget: bits/budget la30 0.972, la90 0.972, identical=True
- mixed QP30: per-GOP bits rel. diff max 0.0003, PSNR diff max 0.0000 dB
- mixed QP38: per-GOP bits rel. diff max 0.0007, PSNR diff max 0.0000 dB
- mixed ABR (plain) at QP38 budget: bits/budget la30 0.934, la90 0.934, identical=True
- mixed ABR (tree) at QP38 budget: bits/budget la30 0.714, la90 0.714, identical=True
