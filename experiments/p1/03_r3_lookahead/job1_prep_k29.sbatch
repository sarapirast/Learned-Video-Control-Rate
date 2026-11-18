#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=48G
#SBATCH --time=0:45:00
#SBATCH --job-name=r3k_prep
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%j.out
# Job 1 of 03_r3_lookahead (batch 1): BC data and mean shift for R3 at k29 (x264), with the team's Exp 5b recipe,
# plus the k5 reproduction checks. No encodes, ~10 min. The BC networks (k29, k0) are job 2.
# Run: bash submit_batch1.sh (job 1 -> job 2 -> R3 array), or sbatch job1_prep_k29.sbatch.
# Inputs: Aayush's search plans / infos / fold (read-only), his shifts_smooth.json and k5 data (for the checks).
# Outputs: $B/exp5/ (data_x264_k*.npz, data_v2_x264_k*.npz, plans*.pkl, shifts_smooth.json).
# History: as first run (job 14304096) this job also had a step 4 that trained both BC networks at once; two
# bc_train.py with 16 threads each oversubscribe the 16 cores ~20x, so it hit the time limit. Steps 1-3 passed.
# Step 4 now lives only in job 2, which trains the networks one after the other.
#   1. bc_data_build.py (P1 copy of build.py) at k5 + k29: BC dataset v1 -> check k5's smooth shift == Aayush's
#   2. k29 smooth pooled shift (shift_smooth.py's fit) -> exp5/shifts_smooth.json = Aayush's file + x264|29|*
#   3. bc_data_build.py --v2 at k5 + k29 -> check k5's v2 data == Aayush's data_v2_x264_k5.npz (as a set of rows)
# Every check must pass or the job stops (and the jobs that depend on it never start).
set -euo pipefail
source /scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead/env.sh
E=$B/exp5; W=$(( SLURM_CPUS_PER_TASK - 1 ))   # S (script folder) comes from env.sh
cd "$S"                                  # the bc_*.py helpers are called by name
echo "$(date +%T) step 1: v1 data k5,k29"
EXP5_KS=5,29 $PY -W ignore bc_data_build.py --workers $W --out "$E" | tail -3
EXP5_KS=5 $PY -I bc_shift_fit.py "$E" --check
echo "$(date +%T) step 2: k29 shift"
EXP5_KS=29 $PY -I bc_shift_fit.py "$E"
echo "$(date +%T) step 3: v2 data k5,k29 (RC_SHIFTS=$RC_SHIFTS)"
EXP5_KS=5,29 $PY -W ignore bc_data_build.py --v2 --workers $W --out "$E" | tail -3
$PY -I bc_data_compare.py "$E" v2 5
for f in data_v2_x264_k29.npz plans_v2_x264.pkl shifts_smooth.json; do test -s "$E/$f"; done   # what job 2 needs
rm -rf "$RC_TMP"
echo "$(date +%T) prep done (BC networks: job 2)"
