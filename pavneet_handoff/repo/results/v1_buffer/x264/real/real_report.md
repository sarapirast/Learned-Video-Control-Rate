# D40 live channel with the real encoder in the loop (x264)

Channel AR(1) rho 0.8, sigma 0.3, cap 1.0 s, stall weight 0.5 dB per %. Score = luma dPSNR_B - 0.17 x %over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.

- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).
- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer (E2, channel-blind).
- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV (E3, channel-aware).

E2 target fraction tuned on val (f 0.6: -3.070, f 0.7: -2.301, f 0.8: -1.736, f 0.9: -1.663, f 1: -2.829): f = 0.9. enc_vbv_f1 = untuned (target = channel mean).

## v1 test (n = 8, every 3rd case)

E2 on this test set by f: 0.6 -3.120, 0.7 -2.347, 0.8 -1.811, 0.9 -1.726, 1 -2.861 (hindsight = f0.9).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:-------|:-----------|----------:|:---------------------|
| vbv2              |     724 |       -2.155 |    -1.396 | 83.8%  | 0%         |     1.518 | 21%                  |
| ppo_v2            |     724 |       -1.778 |    -1.211 | 86.8%  | 1%         |     1.13  | 18%                  |
| rp_vbv2           |      96 |       -1.992 |    -1.146 | 86.2%  | 0%         |     1.69  | 27%                  |
| rp_ppo_v2         |      96 |       -1.704 |    -1.12  | 88.1%  | 0%         |     1.17  | 22%                  |
| enc_vbv_f1        |     724 |       -2.861 |    -0.452 | 101.0% | 54%        |     4.216 | 50%                  |
| enc_vbv2          |     724 |       -3.024 |    -2.765 | 88.3%  | 0%         |     0.516 | 14%                  |
| enc_ppo_v2        |     724 |       -2.46  |    -2.103 | 90.3%  | 0%         |     0.711 | 16%                  |
| il_ppo_rr         |     724 |       -1.666 |    -1.077 | 88.4%  | 1%         |     1.157 | 19%                  |
| rp_il_ppo_rr      |     724 |       -1.666 |    -1.077 | 88.4%  | 1%         |     1.157 | 19%                  |
| enc_il_ppo_rr     |     724 |       -2.74  |    -2.233 | 91.4%  | 1%         |     1.009 | 22%                  |
| enc_vbv           |     724 |       -1.726 |    -0.996 | 91.1%  | 0%         |     1.459 | 22%                  |
| enc_vbv_hindsight |     724 |       -1.726 |    -0.996 | 91.1%  | 0%         |     1.459 | 22%                  |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     724 | +0.378 [+0.246, +0.496] |
| ppo_v2 - enc_vbv              |     724 | -0.052 [-0.452, +0.217] |
| ppo_v2 - enc_vbv_hindsight    |     724 | -0.052 [-0.452, +0.217] |
| ppo_v2 - enc_vbv2             |     724 | +1.246 [+0.768, +1.769] |
| enc_vbv2 - enc_vbv            |     724 | -1.298 [-1.927, -0.829] |
| enc_ppo_v2 - enc_vbv2         |     724 | +0.563 [+0.275, +0.950] |
| enc_ppo_v2 - enc_vbv          |     724 | -0.734 [-1.102, -0.458] |
| enc_ppo_v2 - ppo_v2           |     724 | -0.683 [-1.021, -0.346] |
| enc_vbv2 - vbv2               |     724 | -0.868 [-1.399, -0.386] |
| rp_il_ppo_rr - il_ppo_rr      |     724 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     724 | +0.489 [+0.389, +0.612] |
| il_ppo_rr - ppo_v2            |     724 | +0.111 [+0.046, +0.215] |
| il_ppo_rr - enc_vbv           |     724 | +0.059 [-0.275, +0.289] |
| il_ppo_rr - enc_vbv_hindsight |     724 | +0.059 [-0.275, +0.289] |
| enc_il_ppo_rr - enc_vbv2      |     724 | +0.283 [+0.014, +0.602] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | +0.104 [+0.015, +0.181] |

## test playlists (n = 16, every 3rd)

E2 on this test set by f: 0.6 -3.535, 0.7 -3.152, 0.8 -3.507, 0.9 -4.844, 1 -7.508 (hindsight = f0.7).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use   | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:------|:-----------|----------:|:---------------------|
| vbv2              |     600 |       -2.645 |    -1.815 | 81.9% | 0%         |     1.648 | 38%                  |
| ppo_v2            |     600 |       -2.039 |    -1.718 | 82.8% | 0%         |     0.641 | 18%                  |
| rp_vbv2           |      96 |       -2.166 |    -1.559 | 81.0% | 0%         |     1.213 | 30%                  |
| rp_ppo_v2         |      96 |       -1.657 |    -1.44  | 82.8% | 0%         |     0.435 | 17%                  |
| enc_vbv_f1        |     600 |       -7.508 |    -0.82  | 99.5% | 30%        |    13.162 | 90%                  |
| enc_vbv2          |     600 |       -3.053 |    -2.721 | 85.3% | 0%         |     0.655 | 26%                  |
| enc_ppo_v2        |     600 |       -3.099 |    -2.594 | 85.8% | 1%         |     0.983 | 26%                  |
| il_ppo_rr         |     600 |       -2.01  |    -1.597 | 85.1% | 1%         |     0.82  | 22%                  |
| rp_il_ppo_rr      |     600 |       -2.01  |    -1.597 | 85.1% | 1%         |     0.82  | 22%                  |
| enc_il_ppo_rr     |     600 |       -3.142 |    -2.435 | 88.0% | 1%         |     1.335 | 34%                  |
| enc_vbv           |     600 |       -4.844 |    -1.354 | 89.7% | 0%         |     6.98  | 65%                  |
| enc_vbv_hindsight |     600 |       -3.152 |    -2.632 | 70.0% | 0%         |     1.038 | 15%                  |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     600 | +0.605 [+0.488, +0.731] |
| ppo_v2 - enc_vbv              |     600 | +2.805 [+2.563, +3.157] |
| ppo_v2 - enc_vbv_hindsight    |     600 | +1.113 [+0.841, +1.374] |
| ppo_v2 - enc_vbv2             |     600 | +1.013 [+0.380, +1.334] |
| enc_vbv2 - enc_vbv            |     600 | +1.792 [+1.436, +2.556] |
| enc_ppo_v2 - enc_vbv2         |     600 | -0.047 [-0.377, +0.146] |
| enc_ppo_v2 - enc_vbv          |     600 | +1.745 [+1.431, +2.319] |
| enc_ppo_v2 - ppo_v2           |     600 | -1.060 [-1.323, -0.713] |
| enc_vbv2 - vbv2               |     600 | -0.408 [-0.764, +0.224] |
| rp_il_ppo_rr - il_ppo_rr      |     600 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     600 | +0.635 [+0.501, +0.780] |
| il_ppo_rr - ppo_v2            |     600 | +0.029 [-0.028, +0.088] |
| il_ppo_rr - enc_vbv           |     600 | +2.835 [+2.600, +3.185] |
| il_ppo_rr - enc_vbv_hindsight |     600 | +1.142 [+0.841, +1.433] |
| enc_il_ppo_rr - enc_vbv2      |     600 | -0.090 [-0.444, +0.099] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | -0.029 [-0.091, +0.031] |
