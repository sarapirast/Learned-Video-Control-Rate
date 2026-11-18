#!/bin/bash
# submit_batch1.sh: batch 1 of 03_r3_lookahead in one go, each job starting only if the previous one succeeded:
#   job 1 (k29 BC data + shift, k5 checks) -> job 2 (BC k29 and k0, seed 3, one after the other)
#   -> R3 array (train_r3.sbatch, runs_batch1_k5_k0_k29_seed3.txt: k5, k0, k29 seed 3).
# Run: bash submit_batch1.sh   (prints the three job IDs). If job 1 has already run, use submit_batch1_bc_then_r3.sh.
set -euo pipefail
S=/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead
P=$(sbatch --parsable "$S/job1_prep_k29.sbatch")
C=$(sbatch --parsable --dependency=afterok:$P "$S/job2_bc_k29_k0_seed3.sbatch")
R=$(sbatch --parsable --dependency=afterok:$C "$S/train_r3.sbatch")
echo "job1 $P -> job2 $C -> R3 array $R (afterok)"
