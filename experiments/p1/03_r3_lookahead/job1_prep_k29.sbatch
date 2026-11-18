#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=48G
#SBATCH --time=1:30:00
#SBATCH --job-name=r3k_prep
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%j.out
# Job 1 of 03_r3_lookahead (batch 1): BC data, shift and BC networks for R3 at k29 and k0 (x264, seed 3), with the
# team's Exp 5b recipe. No encodes.
# Run: sbatch job1_prep_k29.sbatch, or submit_batch1_prep_then_r3.sh (also queues the R3 array after it).
# Inputs: Aayush's search plans / infos / fold (read-only), his shifts_smooth.json and k5 data (for the checks).
# Outputs: $B/exp5/ (data_x264_k*.npz, data_v2_x264_k*.npz, plans*.pkl, shifts_smooth.json, bc/bc_x264_k*_s3.pt).
# KNOWN ISSUE (as run, job 14304096): step 4 starts two bc_train.py at once, each with 16 threads, which
# oversubscribes the 16 cores ~20x and hits the time limit. Steps 1-3 finished and passed; job2 then did step 4.
#   1. bc_data_build.py (P1 copy of build.py) at k5 + k29: BC dataset v1 -> check k5's smooth shift == Aayush's
#   2. k29 smooth pooled shift (shift_smooth.py's fit) -> exp5/shifts_smooth.json = Aayush's file + x264|29|*
#   3. bc_data_build.py --v2 at k5 + k29 -> check k5's v2 data == Aayush's data_v2_x264_k5.npz (as a set of rows)
#   4. bc_train.py (team copy, unchanged) seed 3: k29 on the new data, k0 on Aayush's existing k0 data
# Every check must pass or the job stops (and the RL array, which depends on it, never starts).
set -euo pipefail
source /scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead/env.sh
E=$B/exp5; W=$(( SLURM_CPUS_PER_TASK - 1 ))   # S (script folder) comes from env.sh
BC=$REPO/p2_data/exp_next/exp5/bc_train.py
cd "$S"                                  # the bc_*.py helpers are called by name
echo "$(date +%T) step 1: v1 data k5,k29"
EXP5_KS=5,29 $PY -W ignore bc_data_build.py --workers $W --out "$E" | tail -3
EXP5_KS=5 $PY -I bc_shift_fit.py "$E" --check
echo "$(date +%T) step 2: k29 shift"
EXP5_KS=29 $PY -I bc_shift_fit.py "$E"
echo "$(date +%T) step 3: v2 data k5,k29 (RC_SHIFTS=$RC_SHIFTS)"
EXP5_KS=5,29 $PY -W ignore bc_data_build.py --v2 --workers $W --out "$E" | tail -3
$PY -I bc_data_compare.py "$E" v2 5
echo "$(date +%T) step 4: BC seed 3 at k29 (new data) and k0 (Aayush's data), in parallel"
$PY -W ignore "$BC" --ks 29 --seeds 3 --data "$E" --out "$E/bc" --tag k29_s3 > "$B/logs/bc_k29.log" 2>&1 &
P1=$!
$PY -W ignore "$BC" --ks 0 --seeds 3 --data /scratch1/aayushso/ee599/results_v1/next/exp5 --out "$E/bc" --tag k0_s3 \
    > "$B/logs/bc_k0.log" 2>&1 &
P2=$!
wait $P1; wait $P2
ls -la "$E/bc"
test -f "$E/bc/bc_x264_k29_s3.pt" && test -f "$E/bc/bc_x264_k0_s3.pt"
rm -rf "$RC_TMP"
echo "$(date +%T) prep done"
