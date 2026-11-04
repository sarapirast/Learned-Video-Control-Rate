# Literature survey: how RL and learned controllers get features from video (2026-11-04)

**Question:** in work where an RL policy (or a learned controller) acts on video or images, how are the input
features extracted? What does that mean for our per-frame QP policy?

**Method:** web search (arXiv, proceedings, publisher pages) plus a full read of the MuZero rate-control paper's
appendix. Details marked *(abstract)* come only from abstracts or summaries, not the full paper.

---

## 1. Learned rate control in real video encoders (closest to our problem)

| Work | What the policy sees | Pixels? | Learner | Scale |
|---|---|---|---|---|
| **MuZero-RC** (DeepMind/YouTube, VP9) [1] | the libvpx first-pass statistics of every frame; PSNR, bits and QP of every frame coded so far; next frame's index and type; video duration; target bitrate; fraction of target used | no | MuZero; a Transformer-XL over the per-frame statistic sequence gives a 512-d embedding | 20,000 training videos; evaluated on 3,062 clips |
| **Neural rate control by imitation** (Mao et al., VP9) [2] | first-pass statistics of all frames, e.g. noise energy and motion-vector statistics | no | imitation of searched optimal QP sequences | evaluated on 200 unseen videos *(abstract)* |
| **Dual-critic DDPG for x265 frame-level bit allocation** [3] | mean and variance of the frame's pixels and of its zero-motion residual; the same averaged over the rest of the GOP; % of budget left; frames left; temporal layer; GOP target | only as hand-made statistics | DDPG; the action is a delta QP in [-10, 10] on x265's own QP (a residual policy) | HEVC test sequences |
| **Frank-Wolfe action-constrained RL, x265** [4] | follows [3] | as [3] | constrained RL | *(abstract)* |
| **Q-learning for HEVC frame and intra rate control** (NYCU) [5][6] | texture complexity, bit balance | hand-made | Q-learning with a small neural Q-function | HM test sequences *(abstract)* |

**Takeaway:** none of the encoder RL work feeds raw frames to the policy.
- The state is **cheap encoder statistics plus budget bookkeeping**.
- The strongest system, MuZero-RC, learns a representation, but over the *sequence of per-frame first-pass
  statistics* (with a Transformer), not over pixels. It also trains on 20,000 videos.
- [3] is also a residual policy on the encoder's own base QP, like our proposal D.

## 2. CNN features from pixels in codec rate control (supervised, not RL)

| Work | How the CNN is used | Reported gain |
|---|---|---|
| Li et al., VCIP 2017 [7] | predicts each CTU's R-λ model parameters from its content | about 0.7% BD-rate, lower rate error |
| Wei et al., IEICE 2021 [8] | predicts the R-λ curve's parameters; the initial λ comes from them plus the bit budget | *(abstract)* |
| Lu et al., DCC 2020 [9] | predicts the R-QP parameters (µ, ν), and a second CNN predicts CTU bit consumption | 1.33% BD-rate in HM 16.9 |
| Marzuki & Sim [10] | VGG-16 features (spatial and temporal) to set CTU bit budget, λ and QP | -2.04% BD-rate vs HM-16.20 |
| VVC rate control, TCSVT 2023 [11] | deep nets infer CTU R-Q / D-Q parameters from prediction residuals | 1.77% BD-rate vs VTM-13.0 |

**Takeaway:** when codec work does use pixel CNNs, they're **trained supervised to predict rate-distortion model
parameters**, and a classical controller then uses those predictions. Gains are modest: about 0.7-2% BD-rate.

## 3. RL for video streaming (policies that pick bitrates)

- **Pensieve** [12]: the state is past throughput, download times, next-chunk sizes, buffer level, chunks left
  and last bitrate. **No content features at all.**
- **QARC** [13]: a separately trained **video quality prediction network (VQPN)** predicts future perceptual
  quality from past frames, and that *predicted quality vector* replaces raw pictures as the RL input. The authors
  call it a fix for "state explosion". The RL part (A3C) never sees pixels.

