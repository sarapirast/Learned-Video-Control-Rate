#!/bin/bash
# submit_x265.sh: the x265 lookahead runs (CLI backend: ~1.5-1.75 h per R3 run instead of ~4 min on the x264 shim).
#   job 6 (k29 data + shift with k5 checks, BC k29/k0 seeds 3-5) -> R3 array (k0, k29 x seeds 3-5)
#   job 7 (always, independent): Aayush's stored x265 k5 model evaluated with this x265 setup = his rows exactly
#   options: --r2c (R2c array k0/k29 x seeds 3-5, no dependency), --repro (R3 k5 seed 3, 180k, vs Aayush's model_180993),
#            --seeds1 (first round with seed 3 only: R3 tasks 0 and 3)
# Run: bash submit_x265.sh [--r2c] [--repro] [--seeds1]      Every job gets P1_ENC=x265 and a 4 h limit for RL (2x the slowest x265 180k run seen, ~115 min); dependants are cancelled automatically if job 6 fails.
set -euo pipefail
S=/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead
SH=/scratch1/ahhanagu/ee599/results/r3_kcurve/exp5_x265/shifts_smooth.json
X=(--export=ALL,P1_ENC=x265)
ARR=0-5; [[ " $* " == *" --seeds1 "* ]] && ARR=0,3
P=$(sbatch --parsable "${X[@]}" "$S/job6_prep_bc_x265_k0_k29.sbatch")
R=$(sbatch --parsable "${X[@]}" --time=4:00:00 --kill-on-invalid-dep=yes --dependency=afterok:$P --array=$ARR --job-name=r3k_x265_r3 \
      "$S/train_r3.sbatch" "$S/runs_x265_r3_k0_k29.txt" "$SH")
echo "job6 $P -> R3 x265 array $R (tasks $ARR)"
V=$(sbatch --parsable "${X[@]}" "$S/../04_r2c_control/job7_reeval_x265_k5.sbatch")   # eval-only check, no dependency
echo "job7 eval-only x265 check $V"
if [[ " $* " == *" --r2c "* ]]; then      # R2c needs no BC; it needs the shifts file (k0 in Aayush's, k29 from job 6)
  C=$(sbatch --parsable "${X[@]}" --time=4:00:00 --kill-on-invalid-dep=yes --dependency=afterok:$P --array=$ARR --job-name=r3k_x265_r2c \
        "$S/train_r3.sbatch" "$S/../04_r2c_control/runs_x265_r2c_k0_k29.txt" "$SH")
  echo "R2c x265 array $C"
fi
if [[ " $* " == *" --repro "* ]]; then
  Q=$(sbatch --parsable "${X[@]}" --time=4:00:00 --kill-on-invalid-dep=yes --dependency=afterok:$P --array=0 --job-name=r3k_x265_repro \
        "$S/train_r3.sbatch" "$S/runs_x265_k5_s3_repro.txt" "$SH")
  echo "repro x265 k5 s3 $Q"
fi
