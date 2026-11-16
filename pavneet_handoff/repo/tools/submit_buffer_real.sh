#!/bin/bash
# D40 for one encoder: live channel with the real encoder in the loop (experiments/buffer_real.py).
#   run    : runs/buffer_real.txt (44 shards: default channel val 4 / test 12 / test16 12, LTE traces val 4 / test 12),
#            at most 6 at a time, 2 CPU / 8 GB each
#   report : runs/buffer_real_report.txt (default, trace), after all shards
# usage: bash tools/submit_buffer_real.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
sb() { sbatch --parsable --export=ALL $P "$@"; }
N=$(( $(wc -l < runs/buffer_real.txt) - 1 ))
RU=$(sb --time=3:00:00 --array=0-$N%6 --job-name=${E}_d40_real tools/real_task.sbatch runs/buffer_real.txt)
REP=$(sb --time=0:20:00 --array=0-1 --dependency=afterany:$RU --job-name=${E}_d40_report tools/real_task.sbatch runs/buffer_real_report.txt)
echo "$E d40 real $RU / report $REP"
