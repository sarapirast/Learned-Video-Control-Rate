# R3 with its own previous-GOP history (test; exp_next/fw/seq_history.py)

R3 k5, 180k model, seeds 3-5; 'stored' = final4's GOP n-1 history as replayed in every R3 number so far, 'own' = computed from R3's own encode of GOP n-1 (sequential per clip and level). 100 dB cap, hole excluded. Rule (exp_next/fw/PLAN.md): |pooled diff| <= 0.02 dB -> one sentence; larger -> escalate.

**POST-HOC deployment-faithful re-measurement on test (Aayush OK 11-17, option 1 after the val escalation):** the frozen R3 models of the 11-16 test pass, same test episodes, run in clip order with R3's own GOP n-1 history; no training, no choices. The pre-registered primary (final4's history) is unchanged.

## x264

- own - stored history, pooled: +0.004 [-0.004, +0.012] (n 993; 89 % of episodes used their own GOP n-1)
- by class: cut/gradual +0.006 [-0.019, +0.030]; stable +0.003 [-0.006, +0.012]
- by level: L24 +0.003; L30 -0.006; L36 -0.001; L42 +0.018
- R3 (stored history) - final4: +0.067 [+0.023, +0.107] *
- **R3 (own history) - final4: +0.071 [+0.024, +0.114] ***
- R3 (own history) - final4 by class: cut/gradual +0.066 [-0.056, +0.190]; stable +0.072 [+0.032, +0.110] *

| history   |    n |   score |     A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:----------|-----:|--------:|------:|-------:|---------------:|--------------:|---------------:|---------:|
| final4    |  993 |  -0.107 | 0.067 | -0.174 |          1.925 |         4.335 |         -0.17  |   54.683 |
| own       | 2979 |  -0.037 | 0.133 | -0.17  |          2.515 |         5.359 |         -1.49  |   23.229 |
| stored    | 2979 |  -0.04  | 0.131 | -0.171 |          2.531 |         5.485 |         -1.452 |   24.102 |

## x265

- own - stored history, pooled: -0.012 [-0.021, -0.004] * (n 994; 89 % of episodes used their own GOP n-1)
- by class: cut/gradual -0.016 [-0.030, -0.002] *; stable -0.011 [-0.020, -0.002] *
- by level: L24 -0.004; L30 +0.000; L36 -0.016; L42 -0.027
- R3 (stored history) - final4: +0.163 [+0.086, +0.251] *
- **R3 (own history) - final4: +0.151 [+0.078, +0.233] ***
- R3 (own history) - final4 by class: cut/gradual +0.086 [-0.024, +0.183]; stable +0.168 [+0.094, +0.257] *

| history   |    n |   score |      A |    E-P |   mean |err| % |   p90 |err| % |   signed err % |   % over |
|:----------|-----:|--------:|-------:|-------:|---------------:|--------------:|---------------:|---------:|
| final4    |  994 |  -0.185 | -0.03  | -0.155 |          1.634 |         3.755 |         -0.106 |   55.231 |
| own       | 2982 |  -0.034 |  0.116 | -0.149 |          2.24  |         3.979 |         -1.546 |   21.294 |
| stored    | 2982 |  -0.022 |  0.121 | -0.143 |          2.193 |         3.905 |         -1.548 |   21.261 |

- **Both encoders pooled: own - stored -0.004 [-0.010, +0.002]**

(pooled over encoders for the history effect only; R3 - final4 is per encoder, as pre-registered)
