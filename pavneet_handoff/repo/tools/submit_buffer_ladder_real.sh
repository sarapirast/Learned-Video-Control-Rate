#!/bin/bash
# D47 for one encoder: D40 + D43 real-encoder checks in the leak-fixed setting (RC_BUF_LADDER=1, D45).
# Outputs: rcwork_v1/<codec>/results_buffer{,_trace}_ladder/{real,il_rr_*,il_ppo_rr_L2_s0} (D40 / D43 untouched).
#   real   : runs/buffer_ladder_real.txt (44 shards: vbv2, ppo_v2, E1 replay, E2 encoder ABR+VBV, E3), 6 at a time
#   rr     : il_ppo seed 0 retrained with its model saved (il_ppo_rr), AR(1) and LTE          2 tasks
#   model  : runs/buffer_ladder_real_model.txt (24 shards, il_ppo_rr real encodes), after rr, 6 at a time
#   report : D40 report per channel, after real + model
# usage: bash tools/submit_buffer_ladder_real.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E RC_PRESET=medium
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
sb() { sbatch --parsable --export=ALL $P "$@"; }
RU=$(sb --time=3:00:00 --array=0-43%6 --job-name=${E}_d47_real tools/real_task.sbatch runs/buffer_ladder_real.txt)
RR=$(sb --time=3:00:00 --array=0-1 --job-name=${E}_d47_rr tools/rl3_task.sbatch runs/buffer_ladder_rr.txt)
MO=$(sb --time=3:00:00 --array=0-23%6 --dependency=afterok:$RR --job-name=${E}_d47_model tools/real_task.sbatch runs/buffer_ladder_real_model.txt)
REP=$(sb --time=0:20:00 --array=0-1 --dependency=afterany:$RU:$MO --job-name=${E}_d47_report tools/real_task.sbatch runs/buffer_ladder_real_report.txt)
echo "$E d47 real $RU / rr $RR / model $MO / report $REP"
