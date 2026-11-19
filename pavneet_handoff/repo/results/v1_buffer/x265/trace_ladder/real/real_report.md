# D40 live channel with the real encoder in the loop (x265, trace_ladder)

Channel Belgium 4G/LTE traces (test files), cap 1.0 s, stall weight 0.5 dB per %. Score = luma dPSNR_B - 0.17 x %over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.

- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).
- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer (E2, channel-blind).
- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV (E3, channel-aware).

E2 target fraction tuned on val (f 0.2: -7.988, f 0.3: -6.894, f 0.4: -7.212, f 0.5: -7.995, f 0.6: -9.405, f 0.7: -11.104, f 0.8: -13.328, f 0.9: -16.220, f 1: -20.317): f = 0.3. enc_vbv_f1 = untuned (target = channel mean).

## v1 test (n = 8, every 3rd case)

E2 on this test set by f: 0.2 -7.142, 0.3 -5.770, 0.4 -5.228, 0.5 -5.414, 0.6 -5.924, 0.7 -6.749, 0.8 -7.788, 0.9 -9.372, 1 -11.771 (hindsight = f0.4).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:------|:-----------|----------:|:---------------------|
| vbv2              |     724 |       -5.186 |    -1.994 | 77.1% | 2%         |     6.081 | 17%                  |
| ppo_v2            |     724 |       -4.922 |    -1.838 | 77.4% | 2%         |     5.877 | 17%                  |
| rp_vbv2           |      96 |       -8.047 |    -1.523 | 85.3% | 9%         |    10.888 | 20%                  |
| rp_ppo_v2         |      96 |       -7.653 |    -1.425 | 84.0% | 9%         |    10.335 | 17%                  |
| enc_vbv_f1        |     724 |      -11.771 |    -0.765 | 96.7% | 26%        |    21.734 | 28%                  |
| enc_vbv2          |     724 |       -7.14  |    -2.619 | 83.7% | 7%         |     8.537 | 18%                  |
| enc_ppo_v2        |     724 |       -7.414 |    -2.506 | 83.8% | 9%         |     9.215 | 20%                  |
| il_ppo_rr         |     724 |       -5.133 |    -1.725 | 77.6% | 3%         |     6.429 | 14%                  |
| rp_il_ppo_rr      |     724 |       -5.133 |    -1.725 | 77.6% | 3%         |     6.429 | 14%                  |
| enc_il_ppo_rr     |     724 |       -8.035 |    -2.484 | 84.8% | 9%         |    10.436 | 22%                  |
| enc_vbv           |     724 |       -5.77  |    -5.668 | 33.3% | 0%         |     0.203 | 1%                   |
| enc_vbv_hindsight |     724 |       -5.228 |    -4.492 | 42.1% | 0%         |     1.473 | 2%                   |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     724 | +0.264 [-0.066, +0.620] |
| ppo_v2 - enc_vbv              |     724 | +0.848 [-0.999, +2.154] |
| ppo_v2 - enc_vbv_hindsight    |     724 | +0.306 [-1.440, +1.572] |
| ppo_v2 - enc_vbv2             |     724 | +2.218 [+0.525, +3.911] |
| enc_vbv2 - enc_vbv            |     724 | -1.370 [-3.443, +0.344] |
| enc_ppo_v2 - enc_vbv2         |     724 | -0.274 [-0.798, +0.119] |
| enc_ppo_v2 - enc_vbv          |     724 | -1.644 [-3.804, +0.054] |
| enc_ppo_v2 - ppo_v2           |     724 | -2.492 [-4.335, -0.765] |
| enc_vbv2 - vbv2               |     724 | -1.954 [-3.735, -0.108] |
| rp_il_ppo_rr - il_ppo_rr      |     724 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     724 | +0.053 [-0.394, +0.562] |
| il_ppo_rr - ppo_v2            |     724 | -0.211 [-0.597, +0.205] |
| il_ppo_rr - enc_vbv           |     724 | +0.636 [-1.207, +1.971] |
| il_ppo_rr - enc_vbv_hindsight |     724 | +0.095 [-1.643, +1.406] |
| enc_il_ppo_rr - enc_vbv2      |     724 | -0.895 [-1.882, -0.281] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | -0.000 [-0.350, +0.333] |
