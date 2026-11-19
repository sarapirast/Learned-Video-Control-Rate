# Exp 4 R3 (k5, val): PPO from the BC actor (exp_next/exp4/report_r3.py)

Pre-registration: exp_next/exp5/PREREG_BC.md REVISION 4. Paired on (GOP, level), seeds averaged per episode, 95% clip bootstrap ('*' excludes 0), level-24 hole excluded. Encoders: x264.

Runs: **R3** = R2's recipe + o[2] masked + mean[t] (real-valued, before final4's rounding) + bit cap + 20k-step critic warm-up + actor from BC. **R2c (control)** = R3's exact setup, actor from rl.py's standard residual init instead of BC (its warm-up freezes that actor, so 160k actor-update steps vs R2's 180k). R2 = stored R2 (o[2] present, no mean[t], no bit cap, no warm-up). o[5..8] are live in all three (only BC training masked them). Hence R3 - R2c = the BC-start effect; R2c - R2 = what the setup changes cost on their own (the handicap BC has to make up).

## GATE: R3 - final4, pooled

- +0.066 [+0.013, +0.122] * (n 548) -> **PASS** (point >= +0.03 and CI lower bound > 0) -- PARTIAL: not all encoders in yet, not the gate

## Comparisons per encoder

| comparison | x264 | pooled |
|---|---|---|
| R3 - final4 | +0.066 [+0.012, +0.124] * | +0.066 [+0.009, +0.123] * |
| R3 - R2c = effect of the BC start | +0.118 [+0.079, +0.162] * | +0.118 [+0.079, +0.161] * |
| R2c - R2 = cost of R3's setup changes alone | -0.066 [-0.106, -0.033] * | -0.066 [-0.104, -0.035] * |
| R3 - R2 | +0.052 [+0.025, +0.081] * | +0.052 [+0.025, +0.082] * |
| R2c - final4 | -0.053 [-0.083, -0.022] * | -0.053 [-0.084, -0.024] * |
| R2 - final4 | +0.014 [-0.034, +0.056] | +0.014 [-0.031, +0.056] |
| R3 180k - R3 60k | +0.069 [+0.044, +0.099] * | +0.069 [+0.045, +0.097] * |

Per seed (R3 - final4 / R3 - R2c): s0 +0.047 / +0.108; s1 +0.037 / +0.062; s2 +0.114 / +0.185
Cut/gradual vs stable (R3 - final4): cut/gradual -0.009 [-0.142, +0.124] (n 86); stable +0.080 [+0.027, +0.136] * (n 462)

## Decomposition (seed-level episodes; offset = QP - final4's QP, includes mean[t])

Signed spend error < 0 = under budget. Going over costs 2-3x more than going under (Exp 1 slope), so landing under more often can be a cheaper mistake; read % over together with signed and p90 error.

| enc   | method   |    n |   score |     A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |   mean offset |   mean |offset| |
|:------|:---------|-----:|--------:|------:|-------:|---------------:|--------------:|---------------:|---------:|--------------:|----------------:|
| x264  | R2       | 1644 |  -0.1   | 0.063 | -0.163 |          1.874 |         4.945 |         -0.219 |   45.62  |         0.037 |           1.017 |
| x264  | R2c      | 1644 |  -0.166 | 0.024 | -0.19  |          1.942 |         5.589 |          0.337 |   62.53  |        -0.463 |           0.963 |
| x264  | R2c@60k  | 1644 |  -0.235 | 0.012 | -0.246 |          3.192 |        10.079 |         -1.284 |   57.847 |        -0.583 |           1.164 |
| x264  | R3       | 1644 |  -0.048 | 0.108 | -0.156 |          2.021 |         4.709 |         -0.744 |   27.311 |        -0.4   |           1.618 |
| x264  | R3@60k   | 1644 |  -0.117 | 0.061 | -0.178 |          2.358 |         5.87  |         -1.029 |   34.915 |        -0.819 |           1.287 |
| x264  | final4   | 1644 |  -0.113 | 0.072 | -0.185 |          1.84  |         3.7   |          0.413 |   55.657 |       nan     |         nan     |

