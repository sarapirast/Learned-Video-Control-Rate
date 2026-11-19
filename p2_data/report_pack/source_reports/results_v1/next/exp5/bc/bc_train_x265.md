# Exp 5b BC classifier, x265 (exp_next/exp5/bc_train.py)

Target label2 (13 classes), beta 0.1 weights, hold-out 10% of fitting clips, 40000 steps x batch 1024, lr 0.0003; checkpoint = lowest hold-out weighted CE (every 2000). R^2 = expected offset vs the per-frame weighted mean of the target (the centred-label R^2; go/no-go threshold 0.10 at k5).

| k | seed | best step | hold-out CE | CE of per-frame prior | acc | R^2 centred | P(argmax = 0) | minutes |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 38000 | 1.6443 | 2.1200 | 0.346 | 0.577 | 0.183 | 3.2 |
| 0 | 1 | 32000 | 1.6471 | 2.1200 | 0.343 | 0.578 | 0.148 | 3.1 |
| 0 | 2 | 40000 | 1.6449 | 2.1200 | 0.345 | 0.573 | 0.185 | 3.1 |
| 5 | 0 | 12000 | 1.6735 | 1.9706 | 0.323 | 0.402 | 0.266 | 3.1 |
| 5 | 1 | 10000 | 1.6734 | 1.9706 | 0.322 | 0.418 | 0.308 | 3.1 |
| 5 | 2 | 14000 | 1.6765 | 1.9706 | 0.324 | 0.411 | 0.219 | 3.1 |

Hold-out clips are fitting clips (train minus the fold); the fold and val were never in the data.

