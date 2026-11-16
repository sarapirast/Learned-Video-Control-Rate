# D40 live channel with the real encoder in the loop (x265)

Channel AR(1) rho 0.8, sigma 0.3, cap 1.0 s, stall weight 0.5 dB per %. Score = luma dPSNR_B - 0.17 x %over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.

- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).
- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer (E2, channel-blind).
- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV (E3, channel-aware).

E2 target fraction tuned on val (f 0.6: -3.199, f 0.7: -2.527, f 0.8: -2.035, f 0.9: -1.903, f 1: -2.563): f = 0.9. enc_vbv_f1 = untuned (target = channel mean).

## v1 test (n = 8, every 3rd case)

E2 on this test set by f: 0.6 -2.864, 0.7 -2.216, 0.8 -1.797, 0.9 -1.768, 1 -2.611 (hindsight = f0.9).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:------|:-----------|----------:|:---------------------|
| vbv2              |     724 |       -1.83  |    -1.245 | 84.3% | 0%         |     1.17  | 20%                  |
| ppo_v2            |     724 |       -1.359 |    -0.944 | 87.9% | 1%         |     0.815 | 14%                  |
| rp_vbv2           |      96 |       -1.609 |    -1.06  | 86.3% | 0%         |     1.099 | 17%                  |
| rp_ppo_v2         |      96 |       -1.207 |    -0.867 | 89.2% | 0%         |     0.68  | 14%                  |
| enc_vbv_f1        |     724 |       -2.611 |    -0.69  | 97.8% | 27%        |     3.543 | 44%                  |
| enc_vbv2          |     724 |       -1.849 |    -1.625 | 87.7% | 0%         |     0.447 | 13%                  |
| enc_ppo_v2        |     724 |       -1.894 |    -1.439 | 91.0% | 2%         |     0.857 | 16%                  |
| il_ppo_rr         |     724 |       -1.315 |    -0.971 | 87.6% | 1%         |     0.679 | 12%                  |
| rp_il_ppo_rr      |     724 |       -1.315 |    -0.971 | 87.6% | 1%         |     0.679 | 12%                  |
| enc_il_ppo_rr     |     724 |       -1.842 |    -1.471 | 90.8% | 1%         |     0.729 | 15%                  |
| enc_vbv           |     724 |       -1.768 |    -1.139 | 88.8% | 0%         |     1.258 | 18%                  |
| enc_vbv_hindsight |     724 |       -1.768 |    -1.139 | 88.8% | 0%         |     1.258 | 18%                  |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     724 | +0.471 [+0.392, +0.572] |
| ppo_v2 - enc_vbv              |     724 | +0.409 [+0.156, +0.602] |
| ppo_v2 - enc_vbv_hindsight    |     724 | +0.409 [+0.156, +0.602] |
| ppo_v2 - enc_vbv2             |     724 | +0.490 [+0.281, +0.683] |
| enc_vbv2 - enc_vbv            |     724 | -0.081 [-0.286, +0.069] |
| enc_ppo_v2 - enc_vbv2         |     724 | -0.045 [-0.185, +0.057] |
| enc_ppo_v2 - enc_vbv          |     724 | -0.126 [-0.409, +0.068] |
| enc_ppo_v2 - ppo_v2           |     724 | -0.535 [-0.779, -0.303] |
| enc_vbv2 - vbv2               |     724 | -0.019 [-0.234, +0.233] |
| rp_il_ppo_rr - il_ppo_rr      |     724 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     724 | +0.516 [+0.412, +0.652] |
| il_ppo_rr - ppo_v2            |     724 | +0.044 [-0.024, +0.127] |
| il_ppo_rr - enc_vbv           |     724 | +0.453 [+0.214, +0.649] |
| il_ppo_rr - enc_vbv_hindsight |     724 | +0.453 [+0.214, +0.649] |
| enc_il_ppo_rr - enc_vbv2      |     724 | +0.007 [-0.085, +0.097] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | +0.034 [-0.096, +0.133] |

## test playlists (n = 16, every 3rd)

E2 on this test set by f: 0.6 -3.341, 0.7 -3.075, 0.8 -3.398, 0.9 -4.630, 1 -7.015 (hindsight = f0.7).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:------|:-----------|----------:|:---------------------|
| vbv2              |     600 |       -2.322 |    -1.64  | 82.3% | 0%         |     1.361 | 32%                  |
| ppo_v2            |     600 |       -1.655 |    -1.436 | 84.0% | 0%         |     0.439 | 16%                  |
| rp_vbv2           |      96 |       -1.98  |    -1.412 | 82.1% | 0%         |     1.137 | 24%                  |
| rp_ppo_v2         |      96 |       -1.338 |    -1.204 | 84.1% | 0%         |     0.268 | 11%                  |
| enc_vbv_f1        |     600 |       -7.015 |    -0.966 | 97.2% | 16%        |    11.976 | 86%                  |
| enc_vbv2          |     600 |       -2.424 |    -2.045 | 84.9% | 0%         |     0.729 | 24%                  |
| enc_ppo_v2        |     600 |       -2.496 |    -1.992 | 86.1% | 1%         |     0.964 | 23%                  |
| il_ppo_rr         |     600 |       -1.639 |    -1.426 | 84.7% | 0%         |     0.427 | 14%                  |
| rp_il_ppo_rr      |     600 |       -1.639 |    -1.426 | 84.7% | 0%         |     0.427 | 14%                  |
| enc_il_ppo_rr     |     600 |       -2.541 |    -1.942 | 86.8% | 1%         |     1.139 | 27%                  |
| enc_vbv           |     600 |       -4.63  |    -1.427 | 88.0% | 0%         |     6.405 | 62%                  |
| enc_vbv_hindsight |     600 |       -3.075 |    -2.538 | 69.4% | 0%         |     1.074 | 14%                  |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     600 | +0.667 [+0.540, +0.765] |
| ppo_v2 - enc_vbv              |     600 | +2.974 [+2.683, +3.342] |
| ppo_v2 - enc_vbv_hindsight    |     600 | +1.420 [+1.168, +1.608] |
| ppo_v2 - enc_vbv2             |     600 | +0.768 [+0.484, +0.906] |
| enc_vbv2 - enc_vbv            |     600 | +2.206 [+1.908, +2.669] |
| enc_ppo_v2 - enc_vbv2         |     600 | -0.073 [-0.181, +0.032] |
| enc_ppo_v2 - enc_vbv          |     600 | +2.133 [+1.861, +2.611] |
| enc_ppo_v2 - ppo_v2           |     600 | -0.841 [-0.954, -0.565] |
| enc_vbv2 - vbv2               |     600 | -0.102 [-0.228, +0.179] |
| rp_il_ppo_rr - il_ppo_rr      |     600 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     600 | +0.683 [+0.520, +0.835] |
| il_ppo_rr - ppo_v2            |     600 | +0.016 [-0.049, +0.084] |
| il_ppo_rr - enc_vbv           |     600 | +2.991 [+2.743, +3.320] |
| il_ppo_rr - enc_vbv_hindsight |     600 | +1.436 [+1.176, +1.658] |
| enc_il_ppo_rr - enc_vbv2      |     600 | -0.117 [-0.207, -0.025] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | -0.026 [-0.096, +0.040] |
