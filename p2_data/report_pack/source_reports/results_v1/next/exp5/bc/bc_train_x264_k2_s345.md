# Exp 5b BC classifier, x264 (exp_next/exp5/bc_train.py)

Target label2 (13 classes), beta 0.1 weights, hold-out 10% of fitting clips, 40000 steps x batch 1024, lr 0.0003; checkpoint = lowest hold-out weighted CE (every 2000). R^2 = expected offset vs the per-frame weighted mean of the target (the centred-label R^2; go/no-go threshold 0.10 at k5).

| k | seed | best step | hold-out CE | CE of per-frame prior | acc | R^2 centred | P(argmax = 0) | minutes |
|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 20000 | 1.6908 | 2.0763 | 0.316 | 0.519 | 0.235 | 4.7 |
| 2 | 4 | 24000 | 1.6987 | 2.0763 | 0.318 | 0.510 | 0.204 | 4.7 |
| 2 | 5 | 20000 | 1.6932 | 2.0763 | 0.310 | 0.518 | 0.204 | 4.7 |

Hold-out clips are fitting clips (train minus the fold); the fold and val were never in the data.

