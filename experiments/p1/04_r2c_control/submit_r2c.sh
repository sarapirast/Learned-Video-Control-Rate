#!/bin/bash
# submit_r2c.sh: queue the R2c control runs (R3's recipe without the BC start) as one array of 7 rl.py runs:
#   tasks 0-2 = k0 seeds 3-5, tasks 3-5 = k29 seeds 3-5, task 6 = k5 seed 0 (reproduces Aayush's stored R2c run).
# Uses 03_r3_lookahead/train_r3.sbatch and env.sh (default shifts file: k0, k5, k29). No BC stage, no dependency.
# Run: bash submit_r2c.sh        (as run on 2026-11-16: job 14308917)
# Outputs: /scratch1/ahhanagu/ee599/results/r3_kcurve/work/results_rl/res_k*_..._meanpooled_wu20k_s*/ ("no bcinit")
set -euo pipefail
P1=/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1
J=$(sbatch --parsable --array=0-6 --job-name=r3k_r2c "$P1/03_r3_lookahead/train_r3.sbatch" "$P1/04_r2c_control/runs_r2c.txt")
echo "R2c array $J (7 runs)"
