#!/bin/bash
# D42 for one encoder: RL variants vs the D41 oracle (experiments/buffer_rl2.py). Lookups only, no encodes.
#   run    : runs/buffer_rl2.txt (24 runs: ppo_mix, ppo_mixh x 3 seeds; per channel ppo_wide, il, il --wide x 3 seeds),
#            at most 6 at a time, 2 CPU / 8 GB, 3 h each
#   report : runs/buffer_rl2_report.txt (default, trace), after all shards
# usage: bash tools/submit_buffer_rl2.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
sb() { sbatch --parsable --export=ALL $P "$@"; }
N=$(( $(wc -l < runs/buffer_rl2.txt) - 1 ))
RU=$(sb --time=3:00:00 --array=0-$N%6 --job-name=${E}_d42_rl tools/rl2_task.sbatch runs/buffer_rl2.txt)
REP=$(sb --time=0:30:00 --array=0-1 --dependency=afterany:$RU --job-name=${E}_d42_report tools/rl2_task.sbatch runs/buffer_rl2_report.txt)
echo "$E d42 rl $RU / report $REP"
