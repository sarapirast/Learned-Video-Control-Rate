#!/bin/bash
# Batch 2: two independent chains (they can run side by side on different nodes).
#   A: bc2 (BC k29/k0 seeds 4,5) -> rl array A (k0 s4,s5; k29 s4,s5; k5 s4,s5), shifts = exp5/shifts_smooth.json
#   B: prep2 (k2/k10 data, shifts, BC seed 3) -> rl array B (k2 s3, k10 s3), shifts = exp5_k2k10/shifts_smooth.json
set -euo pipefail
S=/scratch1/ahhanagu/ee599/results/r3_kcurve/scripts
B=/scratch1/ahhanagu/ee599/results/r3_kcurve
BA=$(sbatch --parsable "$S/bc2.sbatch")
RA=$(sbatch --parsable --dependency=afterok:$BA --array=0-5 "$S/rl.sbatch" "$S/runs_b2a.txt")
PB=$(sbatch --parsable "$S/prep2.sbatch")
RB=$(sbatch --parsable --dependency=afterok:$PB --array=0-1 "$S/rl.sbatch" "$S/runs_b2b.txt" "$B/exp5_k2k10/shifts_smooth.json")
echo "chain A: bc2 $BA -> rl array $RA (6 runs)"
echo "chain B: prep2 $PB -> rl array $RB (2 runs)"
