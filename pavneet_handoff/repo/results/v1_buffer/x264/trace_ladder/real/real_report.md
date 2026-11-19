# D40 live channel with the real encoder in the loop (x264, trace_ladder)

Channel Belgium 4G/LTE traces (test files), cap 1.0 s, stall weight 0.5 dB per %. Score = luma dPSNR_B - 0.17 x %over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.

- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).
- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer (E2, channel-blind).
- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV (E3, channel-aware).

E2 target fraction tuned on val (f 0.2: -10.278, f 0.3: -8.974, f 0.4: -8.945, f 0.5: -9.551, f 0.6: -10.740, f 0.7: -12.729, f 0.8: -15.063, f 0.9: -18.217, f 1: -22.422): f = 0.4. enc_vbv_f1 = untuned (target = channel mean).

## v1 test (n = 8, every 3rd case)

E2 on this test set by f: 0.2 -8.590, 0.3 -6.579, 0.4 -5.681, 0.5 -5.690, 0.6 -6.146, 0.7 -6.937, 0.8 -8.159, 0.9 -9.946, 1 -12.838 (hindsight = f0.4).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:-------|:-----------|----------:|:---------------------|
| vbv2              |     724 |       -6.746 |    -2.017 | 77.4%  | 5%         |     8.874 | 18%                  |
| ppo_v2            |     724 |       -6.357 |    -1.952 | 78.7%  | 5%         |     8.252 | 19%                  |
| rp_vbv2           |      96 |      -11.378 |    -1.135 | 88.1%  | 11%        |    17.149 | 19%                  |
| rp_ppo_v2         |      96 |      -10.69  |    -1.164 | 89.9%  | 9%         |    15.806 | 18%                  |
| enc_vbv_f1        |     724 |      -12.838 |    -0.456 | 100.2% | 47%        |    24.257 | 32%                  |
| enc_vbv2          |     724 |       -6.976 |    -3.713 | 80.5%  | 3%         |     6.313 | 14%                  |
| enc_ppo_v2        |     724 |       -7.457 |    -4.077 | 80.2%  | 3%         |     6.554 | 18%                  |
| il_ppo_rr         |     724 |       -6.456 |    -1.764 | 80.1%  | 6%         |     8.785 | 18%                  |
| rp_il_ppo_rr      |     724 |       -6.456 |    -1.764 | 80.1%  | 6%         |     8.785 | 18%                  |
| enc_il_ppo_rr     |     724 |       -7.129 |    -3.578 | 82.5%  | 3%         |     6.889 | 18%                  |
| enc_vbv           |     724 |       -5.681 |    -4.92  | 41.2%  | 0%         |     1.523 | 2%                   |
| enc_vbv_hindsight |     724 |       -5.681 |    -4.92  | 41.2%  | 0%         |     1.523 | 2%                   |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     724 | +0.389 [+0.043, +0.722] |
| ppo_v2 - enc_vbv              |     724 | -0.676 [-3.109, +1.094] |
| ppo_v2 - enc_vbv_hindsight    |     724 | -0.676 [-3.109, +1.094] |
| ppo_v2 - enc_vbv2             |     724 | +0.619 [-0.997, +2.144] |
| enc_vbv2 - enc_vbv            |     724 | -1.295 [-2.854, -0.150] |
| enc_ppo_v2 - enc_vbv2         |     724 | -0.481 [-0.976, +0.143] |
| enc_ppo_v2 - enc_vbv          |     724 | -1.776 [-3.306, -0.639] |
| enc_ppo_v2 - ppo_v2           |     724 | -1.100 [-2.704, +0.724] |
| enc_vbv2 - vbv2               |     724 | -0.229 [-1.957, +1.609] |
| rp_il_ppo_rr - il_ppo_rr      |     724 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     724 | +0.290 [-0.206, +0.635] |
| il_ppo_rr - ppo_v2            |     724 | -0.100 [-0.479, +0.157] |
| il_ppo_rr - enc_vbv           |     724 | -0.775 [-3.333, +1.039] |
| il_ppo_rr - enc_vbv_hindsight |     724 | -0.775 [-3.333, +1.039] |
| enc_il_ppo_rr - enc_vbv2      |     724 | -0.153 [-0.766, +0.269] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | -0.035 [-0.615, +0.423] |
