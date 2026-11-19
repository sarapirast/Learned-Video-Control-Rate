# Exp 4 R3 (k5, val): PPO from the BC actor (exp_next/exp4/report_r3.py)

Pre-registration: exp_next/exp5/PREREG_BC.md REVISION 4. Paired on (GOP, level), seeds averaged per episode, 95% clip bootstrap ('*' excludes 0), level-24 hole excluded. Encoders: x264, x265.

Runs: **R3** = R2's recipe + o[2] masked + mean[t] (real-valued, before final4's rounding) + bit cap + 20k-step critic warm-up + actor from BC. **R2c (control)** = R3's exact setup, actor from rl.py's standard residual init instead of BC (its warm-up freezes that actor, so 160k actor-update steps vs R2's 180k). R2 = stored R2 (o[2] present, no mean[t], no bit cap, no warm-up). o[5..8] are live in all three (only BC training masked them). Hence R3 - R2c = the BC-start effect; R2c - R2 = what the setup changes cost on their own (the handicap BC has to make up).

## GATE: R3 - final4, pooled

- +0.128 [+0.050, +0.216] * (n 1098) -> **PASS** (point >= +0.03 and CI lower bound > 0)
- x265 bar = final4 + per-qbin shift (Exp 5a REVISION 4, val +0.153 vs final4): R3 - (final4 + shift) +0.037 [-0.000, +0.071]; R3 - final4 (x265) +0.190 [+0.071, +0.324] *; (final4 + shift) - final4 on these episodes +0.153 [+0.045, +0.275] *

## Comparisons per encoder

| comparison | x264 | x265 | pooled |
|---|---|---|---|
| R3 - final4 | +0.066 [+0.014, +0.122] * | +0.190 [+0.075, +0.324] * | +0.128 [+0.051, +0.219] * |
| R3 - R2c = effect of the BC start | +0.118 [+0.080, +0.160] * | +0.143 [+0.094, +0.195] * | +0.131 [+0.087, +0.173] * |
| R2c - R2 = cost of R3's setup changes alone | -0.066 [-0.109, -0.035] * | +0.014 [-0.002, +0.031] | -0.026 [-0.048, -0.004] * |
| R3 - R2 | +0.052 [+0.025, +0.082] * | +0.158 [+0.101, +0.212] * | +0.105 [+0.067, +0.142] * |
| R2c - final4 | -0.053 [-0.083, -0.022] * | +0.047 [-0.029, +0.142] | -0.003 [-0.047, +0.050] |
| R2 - final4 | +0.014 [-0.030, +0.060] | +0.032 [-0.049, +0.119] | +0.023 [-0.030, +0.088] |
| R3 180k - R3 60k | +0.069 [+0.044, +0.098] * | +0.042 [+0.016, +0.068] * | +0.056 [+0.035, +0.077] * |

Per seed (R3 - final4 / R3 - R2c): s0 +0.130 / +0.132; s1 +0.115 / +0.105; s2 +0.139 / +0.155
Cut/gradual vs stable (R3 - final4): cut/gradual +0.034 [-0.123, +0.265] (n 173); stable +0.146 [+0.076, +0.233] * (n 925)

## Decomposition (seed-level episodes; offset = QP - final4's QP, includes mean[t])

Signed spend error < 0 = under budget. Going over costs 2-3x more than going under (Exp 1 slope), so landing under more often can be a cheaper mistake; read % over together with signed and p90 error.

| enc   | method   |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |   mean offset |   mean |offset| |
|:------|:---------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|--------------:|----------------:|
| x264  | R2       | 1644 |  -0.1   |  0.063 | -0.163 |          1.874 |         4.945 |         -0.219 |   45.62  |         0.037 |           1.017 |
| x264  | R2c      | 1644 |  -0.166 |  0.024 | -0.19  |          1.942 |         5.589 |          0.337 |   62.53  |        -0.463 |           0.963 |
| x264  | R2c@60k  | 1644 |  -0.235 |  0.012 | -0.246 |          3.192 |        10.079 |         -1.284 |   57.847 |        -0.583 |           1.164 |
| x264  | R3       | 1644 |  -0.048 |  0.108 | -0.156 |          2.021 |         4.709 |         -0.744 |   27.311 |        -0.4   |           1.618 |
| x264  | R3@60k   | 1644 |  -0.117 |  0.061 | -0.178 |          2.358 |         5.87  |         -1.029 |   34.915 |        -0.819 |           1.287 |
| x265  | R2       | 1650 |  -0.223 | -0.06  | -0.163 |          2.004 |         5.43  |         -0.805 |   40.485 |        -0.142 |           1.035 |
| x265  | R2c      | 1650 |  -0.209 | -0.041 | -0.168 |          1.755 |         4.791 |         -0.052 |   56.485 |        -0.695 |           1.095 |
| x265  | R2c@60k  | 1650 |  -0.19  | -0.018 | -0.172 |          1.75  |         4.711 |          0.013 |   59.152 |        -0.833 |           0.916 |
| x265  | R3       | 1650 |  -0.066 |  0.08  | -0.146 |          2.244 |         4.944 |         -1.605 |   16.242 |        -0.276 |           1.287 |
| x265  | R3@60k   | 1650 |  -0.108 |  0.041 | -0.148 |          2.173 |         5.75  |         -1.298 |   33.939 |        -0.33  |           1.013 |
| x264  | final4   | 1644 |  -0.113 |  0.072 | -0.185 |          1.84  |         3.7   |          0.413 |   55.657 |       nan     |         nan     |
| x265  | final4   | 1650 |  -0.256 | -0.085 | -0.171 |          1.627 |         3.448 |          0.344 |   50.364 |       nan     |         nan     |

