# R3 with its own previous-GOP history (val; exp_next/fw/seq_history.py)

R3 k5, 180k model, seeds 3-5; 'stored' = final4's GOP n-1 history as replayed in every R3 number so far, 'own' = computed from R3's own encode of GOP n-1 (sequential per clip and level). 100 dB cap, hole excluded. Rule (exp_next/fw/PLAN.md): |pooled diff| <= 0.02 dB -> one sentence; larger -> escalate.

EXPLORATORY (val).

## x264

- own - stored history, pooled: -0.013 [-0.023, -0.002] * (n 548; 89 % of episodes used their own GOP n-1)
- by class: cut/gradual -0.018 [-0.034, -0.006] *; stable -0.012 [-0.024, -0.001] *
- by level: L24 -0.010; L30 -0.012; L36 -0.004; L42 -0.025
- R3 (stored history) - final4: +0.077 [+0.022, +0.145] *
- **R3 (own history) - final4: +0.064 [+0.007, +0.131] ***
- R3 (own history) - final4 by class: cut/gradual +0.052 [-0.102, +0.191]; stable +0.067 [+0.006, +0.137] *

| history   |    n |   score |     A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:----------|-----:|--------:|------:|-------:|---------------:|--------------:|---------------:|---------:|
| final4    |  548 |  -0.115 | 0.07  | -0.185 |          1.84  |         3.687 |          0.413 |   55.657 |
| own       | 1644 |  -0.051 | 0.126 | -0.176 |          2.436 |         6.038 |         -1.249 |   22.993 |
| stored    | 1644 |  -0.038 | 0.13  | -0.168 |          2.429 |         5.969 |         -1.382 |   22.871 |

## x265

- own - stored history, pooled: -0.041 [-0.081, -0.011] * (n 550; 89 % of episodes used their own GOP n-1)
- by class: cut/gradual +0.006 [-0.020, +0.067]; stable -0.050 [-0.099, -0.009] *
- by level: L24 -0.025; L30 +0.004; L36 -0.013; L42 -0.130
- R3 (stored history) - final4: +0.209 [+0.085, +0.346] *
- **R3 (own history) - final4: +0.168 [+0.072, +0.275] ***
- R3 (own history) - final4 by class: cut/gradual +0.133 [-0.081, +0.556]; stable +0.174 [+0.083, +0.278] *

| history   |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:----------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| final4    |  550 |  -0.254 | -0.084 | -0.17  |          1.627 |         3.448 |          0.344 |   50.364 |
| own       | 1650 |  -0.086 |  0.078 | -0.164 |          2.321 |         5.307 |         -1.293 |   18.545 |
| stored    | 1650 |  -0.045 |  0.105 | -0.151 |          2.305 |         4.701 |         -1.517 |   15.818 |

- **Both encoders pooled: own - stored -0.027 [-0.049, -0.010] ***

