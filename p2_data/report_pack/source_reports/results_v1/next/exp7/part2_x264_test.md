# Exp 7 Part 2: zero-shot hierarchy, x264, val (exp_next/exp7/part2.py, part2_report.py)

**Descriptive only** (pre-registered): few same-clip streams; the retuned rule was tuned on these streams. 972 cases, 12 source groups; bc_ppo = Pavneet's stored BC->PPO L = 2, seeds 0-2 averaged per case; final4 = 1.0:6:1.0:2:3:4:1:1:1:0:3 at k5 inside each GOP at B_g = the stream controller's own predicted spend; history from the stream's previous GOP.

| system | score | dPSNR_B | signed spend err % | % streams > 1 % over | p90 abs err % |
|---|---|---|---|---|---|
| stream RL (bc_ppo) + constant QP | -0.3715 | -0.3065 | -2.99 | 12.0 | 9.27 |
| stream RL (bc_ppo) + final4 | -0.0242 | +0.2315 | -1.08 | 13.5 | 9.89 |
| retuned rule + constant QP | -0.3457 | -0.1915 | -0.69 | 26.4 | 5.90 |
| retuned rule + final4 | +0.3642 | +0.4266 | -0.02 | 8.2 | 1.15 |

Paired differences (cluster bootstrap over source groups):

- RL + final4 - RL + constant QP: +0.347 [-0.161, +0.939]
- rule + final4 - rule + constant QP: +0.710 [+0.194, +1.307]
- RL + final4 - rule + final4: -0.388 [-0.517, -0.265]
- RL + constant QP - rule + constant QP (= Part 1): -0.026 [-0.090, +0.035]
- RL + final4 - rule + constant QP: +0.322 [-0.185, +0.865]

Per-GOP check with final4 inside, |GOP bits - B_g| / B_g (%):

| controller | GOPs | mean | median | p90 | max | signed mean |
|---|---|---|---|---|---|---|
| bc_ppo | 23328 | 2.97 | 0.48 | 5.17 | 231.31 | +0.50 |
| rule | 7776 | 2.60 | 0.45 | 4.48 | 121.71 | +0.03 |

Check (mean about 2 % or less): NOT met

