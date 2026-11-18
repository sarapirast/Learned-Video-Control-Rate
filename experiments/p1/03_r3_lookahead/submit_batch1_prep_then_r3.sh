#!/bin/bash
# Batch 1, as first submitted: job 1 (BC data + shift + BC for k29/k0 seed 3), then the R3 array (k5, k0, k29 seed 3)
# after it succeeds. Prints both job IDs. Run: bash submit_batch1_prep_then_r3.sh
# (Job 1's step 4 timed out, see its header; the rerun used submit_batch1_bc_then_r3.sh.)
set -euo pipefail
S=/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead
P=$(sbatch --parsable "$S/job1_prep_k29.sbatch")
R=$(sbatch --parsable --dependency=afterok:$P "$S/train_r3.sbatch")
echo "prep $P -> rl array $R (afterok)"
