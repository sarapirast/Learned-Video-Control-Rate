#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G
#SBATCH --time=1:15:00
#SBATCH --job-name=r3k_prep2
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%j.out
# Batch 2, k2 and k10 (seed 3): same chain as k29 (prep.sbatch steps 1-3 + bc.sbatch), into exp5_k2k10/.
#   1. exp5_build.py v1 at k5,2,10 -> k5 smooth shift must equal Aayush's (else stop)
#   2. k2, k10 smooth shifts -> exp5_k2k10/shifts_smooth.json = exp5/shifts_smooth.json (Aayush's k0/k5 + my k29) + k2, k10
#   3. exp5_build.py --v2 at k5,2,10 -> k5 v2 data must equal Aayush's as a set of rows (else stop)
#   4. bc_train.py seed 3 at k2 then k10, one process (16 threads), networks into exp5/bc
# No encodes. 64G: three k in memory at once (prep.sbatch held two in 48G).
set -euo pipefail
source /scratch1/ahhanagu/ee599/results/r3_kcurve/scripts/env.sh
E=$B/exp5_k2k10; S=$B/scripts; W=$(( SLURM_CPUS_PER_TASK - 1 ))
BC=$REPO/p2_data/exp_next/exp5/bc_train.py
mkdir -p "$E"; cd "$S"
if [[ ! -f $E/shifts_smooth.json ]]; then
  echo "$(date +%T) step 1: v1 data k5,2,10"
  EXP5_KS=5,2,10 $PY -W ignore exp5_build.py --workers $W --out "$E" | tail -2
  EXP5_KS=5 $PY -I exp5_shift.py "$E" --check
  echo "$(date +%T) step 2: k2, k10 shifts"
  EXP5_KS=2,10 $PY -I exp5_shift.py "$E" --base "$B/exp5/shifts_smooth.json"
fi
if [[ ! -f $E/data_v2_x264_k10.npz ]]; then
  echo "$(date +%T) step 3: v2 data k5,2,10"
  RC_SHIFTS=$E/shifts_smooth.json EXP5_KS=5,2,10 $PY -W ignore exp5_build.py --v2 --workers $W --out "$E" | tail -2
  $PY -I exp5_compare.py "$E" v2 5
fi
if [[ -f $B/exp5/bc/bc_x264_k2_s3.pt && -f $B/exp5/bc/bc_x264_k10_s3.pt ]]; then
  echo "BC k2, k10: exist, skipped"
else
  echo "$(date +%T) step 4: BC seed 3 at k2, k10 ($SLURM_CPUS_PER_TASK threads, one process)"
  $PY -W ignore "$BC" --ks 2,10 --seeds 3 --data "$E" --out "$B/exp5/bc" --tag k2k10_s3 > "$B/logs/bc_k2k10-$SLURM_JOB_ID.log" 2>&1
  grep -E '^\| [0-9]+ \| [0-9]' "$B/logs/bc_k2k10-$SLURM_JOB_ID.log" || true
fi
test -f "$B/exp5/bc/bc_x264_k2_s3.pt" && test -f "$B/exp5/bc/bc_x264_k10_s3.pt"
rm -rf "$RC_TMP"
echo "$(date +%T) prep2 done"
