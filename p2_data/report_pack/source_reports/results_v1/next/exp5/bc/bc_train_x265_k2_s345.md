# Exp 5b BC classifier, x265 (exp_next/exp5/bc_train.py)

Target label2 (13 classes), beta 0.1 weights, hold-out 10% of fitting clips, 40000 steps x batch 1024, lr 0.0003; checkpoint = lowest hold-out weighted CE (every 2000). R^2 = expected offset vs the per-frame weighted mean of the target (the centred-label R^2; go/no-go threshold 0.10 at k5).

| k | seed | best step | hold-out CE | CE of per-frame prior | acc | R^2 centred | P(argmax = 0) | minutes |
|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 26000 | 1.6564 | 2.0541 | 0.334 | 0.517 | 0.208 | 19.2 |
| 2 | 4 | 24000 | 1.6468 | 2.0541 | 0.337 | 0.531 | 0.184 | 3.8 |
| 2 | 5 | 18000 | 1.6585 | 2.0541 | 0.335 | 0.517 | 0.185 | 4.7 |

Hold-out clips are fitting clips (train minus the fold); the fold and val were never in the data.

