#!/bin/bash
# D43 for one encoder (experiments/buffer_rl3.py, then experiments/buffer_real.py --model il_ppo_rr).
#   run    : runs/buffer_rl3.txt (20 runs: per channel ppo_pc, il_pc, ppo_pred x 3 seeds + il_rr seed 0), %6, 2 CPU / 8 GB, 3 h
#   report : runs/buffer_rl3_report.txt (default, trace), after all runs
#   real   : runs/buffer_real_model.txt (24 shards: il_ppo_rr with the real encoder; test / test16 / trace test), %6, 2 h,
#            after the runs; then runs/buffer_real_report.txt (D40 report incl. il_ppo_rr)
# usage: bash tools/submit_buffer_rl3.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E RC_PRESET=medium
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
sb() { sbatch --parsable --export=ALL $P "$@"; }
N=$(( $(wc -l < runs/buffer_rl3.txt) - 1 ))
RU=$(sb --time=3:00:00 --array=0-$N%6 --job-name=${E}_d43_rl tools/rl3_task.sbatch runs/buffer_rl3.txt)
REP=$(sb --time=0:30:00 --array=0-1 --dependency=afterany:$RU --job-name=${E}_d43_report tools/rl3_task.sbatch runs/buffer_rl3_report.txt)
M=$(( $(wc -l < runs/buffer_real_model.txt) - 1 ))
RE=$(sb --time=2:00:00 --array=0-$M%6 --dependency=afterany:$RU --job-name=${E}_d43_real tools/real_task.sbatch runs/buffer_real_model.txt)
RR=$(sb --time=0:20:00 --array=0-1 --dependency=afterany:$RE --job-name=${E}_d43_realrep tools/real_task.sbatch runs/buffer_real_report.txt)
echo "$E d43 rl $RU / report $REP / real $RE / real report $RR"
