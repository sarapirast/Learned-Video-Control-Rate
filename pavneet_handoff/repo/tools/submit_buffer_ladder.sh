#!/bin/bash
# Leak-fixed live stream (RC_BUF_LADDER=1: budget and mean channel rate from a fixed ladder, not the stream's content),
# AR(1) and LTE channels, one encoder. Curve lookups only. Outputs: rcwork_v1/<codec>/results_buffer_ladder[_trace]
# (new folders; nothing earlier is touched).
#   base : vbv / rule tuning, then vbv2 + mpc (D39 grid)                    2 tasks
#   wide : vbv2 / mpc on the wider grids (after base)                       2 tasks
#   ppo  : ppo_v2 x 3 seeds x 2 channels (after base)                       6 tasks
#   il   : il -> il_ppo (DAgger on the hindsight oracle, then PPO) x 3 x 2   6 tasks
#   report: D39 reports for both channels (after everything)                2 tasks
# usage: bash tools/submit_buffer_ladder.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E RC_FRESHWORK=/scratch1/pbanga/rcwork_fresh/$E
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
sb() { sbatch --parsable --export=ALL $P "$@"; }
BA=$(sb --time=3:00:00 --array=0-1 --job-name=${E}_lad_base tools/buf_task.sbatch runs/buffer_ladder_base.txt)
WI=$(sb --time=2:00:00 --array=0-1 --dependency=afterok:$BA --job-name=${E}_lad_wide tools/buf_task.sbatch runs/buffer_ladder_wide.txt)
PP=$(sb --time=2:00:00 --array=0-5 --dependency=afterok:$BA --job-name=${E}_lad_ppo tools/buf_task.sbatch runs/buffer_ladder_ppo.txt)
IL=$(sb --time=3:00:00 --array=0-5 --dependency=afterok:$BA --job-name=${E}_lad_il tools/rl2_task.sbatch runs/buffer_ladder_il.txt)
REP=$(sb --time=0:30:00 --array=0-1 --dependency=afterany:$WI:$PP:$IL --job-name=${E}_lad_report tools/buf_task.sbatch runs/buffer_ladder_report.txt)
echo "$E ladder: base $BA / wide $WI / ppo_v2 $PP / il $IL / report $REP"
