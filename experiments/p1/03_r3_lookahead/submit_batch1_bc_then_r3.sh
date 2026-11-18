#!/bin/bash
# Batch 1 when job 1 has already run (normally use submit_batch1.sh): job 2 (BC k29 and k0 seed 3, one after the other), then the R3 array (k5, k0, k29
# seed 3) after it succeeds. Prints both job IDs. Run: bash submit_batch1_bc_then_r3.sh
set -euo pipefail
S=/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead
P=$(sbatch --parsable "$S/job2_bc_k29_k0_seed3.sbatch")
R=$(sbatch --parsable --dependency=afterok:$P "$S/train_r3.sbatch")
echo "bc $P -> rl array $R (afterok)"
