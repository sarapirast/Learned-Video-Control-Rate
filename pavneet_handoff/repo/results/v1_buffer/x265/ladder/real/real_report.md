# D40 live channel with the real encoder in the loop (x265, ladder)

Channel AR(1) rho 0.8, sigma 0.3, cap 1.0 s, stall weight 0.5 dB per %. Score = luma dPSNR_B - 0.17 x %over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.

- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).
- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer (E2, channel-blind).
- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV (E3, channel-aware).

E2 target fraction tuned on val (f 0.6: -3.533, f 0.7: -2.907, f 0.8: -2.459, f 0.9: -2.340, f 1: -3.023): f = 0.9. enc_vbv_f1 = untuned (target = channel mean).

## v1 test (n = 8, every 3rd case)

E2 on this test set by f: 0.6 -2.846, 0.7 -2.237, 0.8 -1.831, 0.9 -1.798, 1 -2.564 (hindsight = f0.9).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:------|:-----------|----------:|:---------------------|
| vbv2              |     724 |       -2.883 |    -1.285 | 84.3% | 3%         |     2.876 | 25%                  |
| ppo_v2            |     724 |       -2.526 |    -1.338 | 82.0% | 2%         |     2.07  | 15%                  |
| rp_vbv2           |      96 |       -5.801 |    -0.828 | 91.4% | 9%         |     7.76  | 27%                  |
| rp_ppo_v2         |      96 |       -5.557 |    -0.955 | 88.5% | 10%        |     7.068 | 20%                  |
| enc_vbv_f1        |     724 |       -2.564 |    -0.765 | 96.7% | 26%        |     3.32  | 41%                  |
| enc_vbv2          |     724 |       -3.719 |    -1.831 | 89.5% | 7%         |     3.243 | 23%                  |
| enc_ppo_v2        |     724 |       -3.954 |    -1.958 | 88.0% | 8%         |     3.36  | 17%                  |
| il_ppo_rr         |     724 |       -2.293 |    -1.133 | 84.2% | 3%         |     1.998 | 13%                  |
| rp_il_ppo_rr      |     724 |       -2.293 |    -1.133 | 84.2% | 3%         |     1.998 | 13%                  |
| enc_il_ppo_rr     |     724 |       -3.868 |    -1.746 | 90.6% | 9%         |     3.572 | 21%                  |
| enc_vbv           |     724 |       -1.798 |    -1.19  | 87.8% | 0%         |     1.216 | 17%                  |
| enc_vbv_hindsight |     724 |       -1.798 |    -1.19  | 87.8% | 0%         |     1.216 | 17%                  |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     724 | +0.356 [+0.193, +0.593] |
| ppo_v2 - enc_vbv              |     724 | -0.728 [-1.952, -0.110] |
| ppo_v2 - enc_vbv_hindsight    |     724 | -0.728 [-1.952, -0.110] |
| ppo_v2 - enc_vbv2             |     724 | +1.192 [+0.228, +1.977] |
| enc_vbv2 - enc_vbv            |     724 | -1.921 [-2.691, -1.381] |
| enc_ppo_v2 - enc_vbv2         |     724 | -0.235 [-0.373, -0.080] |
| enc_ppo_v2 - enc_vbv          |     724 | -2.156 [-2.979, -1.548] |
| enc_ppo_v2 - ppo_v2           |     724 | -1.427 [-2.280, -0.437] |
| enc_vbv2 - vbv2               |     724 | -0.836 [-1.615, +0.148] |
| rp_il_ppo_rr - il_ppo_rr      |     724 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     724 | +0.590 [+0.394, +0.880] |
| il_ppo_rr - ppo_v2            |     724 | +0.234 [+0.154, +0.338] |
| il_ppo_rr - enc_vbv           |     724 | -0.495 [-1.732, +0.115] |
| il_ppo_rr - enc_vbv_hindsight |     724 | -0.495 [-1.732, +0.115] |
| enc_il_ppo_rr - enc_vbv2      |     724 | -0.150 [-0.301, -0.025] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | +0.187 [+0.039, +0.341] |

## test playlists (n = 16, every 3rd)

E2 on this test set by f: 0.6 -3.263, 0.7 -3.022, 0.8 -3.340, 0.9 -4.506, 1 -6.837 (hindsight = f0.7).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:------|:-----------|----------:|:---------------------|
| vbv2              |     600 |       -3.71  |    -1.494 | 83.3% | 4%         |     3.851 | 31%                  |
| ppo_v2            |     600 |       -3.362 |    -1.549 | 81.2% | 3%         |     3.057 | 14%                  |
| rp_vbv2           |      96 |       -2.942 |    -1.235 | 83.1% | 2%         |     3.078 | 31%                  |
| rp_ppo_v2         |      96 |       -2.565 |    -1.25  | 80.7% | 2%         |     2.299 | 15%                  |
| enc_vbv_f1        |     600 |       -6.837 |    -1.022 | 96.4% | 13%        |    11.527 | 85%                  |
| enc_vbv2          |     600 |       -4.915 |    -2.16  | 86.8% | 8%         |     4.895 | 28%                  |
| enc_ppo_v2        |     600 |       -4.8   |    -2.205 | 84.9% | 8%         |     4.588 | 20%                  |
| il_ppo_rr         |     600 |       -3.228 |    -1.359 | 83.3% | 4%         |     3.16  | 19%                  |
| rp_il_ppo_rr      |     600 |       -3.228 |    -1.359 | 83.3% | 4%         |     3.16  | 19%                  |
| enc_il_ppo_rr     |     600 |       -4.726 |    -2.025 | 87.1% | 8%         |     4.798 | 28%                  |
| enc_vbv           |     600 |       -4.506 |    -1.474 | 87.3% | 0%         |     6.064 | 61%                  |
| enc_vbv_hindsight |     600 |       -3.022 |    -2.521 | 69.0% | 0%         |     1.001 | 14%                  |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     600 | +0.348 [+0.218, +0.566] |
| ppo_v2 - enc_vbv              |     600 | +1.144 [-0.497, +2.124] |
| ppo_v2 - enc_vbv_hindsight    |     600 | -0.340 [-2.021, +0.490] |
| ppo_v2 - enc_vbv2             |     600 | +1.553 [+0.551, +2.049] |
| enc_vbv2 - enc_vbv            |     600 | -0.409 [-1.242, +0.292] |
| enc_ppo_v2 - enc_vbv2         |     600 | +0.115 [-0.066, +0.200] |
| enc_ppo_v2 - enc_vbv          |     600 | -0.294 [-1.208, +0.407] |
| enc_ppo_v2 - ppo_v2           |     600 | -1.438 [-1.968, -0.493] |
| enc_vbv2 - vbv2               |     600 | -1.204 [-1.701, -0.136] |
| rp_il_ppo_rr - il_ppo_rr      |     600 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     600 | +0.482 [+0.301, +0.747] |
| il_ppo_rr - ppo_v2            |     600 | +0.133 [+0.036, +0.217] |
| il_ppo_rr - enc_vbv           |     600 | +1.278 [-0.306, +2.195] |
| il_ppo_rr - enc_vbv_hindsight |     600 | -0.207 [-1.836, +0.574] |
| enc_il_ppo_rr - enc_vbv2      |     600 | +0.189 [+0.124, +0.225] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | +0.170 [+0.059, +0.354] |
