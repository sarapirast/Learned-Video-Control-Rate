# Exp 5b BC classifier, x264 (exp_next/exp5/bc_train.py)

Target label2 (13 classes), beta 0.1 weights, hold-out 10% of fitting clips, 40000 steps x batch 1024, lr 0.0003; checkpoint = lowest hold-out weighted CE (every 2000). R^2 = expected offset vs the per-frame weighted mean of the target (the centred-label R^2; go/no-go threshold 0.10 at k5).

| k | seed | best step | hold-out CE | CE of per-frame prior | acc | R^2 centred | P(argmax = 0) | minutes |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 30000 | 1.6960 | 2.1347 | 0.324 | 0.566 | 0.165 | 5.9 |
| 0 | 1 | 26000 | 1.6800 | 2.1347 | 0.329 | 0.582 | 0.181 | 5.2 |
| 0 | 2 | 18000 | 1.6854 | 2.1347 | 0.325 | 0.583 | 0.162 | 5.2 |
| 5 | 0 | 10000 | 1.7206 | 2.0036 | 0.307 | 0.415 | 0.231 | 4.8 |
| 5 | 1 | 4000 | 1.7252 | 2.0036 | 0.304 | 0.407 | 0.278 | 5.1 |
| 5 | 2 | 8000 | 1.7226 | 2.0036 | 0.308 | 0.406 | 0.242 | 4.8 |

Hold-out clips are fitting clips (train minus the fold); the fold and val were never in the data.

