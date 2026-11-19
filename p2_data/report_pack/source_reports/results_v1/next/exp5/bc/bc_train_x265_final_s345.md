# Exp 5b BC classifier, x265 (exp_next/exp5/bc_train.py)

Target label2 (13 classes), beta 0.1 weights, hold-out 10% of fitting clips, 40000 steps x batch 1024, lr 0.0003; checkpoint = lowest hold-out weighted CE (every 2000). R^2 = expected offset vs the per-frame weighted mean of the target (the centred-label R^2; go/no-go threshold 0.10 at k5).

| k | seed | best step | hold-out CE | CE of per-frame prior | acc | R^2 centred | P(argmax = 0) | minutes |
|---|---|---|---|---|---|---|---|---|
| 5 | 3 | 18000 | 1.6780 | 1.9706 | 0.329 | 0.405 | 0.227 | 3.2 |
| 5 | 4 | 24000 | 1.6784 | 1.9706 | 0.321 | 0.416 | 0.205 | 3.2 |
| 5 | 5 | 12000 | 1.6662 | 1.9706 | 0.327 | 0.415 | 0.241 | 3.2 |

Hold-out clips are fitting clips (train minus the fold); the fold and val were never in the data.

