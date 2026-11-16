# Live-stream rate control with reinforcement learning: full write-up (D38–D42)

**Scope.** Every experiment here uses **dataset v1** (Aayush's dataset), with both encoders (x265 and x264). These results are kept apart from the original-dataset results and are not part of the milestone report.

**Contents**
1. Background: what happened before the live-stream work
2. Why live streaming is a better problem for RL
3. Data: video and network
4. The live-stream environment, in detail
5. Baselines
6. How the RL works
7. Experiments and results, D38 to D42
8. Problems we found and fixed along the way
9. All techniques used
10. Conclusions
11. Limits
12. Compute, code and file map

---

## 1. Background: what happened before the live-stream work

### 1.1 Per-GOP RL (D1–D33): early wins that did not survive

The first phase of the project trained RL to pick a QP offset for every frame of a single 30-frame GOP under a bit budget. Methods included BC, CQL→PPO, Lagrangian and PID-Lagrangian PPO, DQN, MPC and model-based pre-training, with lookahead k = 0–29 frames. Several of these looked strong at first. Three problems explained most of that:

1. **The score rewarded leaving budget unused.** The score was "bit saving at equal PSNR − 2 × % over budget", with no cost for unused budget. When we checked (D33), learners spent only **78–96 % of the budget** and delivered **0.3–1.2 dB lower PSNR** than a static plan, yet still showed a positive "saving".
2. **Information leaks.** The budget came from the GOP's own constant-QP spend, and the base-QP estimate used a first pass over the whole GOP. A real live encoder knows neither.
3. **A weak comparison controller.** Aayush rebuilt the setting without leaks (dataset v1, clip-level budgets, his dB metric) and retuned his online controller (final3). After that, **no per-GOP learner beat final3**.

### 1.2 Stream-level RL without a network (D34–D36): small, real, fragile gains

We moved RL to a decision a per-GOP rule cannot make: how to share **one** budget across the GOPs of a stream.

- **D34.** RL picks each GOP's constant QP as an offset of −6..+6 on a remaining-budget rule, scored with Aayush's dB metric.
  - PPO and BC→PPO beat the val-tuned rule by **+0.12 to +0.21 dB** (CIs above 0, both encoders). They closed 16–33 % of the gap to a hindsight plan.
  - BC alone was worse than the rule.
- **D35.** Against the encoders' own stream rate control, RL beat ABR+VBV (+0.44 / +0.17 dB), tied x265 two-pass, and lost to x264 two-pass by 0.27 dB.
  - On new films (Elephants Dream, Tears of Steel) the gain shrank to **+0.03 to +0.07 dB** at n = 8, and was not significant on x265.
- **D36.** LSTM policies and quality feedback added nothing consistent. Training on variable stream lengths helped long streams a little.
- **Throughout**, the offline best constant QP still tied or beat every live method.

### 1.3 Why RL had little room there

- **With a fixed budget and no network, the best policy is nearly "find the right QP and hold it."** Constant QP is close to optimal for typical rate-quality curves.
- **A simple rule already does that well.** It keeps recalibrating its rate model from the GOPs already coded, and it gets most of the way.
- **Nothing is uncertain and no mistake is costly.** A slightly wrong QP costs a little quality and can be corrected next GOP. There is no hard constraint and no hidden, changing quantity to react to.
- **So RL's possible advantage is small,** and small gains are easily lost on new content.

---

## 2. Why live streaming is a better problem for RL

Live streaming changes the problem in three ways:

1. **The network rate changes every second,** and the sender only learns the rate after sending.
2. **There is a hard latency limit.** Bits wait in a sender buffer. If the buffer grows past the latency cap, the viewer's video **freezes (stalls)** until it drains.
3. **The costs are asymmetric.** Aiming too high risks a stall, which is expensive (0.5 dB of score per 1 % of time stalled). Aiming too low wastes picture quality.

So the controller must decide each second under uncertainty, with an expensive failure mode and effects that carry forward through the buffer. Hand-made rules handle this crudely: a fixed safety margin, a fixed reaction speed. Learning *when* to take risk and *when* to back off is what RL is good at.

---

## 3. Data

### 3.1 Video: dataset v1 (Aayush's; read-only)

| Property | Value |
|---|---|
| Clips | 109 clips from 78 sources (Xiph test sequences, Blender films, YouTube UGC) |
| GOPs | 1,042 GOPs of 30 frames (1 s each): **625 train / 152 val / 265 test** (66 / 16 / 27 clips), split by source group so no source appears in two splits |
| Format | 320×180 |
| Encoder settings (frozen) | preset medium, IPPP, closed GOPs, AQ / mb-tree / psy off |
| Per-GOP curves | For every GOP, real constant-QP encodes at QP 18–50 give bits and **luma** PSNR (from Aayush's per-frame table `rd_frames.parquet`) |
| Budgets | Clip-level budgets from `budgets.csv`: at level q0 ∈ {24, 30, 36, 42}, the clip's mean constant-QP bits per GOP. No leak: a GOP's budget does not come from its own encode. |

**Evaluation streams.** Each case is a stream plus a budget level q0 plus a budget scale s ∈ {0.85, 1.0, 1.18}. The budget is s × the sum of the GOPs' v1 budgets.
- **test (n = 8 GOPs):** every 8-GOP window of each test clip, plus 100 mixed streams (8 GOPs from different clips): **2,172 cases**.
- **test16 (n = 16 GOPs):** 150 playlists (consecutive GOPs of a clip, continuing into another clip) × 12 budgets: **1,800 cases**.
- **val:** **1,704 cases**, used only to tune baselines.
- **Training:** random training streams of 4–24 GOPs, q0 drawn from 24–44, s from U(0.8, 1.25). The policy never observes q0 or s.

**New films (generalisation check, D35/D39).** Elephants Dream and Tears of Steel, which are not in v1's training data. 6 segments per film, at n = 16 and n = 32 GOPs. Their PSNR is 6:1:1 YUV rather than luma, so their dB values aren't directly comparable with the v1 numbers.

### 3.2 Network

**Simulated network (default).** For GOP i the network can send R_i = m_i × B / n bits.
- log m_i follows an AR(1) process: ρ = 0.8, σ = 0.3.
- m is normalised so its mean over the stream is 1, i.e. the network carries exactly the budget on average.
- Each evaluation case gets its own fixed channel, seeded from the case, so every method faces the same network.

**Real network: Belgium 4G/LTE throughput logs** (van der Hooft et al., Ghent University).
- 40 logs of 4G throughput recorded from moving users (foot, bicycle, bus, tram, train, car).
- We kept only the throughput column and dropped the GPS columns.
- **Split by file** with a fixed hash: **19 train logs (9,095 s), 10 val (4,959 s), 11 test (3,982 s)**.
- For each case we take a random window of the right length, normalise it to mean 1 like the simulated channel, and floor it at 5 % of the mean.
- These traces are much rougher than the simulation: the standard deviation of the 1-s log-rate change is **1.2 vs 0.3**, with deep fades.

---

## 4. The live-stream environment, in detail (`rclib/bufenv.py`)

**Decision.** Once per GOP (once per second), the controller picks that GOP's constant QP as an **offset −6..+6** on a base rule's QP. It is clipped to QP 18–50.

**Outcome.** The GOP's bits and luma PSNR are looked up in its real constant-QP curve. Because the GOPs are closed, really encoding the stream with those QPs gives exactly the same numbers; D40 checked this.

**Buffer dynamics,** per second i:
```
F ← F + bits_i                      # GOP i enters the sender buffer
F ← F − min(F, R_i)                 # the network drains up to R_i
if F > CAP:                         # latency cap: CAP = D_CAP × B / n  (D_CAP = 1 s at the mean rate)
    stall_i = (F − CAP) / R_i       # seconds the viewer waits while the excess drains
    F ← CAP
```
The controller sees R_i only **after** GOP i was sent.

**Score** (higher is better; dB):
```
score = dPSNR_B − 0.17 × (% over budget) − 0.5 × (% of the stream's duration stalled)
dPSNR_B = pooled luma PSNR of the stream − PSNR of the stream's own constant-QP curve at exactly the budget B
```
- The first two terms are Aayush's metric.
- **The stall weight of 0.5 dB per 1 % was fixed before any result was seen.** It makes a stall cost more than overshooting. The robustness sweep varies it (0.25 and 1.0).

**Lookahead L = 2.** The controller sees cheap first-pass costs of the current GOP and the next 2 GOPs, never their real bits or quality.

**Statistics.**
- Every comparison is paired on identical cases: same stream, same budget, same network.
- The 95 % interval is a **cluster bootstrap** over source groups, 4,000 resamples; each mixed stream is its own cluster.
- Learners are trained with **3 seeds**, and their per-case scores are averaged before comparing.

---

## 5. Baselines

Every baseline is **tuned on val, separately for each encoder and each network type**, before any learner result was looked at.

### 5.1 Rules

| Name | Logic | Tuned parameters |
|---|---|---|
| **rule** (D34) | Remaining-budget rule. Picks the QP whose rate model spends margin × (remaining budget) over the remaining GOPs. The rate model is bits = c × first-pass × 2^(−(QP − 30)/qpd), with c recalibrated online from coded GOPs. **Ignores the buffer.** | margin, slope qpd, prior weight cw |
| **vbv** (D38) | rule, then raises QP so the rate model predicts buffer + bits − R̂ ≤ ψ × CAP. R̂ is an exponential moving average (α) of observed network rates. This copies the logic of encoder VBV. | ψ, α |
| **vbv2** (D39, main baseline) | Buffer-tracking rule. Target bits = R̂ × exp(−κ × observed volatility) + β × (ψ × CAP − F), capped at CAP + R̂ − F, then converted to a QP with the calibrated rate model. Optional remaining-budget clamp (rmargin). It contains vbv as a special case. | ψ, β, κ, α, rmargin: **672-point grid** |
| **mpc** (D39) | vbv2 plus a planner. For each offset −6..+6, hold that QP for H GOPs, simulate the buffer on **64 sampled network paths from the true network model**, and pick the offset maximising −γ × QP − expected stall cost. On traces it gets an AR(1) model fitted on the training traces (ρ 0.31, σ 0.47). | γ, H |
| **const** | Best single constant QP for the whole stream, chosen in hindsight. **Offline and buffer-blind.** | none |

**Tuned values at L = 2:**

| | vbv2 (ψ, β, κ, α, rmargin) | mpc (γ, H) | rule margin |
|---|---|---|---|
| x265, simulated | 1.0, 0.6, 1.5, 1.0, 0.9 | 0.02, 2 | 0.75 |
| x265, 4G traces | 0.2, 0.6, 0.5, 0.6, 0.9 | 0.0025, 4 | 0.70 |
| x264, simulated | 0.7, 0.6, 0.5, 0.6, 0.9 | 0.0025, 2 | 0.75 |
| x264, 4G traces | 0.35, 1.0, 1.5, 1.0, 0.9 | 0.0025, 2 | 0.70 |

On traces vbv2 tunes itself to be much more cautious, with low ψ (target buffer level).

### 5.2 The encoders' own rate control (D40; real encodes)

- **E2: encoder ABR+VBV for the whole stream.**
  - One real x264/x265 encode of the stream with target = f × the mean network rate, maxrate = target, and a 1-s VBV buffer.
  - It doesn't see the network second by second, as with a fixed-bitrate live encoder.
  - f is tuned on val over {0.2, …, 1.0}. We also report **hindsight E2**, with f picked on the test set itself, as an upper bound for this method.
- **E3: encoder ABR+VBV per second.**
  - Each second, the encoder must hit a bit target (maxrate = bufsize = target) set by vbv2 (enc_vbv2) or by ppo_v2 (enc_ppo_v2).
  - Measured bits feed the buffer simulation.

### 5.3 Hindsight oracle (D41; upper bound)

- **What it knows:** each case's **whole future network** and **every GOP's curve**. It picks one QP per GOP to maximise the exact score.
- **Search:**
  1. Backward dynamic programming over the buffer level (129 bins), once for each of 36 bit weights × 8 stall weights (288 combinations). Each resulting policy is replayed exactly from an empty buffer.
  2. Starting points: every constant QP, plus the actual QP sequences of vbv2, mpc and ppo_v2 (3 seeds) on that case.
  3. Exact local search from the best 4 starting points: ±1 / ±2 moves on one GOP, and paired +1/−1 moves on two GOPs, until nothing improves.
- **Checks:**
  - Its scorer reproduces every stored vbv2 / mpc / ppo_v2 score exactly (max difference 1e-14).
  - It beats every seeded method on 100 % of cases.
- **Caveat:** no live controller can reach it, because it also knows future content.

---

## 6. How the RL works

### 6.1 ppo_v2 (D39): the main method

**Residual design.** vbv2 proposes a QP each second, and the policy chooses an **offset −6..+6** (13 discrete actions) on top. The policy therefore starts from a strong, safe behaviour and only has to learn *corrections*.

**Observation** (all features scaled to about ±1):
- **Stream state:** position in the stream, GOPs left and log stream length, budget spent vs expected, the rate model's calibration error, and the last action.
- **Content:** first-pass cost of the current GOP and the next 2 (lookahead L = 2), relative to the GOPs seen so far, plus simple scene features.
- **Quality feedback:** the last GOP's PSNR vs the stream's pooled PSNR so far, the pooled PSNR so far, and the last GOP's bits vs its equal share.
- **Network and buffer:**
  - buffer fullness (F / CAP);
  - the last observed network rate and its smoothed average (log2, relative to the mean);
  - % of time stalled so far, and whether the last second stalled;
  - how far vbv2's QP is from the buffer-blind rule's (a measure of buffer pressure);
  - the latency cap.

**Reward.** The final stream score, given once at the end (γ = 1, no shaping), so the policy optimises exactly what we report.

**Training.**
- PPO (stable-baselines3), MLP policy and value nets with two 128-unit ReLU layers.
- **2 M steps**, 16 parallel environments, rollout 128, batch 256, 5 epochs, learning rate 3e-4, entropy 0.01, GAE λ 0.95.
- Stream length drawn from **4–24 GOPs** each episode; network drawn fresh each episode.
- **On the 4G setting, the policy is trained on the 4G training traces with the trace-tuned vbv2.** On the simulated setting, it is trained on the simulated network.

**Evaluation.** Deterministic (most likely action), on the fixed test cases.

**What it learns** (from the use and stall statistics): it spends more of the network than vbv2 when the buffer is low and the network is steady, and backs off earlier than vbv2 when the network is turning down or the buffer is filling.

### 6.2 il_ppo (D42): imitation of the oracle, then PPO

1. **Teacher.** At any state of a training episode (GOP i, buffer F, QPs used so far), the teacher replays all 288 D41 DP policies from that exact state using the **true future network and curves**. It keeps the best full plan by exact score, and also keeps its previous plan if that plan is still consistent with what happened. The teacher's next QP, minus vbv2's QP, clipped to ±6, is the label.
2. **DAgger, 4 rounds × 1,000 episodes.** In round k, each step follows the teacher with probability 0.5^k, otherwise the student. Every visited state is labelled by the teacher, and all labels are aggregated (about 56,000).
   - After each round the student is trained by maximum likelihood (Adam 1e-3, batch 512, 10 epochs).
   - **The student sees only the normal ppo_v2 observation,** never the future.
3. **Critic warm-up.** 1,000 episodes with the student's own policy. The value network alone is fitted to the final scores (20 epochs).
4. **PPO fine-tuning.** 1 M steps at learning rate 1e-4, entropy 0.003, from the imitation policy. Everything else matches ppo_v2.

`il` is the policy after step 2; `il_ppo` is the policy after step 4.

### 6.3 Other D42 variants (no gain)

- **ppo_mix: one policy for both network types.**
  - Each training episode draws either a simulated network with randomised settings (ρ ~ U(0.5, 0.95), σ ~ U(0.1, 0.6)) or a 4G training window, 50/50.
  - The base rule switches to that network type's tuned vbv2.
- **ppo_mixh:** ppo_mix, plus the last 8 observed network rates in the observation.
- **ppo_wide:** ppo_v2 with a wider range of offsets, −24..+6 (31 actions).
- **il_w / il_w_ppo:** the imitation pipeline with the wide range.

---

## 7. Experiments and results

All scores are dB, and higher is better. Tables show **v1 test, n = 8** unless marked. In the tables:
- **use** = bits sent as a share of the budget;
- **stall %** = share of stream time frozen;
- **streams w/ stall** = share of cases with any stall.

### 7.1 D38: first live-stream run

**Setup.**
- Simulated network, rule / vbv / const baselines.
- PPO on the vbv rule at L = 0 and L = 2, 3 seeds.

**Results.**
- PPO beat vbv by **+0.56 [+0.48, +0.68] (x265)** and **+0.43 [+0.37, +0.50] (x264)**, and on n = 16 playlists by +0.48 / +0.44. PPO stalled less (x265: 0.44 % vs 0.74 % of the time).
- vbv beat the buffer-blind rule by +0.4 to +2.6 dB, so watching the buffer matters a lot.
- The offline best constant QP stalls **10–25 %** of the time, which shows that ignoring the network is disastrous here.

**What it turned out to mean.** Most of this margin came from a weak rule (see D39).

### 7.2 D39: a much stronger rule, RL on top of it, and robustness

**Stronger baselines first.**
- vbv2 beat vbv by **+0.48 (x265) / +0.50 (x264)**.
- The D38 policy was no longer significantly better than vbv2 at n = 8: x265 +0.08 [−0.03, +0.24], x264 −0.06 [−0.18, +0.08].
- **Lesson: RL has to be built on the strong rule, not on a weak one.** That gave **ppo_v2**.

**Main table (simulated network, v1 test, n = 8):**

| Method | x265 score | use | stall % | streams w/ stall | x264 score | use | stall % |
|---|---|---|---|---|---|---|---|
| const (offline) | −5.73 | 97 % | 11.0 | 74 % | −5.44 | 97 % | 10.4 |
| rule | −2.81 | 75 % | 2.14 | 27 % | −3.01 | 75 % | 2.15 |
| vbv | −2.24 | 74 % | 0.74 | 12 % | −2.51 | 73 % | 0.74 |
| **vbv2** | **−1.77** | 84 % | 0.97 | 18 % | **−2.02** | 84 % | 1.16 |
| mpc | −1.79 | 89 % | 1.03 | 20 % | −2.04 | 85 % | 1.05 |
| ppo (D38, on vbv) | −1.69 | 79 % | 0.44 | 8 % | −2.08 | 79 % | 0.68 |
| **ppo_v2** | **−1.33** | 87 % | 0.61 | 12 % | **−1.67** | 86 % | 0.82 |

**ppo_v2 vs vbv2:**
- v1 test: x265 **+0.436 [+0.366, +0.539]**, x264 **+0.347 [+0.262, +0.435]**.
- n = 16 playlists: **+0.576** on both.
- **ppo_v2 vs mpc:** +0.459 / +0.370.
- **Where the gain comes from:** ppo_v2 sends about **3 % more of the budget** *and* stalls less (x265 0.61 % vs 0.97 %; streams with any stall 12 % vs 18 %). It improves quality and safety at the same time.

**Robustness (ppo_v2 vs vbv2, v1 test, one setting changed at a time, everything re-tuned and retrained):**

| Setting | x265 | x264 |
|---|---|---|
| Default (σ 0.3, cap 1 s, stall weight 0.5) | +0.44 | +0.35 |
| Calmer network, σ 0.15 | +0.43 | +0.37 |
| Rougher network, σ 0.5 | +0.52 | +0.41 |
| Tighter latency cap, 0.5 s | +0.62 | +0.55 |
| Looser latency cap, 2 s | +0.47 | +0.30 |
| Stalls cheaper, 0.25 dB per % | +0.46 | +0.33 |
| Stalls dearer, 1.0 dB per % | +0.53 | +0.43 |
| **Real 4G traces** | **+0.23 [+0.06, +0.44]** | **+0.41 [+0.26, +0.60]** |
| New films, n = 16 | +0.19 | +0.23 |
| New films, n = 32 | +0.30 | +0.40 |

- **Every CI is above 0.** All five pre-registered hypotheses (HC1–HC5) passed on both encoders.
- The gain is largest when the latency cap is tight, where buffer management matters most.
- **Against mpc on new films:** +0.12 / +0.15 at n = 16; at n = 32, +0.24 on x265 and +0.03 [−0.13, +0.20] on x264, which is not significant.

**4G traces, v1 test, n = 8:**

| Method | x265 score | use | stall % | x264 score | use | stall % |
|---|---|---|---|---|---|---|
| const (offline) | −14.93 | 97 % | 29.4 | −14.70 | 97 % | 28.9 |
| rule | −7.53 | 70 % | 10.9 | −7.69 | 70 % | 10.8 |
| vbv2 | −3.26 | 76 % | 2.11 | −3.90 | 75 % | 2.41 |
| mpc | −3.50 | 71 % | 2.46 | −3.78 | 78 % | 3.24 |
| ppo_v2 | −3.03 | 81 % | 2.51 | −3.49 | 76 % | 2.44 |

- On traces every method stalls 2–2.5 % of the time, because deep fades can't be predicted.
- RL's gain there comes mostly from **better quality** (it uses more of the network), not from fewer stalls.

### 7.3 D40: real encoders in the loop

The network stays simulated or replayed from traces; **the video is really encoded and decoded** with v1 settings.
- **Cases:** every 3rd case of test and test16 (724 and 600), and of trace test (724).
- **Output:** 44 shards per encoder, plus a 20-task extension for E2.

**E1, replay check.** For 96 cases per set, the QPs that vbv2 and ppo_v2 chose were really encoded. **The result equalled the lookups exactly** on both encoders and all sets. The simulation does not flatter RL.

**ppo_v2 vs E2 (encoder ABR+VBV, whole stream):**

| Setting | E2 target f (val → hindsight) | x265: vs val-tuned E2 | x265: vs hindsight E2 | x264: vs val-tuned E2 | x264: vs hindsight E2 |
|---|---|---|---|---|---|
| n = 8 | 0.9 → 0.9 | +0.41 [+0.16, +0.60] | +0.41 | −0.05 [−0.45, +0.22] | −0.05 (tie) |
| n = 16 | 0.9 → 0.7 | +2.97 | **+1.42 [+1.17, +1.61]** | +2.81 | **+1.11 [+0.84, +1.37]** |
| 4G traces | 0.3 → 0.4 / 0.5 | +2.86 [+2.20, +3.43] | **+2.22 [+1.59, +2.90]** | +3.09 [+2.09, +3.80] | **+2.15 [+1.28, +3.14]** |

- **E2 with target = the mean network rate (untuned) stalls 3.5–25 % of the time.** It needs a very different safety margin in each setting.
- **E2's targets differ by setting:** about 90 % of the mean network rate for short streams, 70 % for playlists and 30–50 % on 4G. **RL and vbv2 adapt online and need no such guess.**

**ppo_v2 vs E3 (encoder hitting vbv2's per-second targets):** x265 +0.49 / +0.77 / trace +0.64; x264 +1.25 / +1.01 / trace +1.99. All CIs are above 0.
- E3 is even worse than vbv2 with constant QP (−0.02 to −1.71). The encoders' 1-s ABR spends bits less efficiently than one constant QP per GOP.

**RL as E3's target setter (enc_ppo_v2 − enc_vbv2):**
- x265: −0.05 / −0.07 / trace −0.81.
- x264: +0.56 / −0.05 / trace +0.34.
- Mixed, mostly about 0. A policy trained to pick QPs does not transfer to setting bit targets, since it was never trained with an encoder in the loop.

### 7.4 D41: hindsight oracle (how much room is left)

| Setting | x265: oracle − vbv2 | x265: ppo_v2 closes | x264: oracle − vbv2 | x264: ppo_v2 closes | mpc closes (x265 / x264) |
|---|---|---|---|---|---|
| Simulated, n = 8 | +1.68 [+1.49, +1.96] | 26 % [23, 29] | +1.92 [+1.73, +2.21] | 18 % [13, 22] | −1 % / −1 % |
| Simulated, n = 16 | +1.74 [+1.56, +1.90] | 33 % [29, 36] | +1.96 [+1.79, +2.09] | 29 % [26, 32] | 5 % / 12 % |
| 4G, n = 8 | +3.03 [+2.63, +3.55] | 8 % [2, 14] | +3.55 [+3.10, +4.10] | 12 % [8, 15] | −8 % / 3 % |
| 4G, n = 16 | +2.69 [+2.44, +2.90] | 7 % [1, 13] | +3.24 [+2.98, +3.47] | 8 % [4, 11] | −9 % / 6 % |

"Closes" = share of the oracle − vbv2 gap, (method − vbv2) / (oracle − vbv2).

- **There is a lot of headroom,** most of it on 4G: 2.7–3.6 dB.
- **Where the gap comes from:** about a third is vbv2's stall penalty. The rest is how quality is spread across the stream, part of which needs future content.

### 7.5 D42: making the RL better

**Design.** Everything matches ppo_v2: same action space (except the wide variants), score, base rule, test cases and 3 seeds. Only the training changes. 24 runs per encoder.

**Debug finding.** With ±6 actions, the oracle teacher's choice fell outside the range on **24 %** of labels: median −3 below vbv2, 5th percentile −15. So the student could not follow the teacher fully. That led to the wide-range variants and the ppo_wide control.

**Paired results vs ppo_v2** (95 % CI, n = 8 / n = 16):

| Comparison | x265 simulated | x265 4G | x264 simulated | x264 4G |
|---|---|---|---|---|
| **il_ppo − ppo_v2** | **+0.07** [+0.03, +0.11] / **+0.08** [+0.02, +0.13] | **+0.26** [+0.14, +0.37] / **+0.09** [+0.02, +0.18] | **+0.10** [+0.06, +0.15] / **+0.05** [+0.01, +0.08] | **+0.15** [+0.04, +0.24] / **+0.14** [+0.06, +0.21] |
| il_w_ppo − ppo_v2 | +0.10 / +0.08 | +0.08 (ns) / +0.13 (ns) | +0.02 (ns) / +0.03 (ns) | +0.02 (ns) / +0.23 |
| ppo_wide − ppo_v2 | −0.07 / −0.00 | −0.09 (ns) / −0.19 | −0.02 (ns) / −0.00 | −0.00 / +0.11 |
| ppo_mix − ppo_v2 | −0.13 / −0.12 | +0.13 / −0.02 (ns) | −0.06 (ns) / −0.14 | −0.02 (ns) / +0.00 |
| ppo_mixh − ppo_mix | −0.03 / +0.00 | −0.09 / +0.00 | −0.02 / +0.01 | −0.05 / +0.11 |

(ns = CI includes 0)

**Imitation alone vs vbv2:** il −1.0 to −3.1 dB (stalls 3.6–9.5 %); il_w −0.7 to −6.2 dB (stalls up to 18 %).

**Share of the oracle gap closed, ppo_v2 → il_ppo:**

| | x265 n = 8 | x265 n = 16 | x264 n = 8 | x264 n = 16 |
|---|---|---|---|---|
| Simulated | 26 → **30 %** | 33 → **38 %** | 18 → **23 %** | 29 → **32 %** |
| 4G traces | 8 → **16 %** | 7 → **10 %** | 12 → **16 %** | 8 → **12 %** |

**What we learned.**
1. **Imitating the oracle, then fine-tuning with PPO, is the best learner.** It wins in **8 of 8 settings, every CI above 0**, using about **1.06 M** network-simulation steps vs ppo_v2's 2 M. The largest gain is on 4G traces (x265 n = 8, +0.26).
2. **Imitation on its own fails.** The student matches the teacher on only **25–42 %** of its training labels, because the teacher's choices depend on the future network and content, which the student can't see. Copying a teacher that sees the future gives a policy that takes risks it can't justify, so it stalls a lot. It is still useful as a **starting point**: PPO then corrects it using the real reward. This is a known effect of imitating a teacher with privileged information.
3. **A wider action range didn't help,** even though the oracle often wants QPs far from vbv2. A live policy can't safely make those big moves without knowing the future.
4. **Training one policy on many network types didn't help.** It costs a little on the simulated network. Our ppo_v2 was already trained on the matching network type.
5. **Giving the policy 8 seconds of network history didn't help.** On these traces, the recent past says little about the next second, beyond what the smoothed average already captures.

---

## 8. Problems we found and fixed along the way

- **D38's weak baseline.** The first +0.5 dB was mostly against an undertuned rule. We built vbv2 and mpc, tuned both on val, and re-did RL on top of vbv2.
- **Environment mismatch in D40.** ppo_v2 had been trained and evaluated with a different smoothing factor for observed network volatility (0.6 on x265) than vbv2's default (0.5). In the first D40 debug run, 4 of 12 lookup cases didn't match D39's stored results. After we fixed the environment construction, all matched exactly.
- **E2 tuning at the edge of its grid.** On traces, val picked the lowest target tried (f = 0.6). We extended the grid to 0.2–0.5; val now picks 0.3, inside the grid. We also added hindsight E2.
- **E2 tuned on the wrong stream length.** The n = 16 E2 had been tuned on n = 8 val (f 0.9 vs the best 0.7 at n = 16). The fair n = 16 comparison is against hindsight E2: +1.42 / +1.11, not +2.97 / +2.81.
- **Wrong claim corrected.** I first said ppo_v2 was trained only on the simulated network. In fact the 4G policy was trained on the 4G training traces. This changed the motivation for ppo_mix.
- **Oracle teacher clipped by the action range.** 24 % of labels were clipped at ±6, so we added the wide variants and a matching PPO control.
- **Real encoders ≠ curves at first (D35, earlier).** psy was on in the stream encodes but off in the v1 curves. After matching settings, real encodes reproduced the curves exactly.

---

## 9. All techniques used

**Problem and environment**
- A live-streaming model: a sender buffer with a latency cap, a network revealed after each second, and an explicit stall penalty in a dB score.
- Two network types: an AR(1) simulation, and real Belgium 4G/LTE traces split by file.
- Closed-GOP curve lookups, checked against real encodes.

**Baselines (all val-tuned)**
- A remaining-budget rule.
- A VBV-style rule.
- A 5-parameter buffer-tracking rule (vbv2, 672-point grid).
- Stochastic model-predictive control with the true network model (mpc).
- The best offline constant QP.
- The encoders' ABR+VBV, both whole-stream and per-second, with val-tuned and hindsight-tuned targets.

**RL**
- PPO with a residual action on a strong rule (±6 QP).
- Lookahead of 2 GOPs (first-pass only).
- Training on variable stream lengths (4–24).
- Terminal reward equal to the evaluation score.
- 3 seeds.

**Measuring headroom**
- A hindsight oracle: dynamic programming over the buffer level, with grids of bit and stall weights, plus exact local search. It gives a "share of the gap closed" measure.

**RL improvements tried**
- **Worked:** DAgger imitation of the oracle, then a critic warm-up and PPO fine-tuning (il_ppo).
- **Did not help:** network randomisation, a network-history observation, a wider action range.

**Evaluation**
- Paired comparisons on identical cases.
- 95 % cluster bootstrap by source group.
- Robustness sweep over network roughness, latency cap and stall weight.
- Real 4G traces.
- New films at longer stream lengths.
- Real encodes.

---

## 10. Conclusions

1. **RL helps when the network is live.** PPO on top of a carefully tuned buffer rule improves the score by **+0.35 to +0.58 dB** on dataset v1, **while freezing less**. It held in every setting we tried (network roughness, latency cap, stall weight, real 4G traces, new films), always with CIs above 0.
2. **It beats the encoders' own live rate control in real encodes:** by **+1.1 to +1.4 dB** on long streams and **about +2.2 dB** on real 4G traces, even when the encoder's target is chosen in hindsight. On short streams it gains +0.4 dB on x265 and ties x264.
3. **RL works best as a correction to a good rule,** not as a replacement. RL on a weak rule only looked good because the rule was weak.
4. **Imitating a hindsight oracle, then fine-tuning with PPO, is the best training recipe we found:** another **+0.05 to +0.26 dB** over PPO alone, in all 8 settings. Imitation alone fails because the oracle's decisions rely on the future.
5. **There is still room.** The best learner closes 23–38 % of the gap to the oracle on the simulated network and 10–16 % on 4G traces. Part of the remaining gap needs knowledge of future content and network, which no live controller has.
6. **Why this differs from the earlier non-live results:** with a fixed budget and no network, "find the QP and hold it" is nearly optimal and a rule does it well. Live streaming adds uncertainty and an expensive failure mode, which is where learning when to take risk pays off.

## 11. Limits

- **The network is simulated or replayed.** We never streamed over a live connection to real players. Player-side buffering and ABR ladders are not modelled.
- **One decision per second (constant QP per GOP).** Frame-level rate control inside a GOP is not modelled on either side.
- **We chose the score weights.** The stall weight (0.5 dB per %) and the 1-s cap are our choices. The sweep varied both, and the result held.
- **The traces are one dataset:** 40 Belgian 4G logs (11 in test), with deep fades every method struggles with.
- **The new-film set is small:** 12 segments from 2 films, not independent sources.
- **Low resolution:** dataset v1 is 320×180.
- **The oracle is an upper bound,** not a reachable target.
- **On short streams, x264's own live mode ties RL.**

## 12. Compute, code and file map

**Compute** (all CPU, account rashidin_1753, 2 CPU / 8 GB per task):

| Experiment | Tasks | Time per task |
|---|---|---|
| D38 | 16 | ~14 min |
| D39 | 66 | 5–30 min |
| D40 | 92 + 20 | real encodes, ~20 s per n = 8 case on x265 |
| D41 | 36 | 2–6 min |
| D42 | 52 | 13–45 min |

Each step had its own debug-partition test first.

**Code**

| File | Purpose |
|---|---|
| `rclib/bufenv.py` | Live-stream environment: network, buffer, stalls, score, rule / vbv / vbv2 / mpc |
| `experiments/buffer_rl.py` | D38/D39: baselines, tuning, PPO / ppo_v2, robustness sweep, new films, report |
| `experiments/buffer_real.py` | D40: real-encoder E1 / E2 / E3 |
| `experiments/buffer_oracle.py` | D41: hindsight oracle and gap-closed report |
| `experiments/buffer_rl2.py` | D42: ppo_mix / ppo_mixh / ppo_wide / il / il_w |
| `tools/submit_buffer*.sh`, `tools/*_task.sbatch`, `runs/buffer*.txt` | Job scripts and run lists |

**Reports** (`results/v1_buffer/<codec>/`)
- `buffer_report.md`: all methods, including D42.
- Sweep subfolders: `sig0.15/`, `sig0.5/`, `cap0.5/`, `cap2/`, `lam0.25/`, `lam1/`, `trace/`.
- `real/` and `trace/real/`: D40.
- `oracle/` and `trace/oracle/`: D41 and D42 gap-closed.

**Logs**
- `docs/JOURNAL.md`, `docs/DECISIONS.md` (D38–D42), `docs/JOBS.md`.
- Plain-language summary: `docs/LIVE_STREAM_FINDING_SIMPLE.md`.
