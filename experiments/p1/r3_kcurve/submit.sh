#!/bin/bash
# Submit prep, then the RL array after it succeeds. Prints both job IDs.
set -euo pipefail
S=/scratch1/ahhanagu/ee599/results/r3_kcurve/scripts
P=$(sbatch --parsable "$S/prep.sbatch")
R=$(sbatch --parsable --dependency=afterok:$P "$S/rl.sbatch")
echo "prep $P -> rl array $R (afterok)"
