# VMAF of the encoder rate-control rows, x265 (D54)

3496 re-encodes; per-GOP bits differing from the stored run: 0. VMAF score = dVMAF_B - penalties at the local VMAF/dB rate (as D52). 95 % cluster bootstrap over source groups; * = CI excludes 0.

## Stream level (on-demand, clip-level budgets), test, 8 GOPs, learned rows at L = 2

| comparison | n | VMAF score native | VMAF score 1080p | dVMAF_B native | dVMAF_B 1080p |
|---|---|---|---|---|---|
| bc_ppo - encoder abr_vbv | 724 | +0.35 [-0.04, +0.70] | +0.24 [-0.41, +0.83] | +0.11 [-0.21, +0.46] | -0.19 [-0.72, +0.37] |
| bc_ppo - encoder 2pass | 724 | -0.10 [-0.35, +0.10] | -0.39 [-0.68, -0.16]* | -1.17 [-1.46, -0.85]* | -1.21 [-1.54, -0.89]* |
| rule - encoder abr_vbv | 724 | -0.90 [-1.64, -0.36]* | -1.00 [-2.09, -0.09]* | -0.89 [-1.39, -0.46]* | -1.30 [-2.17, -0.50]* |
| rule - encoder 2pass | 724 | -1.35 [-1.98, -0.92]* | -1.63 [-2.35, -1.15]* | -2.17 [-2.51, -1.91]* | -2.32 [-2.81, -1.97]* |
| live AR(1) test: il_ppo - encoder ABR+VBV | 724 | -6.04 [-15.34, -1.34]* | -0.86 [-4.84, +1.13] | -0.21 [-0.75, +0.43] | -0.03 [-0.38, +0.39] |
| live AR(1) test16: il_ppo - encoder ABR+VBV | 600 | +0.72 [-12.20, +8.66] | +7.60 [+3.07, +10.66]* | -0.94 [-1.81, -0.10]* | -0.83 [-1.45, -0.16]* |
| live LTE test: il_ppo - encoder ABR+VBV | 724 | -2.33 [-16.66, +7.76] | +4.29 [-2.80, +9.20] | +19.97 [+18.90, +20.90]* | +13.83 [+12.52, +14.75]* |
