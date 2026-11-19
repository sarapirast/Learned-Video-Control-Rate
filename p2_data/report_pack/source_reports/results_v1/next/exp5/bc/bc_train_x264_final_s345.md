# Exp 5b BC classifier, x264 (exp_next/exp5/bc_train.py)

Target label2 (13 classes), beta 0.1 weights, hold-out 10% of fitting clips, 40000 steps x batch 1024, lr 0.0003; checkpoint = lowest hold-out weighted CE (every 2000). R^2 = expected offset vs the per-frame weighted mean of the target (the centred-label R^2; go/no-go threshold 0.10 at k5).

| k | seed | best step | hold-out CE | CE of per-frame prior | acc | R^2 centred | P(argmax = 0) | minutes |
|---|---|---|---|---|---|---|---|---|
| 5 | 3 | 16000 | 1.7135 | 2.0036 | 0.312 | 0.419 | 0.268 | 6.7 |
| 5 | 4 | 10000 | 1.7230 | 2.0036 | 0.311 | 0.413 | 0.330 | 7.5 |
| 5 | 5 | 6000 | 1.7097 | 2.0036 | 0.311 | 0.431 | 0.254 | 6.1 |

Hold-out clips are fitting clips (train minus the fold); the fold and val were never in the data.

