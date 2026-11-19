# Exp 7 rule retuning, part 8, x265 (exp_next/exp7/rule_tune.py)

Val same-clip 8-GOP streams: 504 cases. 'As reported' = rule_wide.pkl (tuned by Pavneet on all val 8-GOP cases incl. mixed).

| L | as reported (m, qpd, cw) | its same-clip val score | retuned (m, qpd, cw) | retuned score | interior | settings tried |
|---|---|---|---|---|---|---|
| 0 | (0.98, 4.0, 3.0) | -0.6756 | (1.0, 5.0, 0.25) | -0.5063 | True | 567 |
| 2 | (0.98, 4.5, 6.0) | -0.4526 | (0.99, 4.5, 0.0625) | -0.2937 | True | 648 |
