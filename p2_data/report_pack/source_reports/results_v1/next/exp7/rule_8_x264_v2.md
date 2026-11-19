# Exp 7 rule retuning, part 8, x264 (exp_next/exp7/rule_tune.py)

Val same-clip 8-GOP streams: 504 cases. 'As reported' = rule_wide.pkl (tuned by Pavneet on all val 8-GOP cases incl. mixed).

| L | as reported (m, qpd, cw) | its same-clip val score | retuned (m, qpd, cw) | retuned score | interior | settings tried |
|---|---|---|---|---|---|---|
| 0 | (0.98, 4.5, 3.0) | -0.7686 | (1.0, 5.5, 0.015625) | -0.6151 | True | 729 |
| 2 | (0.98, 4.5, 3.0) | -0.6225 | (1.0, 5.0, 0.0625) | -0.4995 | True | 648 |
