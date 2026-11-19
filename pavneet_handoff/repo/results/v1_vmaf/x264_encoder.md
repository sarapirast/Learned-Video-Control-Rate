# VMAF of the encoder rate-control rows, x264 (D54)

3496 re-encodes; per-GOP bits differing from the stored run: 0. VMAF score = dVMAF_B - penalties at the local VMAF/dB rate (as D52). 95 % cluster bootstrap over source groups; * = CI excludes 0.

## Stream level (on-demand, clip-level budgets), test, 8 GOPs, learned rows at L = 2

| comparison | n | VMAF score native | VMAF score 1080p | dVMAF_B native | dVMAF_B 1080p |
|---|---|---|---|---|---|
| bc_ppo - encoder abr_vbv | 724 | -0.83 [-1.26, -0.44]* | -1.26 [-1.83, -0.81]* | -1.44 [-1.79, -1.09]* | -2.36 [-2.82, -1.95]* |
| bc_ppo - encoder 2pass | 724 | -1.90 [-2.43, -1.45]* | -2.16 [-2.82, -1.68]* | -1.77 [-2.22, -1.36]* | -2.04 [-2.64, -1.58]* |
| rule - encoder abr_vbv | 724 | -1.62 [-2.26, -1.11]* | -2.19 [-3.09, -1.47]* | -2.04 [-2.54, -1.63]* | -3.15 [-3.92, -2.50]* |
| rule - encoder 2pass | 724 | -2.70 [-3.46, -2.10]* | -3.09 [-4.07, -2.33]* | -2.37 [-3.05, -1.86]* | -2.83 [-3.75, -2.13]* |
| live AR(1) test: il_ppo - encoder ABR+VBV | 724 | -13.23 [-25.73, -6.12]* | -4.75 [-10.54, -1.64]* | -0.99 [-1.56, -0.30]* | -1.74 [-2.12, -1.39]* |
| live AR(1) test16: il_ppo - encoder ABR+VBV | 600 | -6.37 [-24.24, +3.50] | +4.22 [-2.69, +8.01] | -1.64 [-2.56, -0.68]* | -2.35 [-2.93, -1.86]* |
| live LTE test: il_ppo - encoder ABR+VBV | 724 | -14.84 [-33.71, -1.80]* | -1.52 [-10.89, +5.25] | +15.81 [+14.98, +16.73]* | +9.78 [+8.89, +10.57]* |
