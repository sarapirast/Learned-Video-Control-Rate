#!/bin/bash
# Batch 2: two independent chains (they can run side by side on different nodes). Run: bash submit_batch2.sh
#   A: job 4 (BC k29/k0 seeds 4,5) -> rl array A (k0 s4,s5; k29 s4,s5; k5 s4,s5), shifts = exp5/shifts_smooth.json
#   B: job 5 (k2/k10 data, shifts, BC seed 3) -> rl array B (k2 s3, k10 s3), shifts = exp5_k2k10/shifts_smooth.json
set -euo pipefail
S=/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead
B=/scratch1/ahhanagu/ee599/results/r3_kcurve
BA=$(sbatch --parsable "$S/job4_bc_k0_k29_seeds45.sbatch")
RA=$(sbatch --parsable --dependency=afterok:$BA --array=0-5 "$S/train_r3.sbatch" "$S/runs_batch2_k0_k29_k5_seeds45.txt")
PB=$(sbatch --parsable "$S/job5_prep_bc_k2_k10.sbatch")
RB=$(sbatch --parsable --dependency=afterok:$PB --array=0-1 "$S/train_r3.sbatch" "$S/runs_batch2_k2_k10_seed3.txt" "$B/exp5_k2k10/shifts_smooth.json")
echo "chain A: job4 $BA -> rl array $RA (6 runs)"
echo "chain B: job5 $PB -> rl array $RB (2 runs)"
