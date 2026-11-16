#!/bin/bash
# D41 for one encoder: hindsight oracle on the live-channel task (experiments/buffer_oracle.py). Lookups only, no encodes.
#   run    : runs/buffer_oracle.txt (16 shards: default channel test 4 / test16 4, LTE traces test 4 / test16 4),
#            at most 6 at a time, 2 CPU / 8 GB, 1 h each
#   report : runs/buffer_oracle_report.txt (default, trace), after all shards
# usage: bash tools/submit_buffer_oracle.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
sb() { sbatch --parsable --export=ALL $P "$@"; }
N=$(( $(wc -l < runs/buffer_oracle.txt) - 1 ))
RU=$(sb --time=1:00:00 --array=0-$N%6 --job-name=${E}_d41_oracle tools/oracle_task.sbatch runs/buffer_oracle.txt)
REP=$(sb --time=0:20:00 --array=0-1 --dependency=afterany:$RU --job-name=${E}_d41_report tools/oracle_task.sbatch runs/buffer_oracle_report.txt)
echo "$E d41 oracle $RU / report $REP"