**Takeaway:** content enters RL through a supervised predictor's *outputs* (predicted quality or rate), trained
separately and frozen.

## 4. RL from images in general (Atari, DeepMind Control, robotics)

| Approach | Idea | Examples |
|---|---|---|
| End-to-end CNN | a CNN trained only by the RL loss | DQN (Mnih et al., 2015). Needs millions of frames |
| Auxiliary self-supervised tasks | extra losses on the same encoder | UNREAL: pixel control, reward prediction; about 10x faster on Labyrinth [14] |
| Contrastive representation | augmented views of a frame should match | CURL [15] |
| Augmentation only | random shifts and crops alone | DrQ, RAD (as reported in [15]'s follow-up note) |
| **Decoupled, frozen encoder** | pretrain the encoder self-supervised, then freeze it for RL | ATC (augmented temporal contrast) matches or beats end-to-end RL, and frozen ATC encoders beat other pretraining [16] |
| World models | learn a compact latent of frames plus a dynamics model, and control in latent space | World Models (VAE + MDN-RNN) [17]; Dreamer; MuZero |
| Pretrained vision models | frozen ImageNet or self-supervised features | competitive with, or better than, ground-truth state for control [18] |
| Predictive contrastive coding | predict future latents against negatives, using word2vec-style negative sampling / NCE | CPC [19], also tested on RL |

**Takeaway:** a CNN encoder trained only by the reward is data-hungry. The data-efficient recipe is to learn the
encoder with a **self-supervised or supervised proxy task** (contrastive, temporal, predictive, or a world model),
often **frozen**, and train the policy on its low-dimensional output.

CPC is the direct descendant of the word2vec idea: predict the context, with negative sampling.

## 5. Cheap "already computed" features: the compressed domain

- **CoViAR** [20] recognises actions straight from the bitstream: I-frames, motion vectors and residuals from the
  encoder.
- A codec agent has these signals for free from its own first pass.
- **Per-title encoding** in industry relies on fast **probe encodes** to estimate complexity [21]. CNN complexity
  predictors exist mainly to skip probes, not to beat them.

---

## What this means for our project

1. **We're already in the mainstream.** Pavneet's state (first-pass bits plus hand-made pixel statistics plus
   budget bookkeeping) matches what [2]-[6] use. Raw frames into the policy is not what the field does for encoder
   control, especially at our data scale: 109 clips, against MuZero-RC's 20,000 videos.
2. **The cheapest real upgrade is richer first-pass statistics, not pixels.**
   - MuZero-RC and [2] use many per-frame first-pass statistics; we use one number (first-pass bits).
   - x264's `--pass 1 --stats` file logs per frame the texture bits (I and P), motion-vector bits, other bits,
     and counts of intra, inter and skipped macroblocks.
   - x265 can log per-frame statistics and lookahead SATD costs.
   - These are the compressed-domain features of section 5, nearly free since we already run a first pass.
3. **If we want a learned latent, learn it over the sequence of per-frame statistics**, the way MuZero-RC does.
   That's a small Transformer or 1-D conv over visible frames, which is our proposal E. It also handles any k
   naturally.
4. **If we want pixel features, follow sections 2-4:**
   - pretrain a small CNN on a proxy task and freeze it; never train it through the RL reward;
   - candidate proxies: (a) supervised, predict the frame's R-D behaviour from our constant-QP curves, as in
     [7]-[11]; (b) self-supervised temporal or contrastive, as in ATC / CPC [16][19];
   - or use a frozen pretrained network as in [18];
   - and expect modest gains: [7]-[11] report about 1-2% BD-rate.
5. **Prefer predicted quantities over raw latents as the interface** where possible, as QARC does: e.g. the
   predicted P-frame cost or quality sensitivity of the GOP. They're interpretable, low-dimensional, and can be
   checked offline before any RL run.
6. **First, check that features matter at all.** In our results the k-curves are flat and the leak and oracle base
   QP dominate. A cheap offline test (does feature X improve prediction of bits, distortion or future cost on val?)
   should gate any RL retraining.

**Suggested order:** (i) the x264/x265 first-pass statistics files as extra per-frame features (cheap, no
training); (ii) the offline prediction test of (i) against the current features; (iii) only if (ii) shows headroom,
a learned encoder, over statistic sequences first and pixels second.

## References

1. Mandhane et al., "MuZero with Self-competition for Rate Control in VP9 Video Compression", arXiv 2202.06626 (2022). https://arxiv.org/abs/2202.06626
2. Mao et al., "Neural Rate Control for Video Encoding using Imitation Learning", arXiv 2012.05339 (2020). https://arxiv.org/abs/2012.05339
3. Dual-critic DDPG for frame-level bit allocation in x265, arXiv 2104.01735 (2021). https://arxiv.org/abs/2104.01735
4. Action-constrained RL with Frank-Wolfe for x265 bit allocation, arXiv 2203.05127 (2022). https://arxiv.org/abs/2203.05127
5. Chen, Hu, Peng, "Reinforcement Learning for HEVC/H.265 Frame-level Bit Allocation" (DSP 2018). https://ir.lib.nycu.edu.tw:443/handle/11536/151055
6. Hu, Peng, Chung, "Reinforcement Learning for HEVC/H.265 Intra-Frame Rate Control" (ISCAS 2018). https://ir.lib.nycu.edu.tw/handle/11536/150871
7. Li et al., "A convolutional neural network-based approach to rate control in HEVC intra coding" (VCIP 2017). https://faculty.ustc.edu.cn/chenzhibo/zh_CN/article/988219/content/2482.htm
8. Wei et al., "A CNN-based optimal CTU λ decision for HEVC intra rate control" (IEICE TIS 2021). https://www.jstage.jst.go.jp/article/transinf/E104.D/10/E104.D_2021EDL8047/_article/-char/ja
9. Lu, Zhou, Jin, Martin, "A Rate Control Scheme for HEVC Intra Coding Using CNN" (DCC 2020). https://sigport.org/node/5002
10. Marzuki, Sim, "A Deep Learning-Based Rate Control for HEVC Intra Coding". https://koreascience.kr/article/CFKO201904533880604.do
11. "Neural network based rate control for Versatile Video Coding" (IEEE TCSVT 2023). https://scholars.ln.edu.hk/en/publications/neural-network-based-rate-control-for-versatile-video-coding/
12. Mao, Netravali, Alizadeh, "Neural Adaptive Video Streaming with Pensieve" (SIGCOMM 2017). https://web.mit.edu/pensieve/
13. Huang et al., "QARC: Video Quality Aware Rate Control for Real-Time Video Streaming via Deep RL" (ACM MM 2018). https://arxiv.org/abs/1805.02482
14. Jaderberg et al., "Reinforcement Learning with Unsupervised Auxiliary Tasks" (ICLR 2017). https://arxiv.org/abs/1611.05397
15. Srinivas, Laskin, Abbeel, "CURL: Contrastive Unsupervised Representations for RL" (ICML 2020). https://arxiv.org/abs/2004.04136
16. Stooke, Lee, Abbeel, Laskin, "Decoupling Representation Learning from Reinforcement Learning" (ICML 2021). https://proceedings.mlr.press/v139/stooke21a.html
17. Ha, Schmidhuber, "Recurrent World Models Facilitate Policy Evolution" / "World Models" (2018). https://arxiv.org/abs/1809.01999
18. Parisi et al., "The Unsurprising Effectiveness of Pre-Trained Vision Models for Control" (ICML 2022). https://proceedings.mlr.press/v162/parisi22a.html
19. van den Oord, Li, Vinyals, "Representation Learning with Contrastive Predictive Coding" (2018). https://arxiv.org/abs/1807.03748
20. Wu et al., "Compressed Video Action Recognition" (CVPR 2018). https://arxiv.org/abs/1712.00636
21. Bitmovin probe-encoding patents (per-title encoding with fast probe encodes). https://patents.justia.com/assignee/bitmovin-gmbh
