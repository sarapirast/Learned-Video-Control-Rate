# Exp 7 rule retuning, part 8, x264 (exp_next/exp7/rule_tune.py)

Val same-clip 8-GOP streams: 504 cases. 'As reported' = rule_wide.pkl (tuned by Pavneet on all val 8-GOP cases incl. mixed).

| L | as reported (m, qpd, cw) | its same-clip val score | retuned (m, qpd, cw) | retuned score | interior | settings tried |
|---|---|---|---|---|---|---|
| 0 | (0.98, 4.5, 3.0) | -0.7686 | (1.0, 5.5, 0.125) | -0.6158 | True | 729 |
| 2 | (0.98, 4.5, 3.0) | -0.6225 | (0.99, 5.0, 0.125) | -0.4971 | True | 729 |
