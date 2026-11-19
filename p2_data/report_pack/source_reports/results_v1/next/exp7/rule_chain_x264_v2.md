# Exp 7 rule retuning, part chain, x264 (exp_next/exp7/rule_tune.py)

Train chains bbb + sintel (6 clips each, in clip order; segments far apart in the films, so every join every 10 GOPs acts like a scene cut), windows of 16 / 32 GOPs, stride 4. Descriptive val check on the sita chain with the train-chain settings.

| N | L | retuned (m, qpd, cw) | train-chain score | interior | sita (val) score, retuned | sita, 8-GOP rule as reported |
|---|---|---|---|---|---|---|
| 16 | 0 | (1.0, 5.0, 0.0625) | -0.6774 | True | -0.6981 | -0.7000 |
| 16 | 2 | (0.99, 5.5, 0.015625) | -0.4863 | True | -0.3188 | -0.3693 |
| 32 | 0 | (1.0, 5.5, 1e-06) | -0.8150 | True (cw at 0+ limit) | -0.4718 | -0.4860 |
| 32 | 2 | (1.0, 5.5, 0.015625) | -0.6201 | True | -0.2165 | -0.2304 |
