# D40 live channel with the real encoder in the loop (x264, ladder)

Channel AR(1) rho 0.8, sigma 0.3, cap 1.0 s, stall weight 0.5 dB per %. Score = luma dPSNR_B - 0.17 x %over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.

- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).
- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer (E2, channel-blind).
- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV (E3, channel-aware).

E2 target fraction tuned on val (f 0.6: -4.968, f 0.7: -4.133, f 0.8: -3.617, f 0.9: -3.499, f 1: -4.588): f = 0.9. enc_vbv_f1 = untuned (target = channel mean).

## v1 test (n = 8, every 3rd case)

E2 on this test set by f: 0.6 -2.867, 0.7 -2.138, 0.8 -1.638, 0.9 -1.629, 1 -2.720 (hindsight = f0.9).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:-------|:-----------|----------:|:---------------------|
| vbv2              |     724 |       -3.713 |    -1.417 | 84.7%  | 6%         |     3.992 | 25%                  |
| ppo_v2            |     724 |       -3.457 |    -1.261 | 87.2%  | 6%         |     3.782 | 22%                  |
| rp_vbv2           |      96 |       -8.238 |    -0.554 | 95.0%  | 12%        |    12.002 | 27%                  |
| rp_ppo_v2         |      96 |       -8.116 |    -0.553 | 96.1%  | 12%        |    11.82  | 23%                  |
| enc_vbv_f1        |     724 |       -2.72  |    -0.456 | 100.2% | 47%        |     4.02  | 48%                  |
| enc_vbv2          |     724 |       -4.049 |    -3.015 | 87.7%  | 3%         |     1.849 | 16%                  |
| enc_ppo_v2        |     724 |       -3.589 |    -2.341 | 89.7%  | 5%         |     2.226 | 19%                  |
| il_ppo_rr         |     724 |       -3.302 |    -1.174 | 87.7%  | 7%         |     3.617 | 22%                  |
| rp_il_ppo_rr      |     724 |       -3.302 |    -1.174 | 87.7%  | 7%         |     3.617 | 22%                  |
| enc_il_ppo_rr     |     724 |       -3.634 |    -2.369 | 89.5%  | 4%         |     2.275 | 21%                  |
| enc_vbv           |     724 |       -1.629 |    -0.938 | 90.4%  | 0%         |     1.381 | 21%                  |
| enc_vbv_hindsight |     724 |       -1.629 |    -0.938 | 90.4%  | 0%         |     1.381 | 21%                  |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     724 | +0.255 [+0.153, +0.362] |
| ppo_v2 - enc_vbv              |     724 | -1.829 [-3.548, -0.891] |
| ppo_v2 - enc_vbv_hindsight    |     724 | -1.829 [-3.548, -0.891] |
| ppo_v2 - enc_vbv2             |     724 | +0.592 [-0.650, +1.705] |
| enc_vbv2 - enc_vbv            |     724 | -2.420 [-3.395, -1.782] |
| enc_ppo_v2 - enc_vbv2         |     724 | +0.460 [+0.194, +0.849] |
| enc_ppo_v2 - enc_vbv          |     724 | -1.960 [-2.698, -1.466] |
| enc_ppo_v2 - ppo_v2           |     724 | -0.131 [-1.068, +1.116] |
| enc_vbv2 - vbv2               |     724 | -0.336 [-1.449, +0.907] |
| rp_il_ppo_rr - il_ppo_rr      |     724 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     724 | +0.411 [+0.308, +0.542] |
| il_ppo_rr - ppo_v2            |     724 | +0.155 [+0.073, +0.267] |
| il_ppo_rr - enc_vbv           |     724 | -1.673 [-3.373, -0.748] |
| il_ppo_rr - enc_vbv_hindsight |     724 | -1.673 [-3.373, -0.748] |
| enc_il_ppo_rr - enc_vbv2      |     724 | +0.415 [+0.156, +0.785] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | +0.024 [-0.252, +0.253] |

## test playlists (n = 16, every 3rd)

E2 on this test set by f: 0.6 -3.264, 0.7 -2.879, 0.8 -3.244, 0.9 -4.581, 1 -7.201 (hindsight = f0.7).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:------|:-----------|----------:|:---------------------|
| vbv2              |     600 |       -4.944 |    -1.547 | 84.5% | 6%         |     5.817 | 40%                  |
| ppo_v2            |     600 |       -4.565 |    -1.498 | 85.3% | 6%         |     5.174 | 26%                  |
| rp_vbv2           |      96 |       -3.994 |    -1.244 | 83.3% | 3%         |     4.946 | 36%                  |
| rp_ppo_v2         |      96 |       -3.621 |    -1.195 | 84.2% | 4%         |     4.289 | 24%                  |
| enc_vbv_f1        |     600 |       -7.201 |    -0.734 | 98.8% | 23%        |    12.76  | 90%                  |
| enc_vbv2          |     600 |       -4.56  |    -2.516 | 86.2% | 6%         |     3.684 | 24%                  |
| enc_ppo_v2        |     600 |       -4.293 |    -2.265 | 86.5% | 6%         |     3.638 | 23%                  |
| il_ppo_rr         |     600 |       -4.487 |    -1.379 | 86.4% | 8%         |     5.233 | 31%                  |
| rp_il_ppo_rr      |     600 |       -4.487 |    -1.379 | 86.4% | 8%         |     5.233 | 31%                  |
| enc_il_ppo_rr     |     600 |       -4.497 |    -2.344 | 87.1% | 6%         |     3.88  | 31%                  |
| enc_vbv           |     600 |       -4.581 |    -1.211 | 89.1% | 0%         |     6.739 | 63%                  |
| enc_vbv_hindsight |     600 |       -2.879 |    -2.384 | 69.5% | 0%         |     0.991 | 15%                  |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     600 | +0.379 [+0.298, +0.471] |
| ppo_v2 - enc_vbv              |     600 | +0.016 [-2.309, +1.355] |
| ppo_v2 - enc_vbv_hindsight    |     600 | -1.685 [-3.979, -0.457] |
| ppo_v2 - enc_vbv2             |     600 | -0.005 [-1.739, +1.200] |
| enc_vbv2 - enc_vbv            |     600 | +0.021 [-0.748, +0.694] |
| enc_ppo_v2 - enc_vbv2         |     600 | +0.267 [-0.113, +0.446] |
| enc_ppo_v2 - enc_vbv          |     600 | +0.288 [-0.582, +0.843] |
| enc_ppo_v2 - ppo_v2           |     600 | +0.272 [-0.888, +1.824] |
| enc_vbv2 - vbv2               |     600 | +0.384 [-0.830, +2.172] |
| rp_il_ppo_rr - il_ppo_rr      |     600 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     600 | +0.457 [+0.367, +0.521] |
| il_ppo_rr - ppo_v2            |     600 | +0.077 [-0.045, +0.143] |
| il_ppo_rr - enc_vbv           |     600 | +0.093 [-2.295, +1.428] |
| il_ppo_rr - enc_vbv_hindsight |     600 | -1.608 [-3.959, -0.380] |
| enc_il_ppo_rr - enc_vbv2      |     600 | +0.062 [-0.227, +0.316] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | -0.069 [-0.229, +0.035] |
