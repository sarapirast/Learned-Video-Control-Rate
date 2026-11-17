#!/bin/bash
# Submit the BC stage, then the RL array after it succeeds (replaces submit.sh's prep stage, whose steps 1-3 are done).
set -euo pipefail
S=/scratch1/ahhanagu/ee599/results/r3_kcurve/scripts
P=$(sbatch --parsable "$S/bc.sbatch")
R=$(sbatch --parsable --dependency=afterok:$P "$S/rl.sbatch")
echo "bc $P -> rl array $R (afterok)"
