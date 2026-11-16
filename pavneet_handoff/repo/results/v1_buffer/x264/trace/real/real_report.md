# D40 live channel with the real encoder in the loop (x264, trace)

Channel Belgium 4G/LTE traces (test files), cap 1.0 s, stall weight 0.5 dB per %. Score = luma dPSNR_B - 0.17 x %over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.

- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).
- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer (E2, channel-blind).
- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV (E3, channel-aware).

E2 target fraction tuned on val (f 0.2: -8.308, f 0.3: -7.246, f 0.4: -7.327, f 0.5: -7.899, f 0.6: -8.947, f 0.7: -11.012, f 0.8: -13.405, f 0.9: -16.643, f 1: -20.861): f = 0.3. enc_vbv_f1 = untuned (target = channel mean).

## v1 test (n = 8, every 3rd case)

E2 on this test set by f: 0.2 -9.023, 0.3 -6.979, 0.4 -6.143, 0.5 -6.037, 0.6 -6.345, 0.7 -7.060, 0.8 -8.219, 0.9 -10.035, 1 -13.042 (hindsight = f0.5).

Lookup vbv2 / ppo_v2 = D39 rows (max |diff| 0.0e+00).

| method            |   cases |   score (dB) |   dPSNR_B | use    | >1% over   |   stall % | streams with stall   |
|:------------------|--------:|-------------:|----------:|:-------|:-----------|----------:|:---------------------|
| vbv2              |     724 |       -4.168 |    -2.496 | 75.9%  | 0%         |     3.343 | 12%                  |
| ppo_v2            |     724 |       -3.886 |    -1.979 | 78.9%  | 0%         |     3.807 | 12%                  |
| rp_vbv2           |      96 |       -3.154 |    -2.346 | 79.3%  | 0%         |     1.616 | 7%                   |
| rp_ppo_v2         |      96 |       -3.046 |    -1.913 | 82.0%  | 1%         |     2.256 | 8%                   |
| enc_vbv_f1        |     724 |      -13.042 |    -0.452 | 101.0% | 54%        |    24.577 | 33%                  |
| enc_vbv2          |     724 |       -5.88  |    -4.64  | 80.6%  | 0%         |     2.48  | 8%                   |
| enc_ppo_v2        |     724 |       -5.536 |    -3.436 | 83.7%  | 0%         |     4.183 | 12%                  |
| il_ppo_rr         |     724 |       -3.52  |    -1.906 | 79.4%  | 1%         |     3.221 | 10%                  |
| rp_il_ppo_rr      |     724 |       -3.52  |    -1.906 | 79.4%  | 1%         |     3.221 | 10%                  |
| enc_il_ppo_rr     |     724 |       -5.473 |    -3.593 | 84.0%  | 0%         |     3.752 | 13%                  |
| enc_vbv           |     724 |       -6.979 |    -6.757 | 31.8%  | 0%         |     0.443 | 1%                   |
| enc_vbv_hindsight |     724 |       -6.037 |    -4.08  | 51.5%  | 0%         |     3.914 | 3%                   |

| comparison                    |   cases | score diff (dB)         |
|:------------------------------|--------:|:------------------------|
| rp_vbv2 - vbv2                |      96 | +0.000 [+0.000, +0.000] |
| rp_ppo_v2 - ppo_v2            |      96 | +0.000 [+0.000, +0.000] |
| ppo_v2 - vbv2                 |     724 | +0.282 [+0.010, +0.626] |
| ppo_v2 - enc_vbv              |     724 | +3.093 [+2.091, +3.798] |
| ppo_v2 - enc_vbv_hindsight    |     724 | +2.151 [+1.276, +3.136] |
| ppo_v2 - enc_vbv2             |     724 | +1.994 [+1.277, +2.808] |
| enc_vbv2 - enc_vbv            |     724 | +1.099 [-0.062, +1.877] |
| enc_ppo_v2 - enc_vbv2         |     724 | +0.344 [-0.216, +1.006] |
| enc_ppo_v2 - enc_vbv          |     724 | +1.443 [+0.365, +2.269] |
| enc_ppo_v2 - ppo_v2           |     724 | -1.649 [-2.532, -0.778] |
| enc_vbv2 - vbv2               |     724 | -1.712 [-2.495, -0.945] |
| rp_il_ppo_rr - il_ppo_rr      |     724 | +0.000 [+0.000, +0.000] |
| il_ppo_rr - vbv2              |     724 | +0.648 [+0.405, +0.998] |
| il_ppo_rr - ppo_v2            |     724 | +0.366 [+0.185, +0.557] |
| il_ppo_rr - enc_vbv           |     724 | +3.458 [+2.488, +4.128] |
| il_ppo_rr - enc_vbv_hindsight |     724 | +2.517 [+1.724, +3.433] |
| enc_il_ppo_rr - enc_vbv2      |     724 | +0.407 [-0.084, +0.975] |
| rp_il_ppo_rr - rp_ppo_v2      |      96 | +0.465 [-0.211, +1.232] |
