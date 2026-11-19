# Exp 7 rule retuning, part chain, x265 (exp_next/exp7/rule_tune.py)

Train chains bbb + sintel (6 clips each, in clip order; segments far apart in the films, so every join every 10 GOPs acts like a scene cut), windows of 16 / 32 GOPs, stride 4. Descriptive val check on the sita chain with the train-chain settings.

| N | L | retuned (m, qpd, cw) | train-chain score | interior | sita (val) score, retuned | sita, 8-GOP rule as reported |
|---|---|---|---|---|---|---|
| 16 | 0 | (0.99, 5.0, 0.0625) | -0.6701 | False | -0.7537 | -0.7442 |
| 16 | 2 | (1.0, 4.5, 1.0) | -0.4700 | True | -0.3888 | -0.3830 |
| 32 | 0 | (1.0, 5.0, 0.0625) | -0.8137 | False | -0.5466 | -0.5305 |
| 32 | 2 | (1.0, 5.0, 3.0) | -0.6212 | True | -0.2151 | -0.2305 |
