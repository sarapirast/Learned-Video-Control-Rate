# D40 live channel with the real encoder in the loop (x265, trace)

Channel Belgium 4G/LTE traces (test files), cap 1.0 s, stall weight 0.5 dB per %. Score = luma dPSNR_B - 0.17 x %over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.

- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).
- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer (E2, channel-blind).
- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV (E3, channel-aware).

E2 target fraction tuned on val (f 0.2: -7.604, f 0.3: -6.814, f 0.4: -7.067, f 0.5: -7.824, f 0.6: -9.007, f 0.7: -10.916, f 0.8: -13.279, f 0.9: -16.331, f 1: -20.273): f = 0.3. enc_vbv_f1 = untuned (target = channel mean).

## v1 test (n = 8, every 3rd case)

E2 on this test set by f: 0.2 -7.607, 0.3 -6.048, 0.4 -5.415, 0.5 -5.544, 0.6 -6.024, 0.7 -6.817, 0.8 -7.944, 0.9 -9.645, 1 -12.218 (hindsight = f0.4).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:------|:-----------|----------:|:---------------------|
| vbv2              |     724 |       -3.488 |    -2.061 | 76.3% | 0%         |     2.853 | 10%                  |
| ppo_v2            |     724 |       -3.192 |    -1.581 | 81.1% | 1%         |     3.216 | 11%                  |
| rp_vbv2           |      96 |       -2.098 |    -1.827 | 80.0% | 0%         |     0.543 | 6%                   |
| rp_ppo_v2         |      96 |       -2.491 |    -1.445 | 83.9% | 1%         |     2.081 | 7%                   |
| enc_vbv_f1        |     724 |      -12.218 |    -0.69  | 97.8% | 27%        |    22.756 | 30%                  |
| enc_vbv2          |     724 |       -3.829 |    -2.424 | 80.7% | 0%         |     2.811 | 6%                   |
| enc_ppo_v2        |     724 |       -4.639 |    -2.038 | 85.5% | 1%         |     5.183 | 13%                  |
| il_ppo_rr         |     724 |       -3.026 |    -1.552 | 80.5% | 0%         |     2.939 | 9%                   |
| rp_il_ppo_rr      |     724 |       -3.026 |    -1.552 | 80.5% | 0%         |     2.939 | 9%                   |
| enc_il_ppo_rr     |     724 |       -4.509 |    -2.044 | 85.2% | 1%         |     4.877 | 12%                  |
| enc_vbv           |     724 |       -6.048 |    -5.765 | 32.6% | 0%         |     0.566 | 1%                   |
| enc_vbv_hindsight |     724 |       -5.415 |    -4.558 | 42.1% | 0%         |     1.713 | 2%                   |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     724 | +0.296 [+0.001, +0.708] |
| ppo_v2 - enc_vbv              |     724 | +2.856 [+2.204, +3.429] |
| ppo_v2 - enc_vbv_hindsight    |     724 | +2.222 [+1.590, +2.901] |
| ppo_v2 - enc_vbv2             |     724 | +0.637 [+0.205, +1.226] |
| enc_vbv2 - enc_vbv            |     724 | +2.219 [+1.463, +2.806] |
| enc_ppo_v2 - enc_vbv2         |     724 | -0.810 [-1.532, -0.181] |
| enc_ppo_v2 - enc_vbv          |     724 | +1.409 [+0.219, +2.416] |
| enc_ppo_v2 - ppo_v2           |     724 | -1.447 [-2.530, -0.644] |
| enc_vbv2 - vbv2               |     724 | -0.341 [-0.921, +0.219] |
| rp_il_ppo_rr - il_ppo_rr      |     724 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     724 | +0.462 [+0.176, +0.756] |
| il_ppo_rr - ppo_v2            |     724 | +0.166 [-0.203, +0.483] |
| il_ppo_rr - enc_vbv           |     724 | +3.022 [+2.306, +3.557] |
| il_ppo_rr - enc_vbv_hindsight |     724 | +2.389 [+1.715, +3.028] |
| enc_il_ppo_rr - enc_vbv2      |     724 | -0.680 [-1.329, -0.194] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | +0.503 [-0.031, +1.130] |
