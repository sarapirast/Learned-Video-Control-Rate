# Exp 5a smooth 4-parameter shift (exp_next/exp5/shift_smooth.py)

Beta 0.1 weights, clipped labels, fitting clips only. Params = I offset, frame-1 offset, ramp value at frame 2, ramp value at frame 29 (QP, real-valued).

| enc | k | variant | I | frame 1 | ramp f2 | ramp f29 | sd of per-frame means about the line (f2-29) | corr(residual, ramp rounding error) |
|---|---|---|---|---|---|---|---|---|
| x264 | 2 | pooled | +0.58 | -1.75 | -1.32 | -0.65 | 0.36 | +0.65 |
| x264 | 2 | L24 | -0.58 | -1.37 | -1.08 | -1.05 | 0.54 | +0.60 |
| x264 | 2 | L30 | +0.05 | -1.71 | -1.36 | -0.95 | 0.53 | +0.16 |
| x264 | 2 | L36 | +0.80 | -1.94 | -1.60 | -0.56 | 0.49 | +0.56 |
| x264 | 2 | L42 | +2.00 | -1.98 | -1.25 | -0.07 | 0.46 | +0.54 |
| x265 | 2 | pooled | +0.54 | -1.86 | -1.28 | -0.73 | 0.34 | +0.64 |
| x265 | 2 | L24 | -0.63 | -1.40 | -1.04 | -0.95 | 0.49 | +0.59 |
| x265 | 2 | L30 | +0.08 | -1.80 | -1.27 | -0.94 | 0.51 | +0.16 |
| x265 | 2 | L36 | +0.87 | -2.07 | -1.56 | -0.71 | 0.45 | +0.55 |
| x265 | 2 | L42 | +1.81 | -2.16 | -1.25 | -0.33 | 0.43 | +0.56 |

Per-level vs pooled (max |difference| of the smooth vectors): x264 k2 1.42; x265 k2 1.27

