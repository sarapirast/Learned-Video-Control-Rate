#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=48G
#SBATCH --time=0:45:00
#SBATCH --job-name=r3k_bc
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%j.out
# Job 2 of 03_r3_lookahead (batch 1): the two BC networks (x264, seed 3, k29 then k0).
# Run: submit_batch1_bc_then_r3.sh (queues the R3 array after it), or sbatch job2_bc_k29_k0_seed3.sbatch.
# Inputs: $B/exp5/ from job 1 steps 1-3; Aayush's k0 BC data (read-only). Outputs: $B/exp5/bc/bc_x264_k{29,0}_s3.pt,
# logs in $B/logs/bc_k*-<jobid>.log.
# Replaces step 4 of job1_prep_k29.sbatch (job 14304096 finished steps 1-3: k5 shift
# and k5 v2 data identical to Aayush's, k29 shift + data written, then timed out in step 4).
# Step 4 timed out because two bc_train.py ran at once, each with torch.set_num_threads(SLURM_CPUS_PER_TASK = 16):
# 32 threads on 16 cores ran ~20x slower. Here they run one after the other with 16 threads each, as Aayush ran BC
# (~7 min per network). A network that already exists is skipped, so a rerun only does what is missing.
set -euo pipefail
source /scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead/env.sh
E=$B/exp5
BC=$REPO/p2_data/exp_next/exp5/bc_train.py
for f in data_v2_x264_k29.npz plans_v2_x264.pkl shifts_smooth.json; do test -s "$E/$f"; done   # outputs of steps 1-3
train() {   # train <k> <data dir>
  if [[ -f $E/bc/bc_x264_k$1_s3.pt ]]; then echo "k$1: exists, skipped"; return; fi
  echo "$(date +%T) BC k$1 seed 3 ($SLURM_CPUS_PER_TASK threads)"
  $PY -W ignore "$BC" --ks "$1" --seeds 3 --data "$2" --out "$E/bc" --tag "k$1_s3" > "$B/logs/bc_k$1-$SLURM_JOB_ID.log" 2>&1
  tail -4 "$B/logs/bc_k$1-$SLURM_JOB_ID.log" | head -1
}
train 29 "$E"
train 0 /scratch1/aayushso/ee599/results_v1/next/exp5
ls -la "$E/bc"
test -f "$E/bc/bc_x264_k29_s3.pt" && test -f "$E/bc/bc_x264_k0_s3.pt"
rm -rf "$RC_TMP"
echo "$(date +%T) BC done"
