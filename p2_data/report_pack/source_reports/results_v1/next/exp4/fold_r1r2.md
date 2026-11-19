# Exp 4 R3 precondition: R2 vs R1 on the fold, k5 (exp_next/exp4/fold_r1r2.py)

Stored 180k models, seeds averaged per episode, paired, 95% clip bootstrap over the 8 fold clips, hole excluded. Rule (PREREG_BC.md REVISION 1): R2's setup unless R2 - R1 CI is entirely below 0.

- R2 - R1 pooled: +0.093 [+0.068, +0.121] * (n 583)
- x264: R2 - R1 +0.178 [+0.126, +0.226] *; R2 - final4 +0.055 [+0.016, +0.100] *; R1 - final4 -0.122 [-0.191, -0.049] *
- x265: R2 - R1 +0.009 [-0.029, +0.048]; R2 - final4 +0.039 [-0.045, +0.139]; R1 - final4 +0.030 [-0.046, +0.124]
- **R2 setup stands for R3**

