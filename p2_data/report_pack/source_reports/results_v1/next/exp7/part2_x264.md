# Exp 7 Part 2: zero-shot hierarchy, x264, val (exp_next/exp7/part2.py, part2_report.py)

**Descriptive only** (pre-registered): few same-clip streams; the retuned rule was tuned on these streams. 504 cases, 9 source groups; bc_ppo = Pavneet's stored BC->PPO L = 2, seeds 0-2 averaged per case; final4 = 1.0:6:1.0:2:3:4:1:1:1:0:3 at k5 inside each GOP at B_g = the stream controller's own predicted spend; history from the stream's previous GOP.

| system | score | dPSNR_B | signed spend err % | % streams > 1 % over | p90 abs err % |
|---|---|---|---|---|---|
| stream RL (bc_ppo) + constant QP | -0.4694 | -0.3813 | -3.56 | 12.7 | 11.80 |
| stream RL (bc_ppo) + final4 | +0.2590 | +0.4710 | -1.93 | 17.3 | 11.31 |
| retuned rule + constant QP | -0.4995 | -0.3751 | -1.86 | 22.4 | 7.40 |
| retuned rule + final4 | +0.5431 | +0.5989 | -0.42 | 6.3 | 1.86 |

Paired differences (cluster bootstrap over source groups):

- RL + final4 - RL + constant QP: +0.728 [-0.121, +3.474]
- rule + final4 - rule + constant QP: +1.043 [+0.088, +4.102]
- RL + final4 - rule + final4: -0.284 [-0.534, -0.120]
- RL + constant QP - rule + constant QP (= Part 1): +0.030 [-0.127, +0.401]
- RL + final4 - rule + constant QP: +0.758 [-0.153, +3.497]

Per-GOP check with final4 inside, |GOP bits - B_g| / B_g (%):

| controller | GOPs | mean | median | p90 | max | signed mean |
|---|---|---|---|---|---|---|
| bc_ppo | 12096 | 3.58 | 0.52 | 9.31 | 132.88 | +0.57 |
| rule | 4032 | 3.81 | 0.51 | 10.07 | 365.53 | +0.48 |

Check (mean about 2 % or less): NOT met

