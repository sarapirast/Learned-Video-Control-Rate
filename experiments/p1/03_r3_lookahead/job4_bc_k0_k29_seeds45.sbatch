#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=48G
#SBATCH --time=1:00:00
#SBATCH --job-name=r3k_bc2
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%j.out
# Job 4 of 03_r3_lookahead (batch 2, chain A): BC networks for seeds 4 and 5 at k29 (my k29 data) and k0 (Aayush's
# k0 data). Run: submit_batch2.sh (queues R3 array A after it). Outputs: $B/exp5/bc/bc_x264_k{29,0}_s{4,5}.pt.
# One bc_train.py at a time
# (16 threads; two at once oversubscribe the cores ~20x, job 14304096). A network that exists is skipped.
set -euo pipefail
source /scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead/env.sh
E=$B/exp5
BC=$REPO/p2_data/exp_next/exp5/bc_train.py
train() {   # train <k> <data dir>: seeds 4,5 in one process (data loaded once)
  local todo=()
  for s in 4 5; do [[ -f $E/bc/bc_x264_k$1_s$s.pt ]] && echo "k$1 s$s: exists, skipped" || todo+=($s); done
  (( ${#todo[@]} )) || return 0
  local seeds; seeds=$(IFS=,; echo "${todo[*]}")
  echo "$(date +%T) BC k$1 seeds $seeds ($SLURM_CPUS_PER_TASK threads)"
  $PY -W ignore "$BC" --ks "$1" --seeds "$seeds" --data "$2" --out "$E/bc" --tag "k$1_s${seeds//,/}" \
      > "$B/logs/bc_k$1_s${seeds//,/}-$SLURM_JOB_ID.log" 2>&1
  grep -E '^\| [0-9]+ \| [0-9]' "$B/logs/bc_k$1_s${seeds//,/}-$SLURM_JOB_ID.log" || true
}
train 29 "$E"
train 0 /scratch1/aayushso/ee599/results_v1/next/exp5
for k in 29 0; do for s in 4 5; do test -f "$E/bc/bc_x264_k${k}_s$s.pt"; done; done
rm -rf "$RC_TMP"
echo "$(date +%T) BC2 done"
