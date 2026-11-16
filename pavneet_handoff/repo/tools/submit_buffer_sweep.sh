#!/bin/bash
# D39 for one encoder: stronger baselines (vbv2, mpc), RL on the strongest rule (ppo_v2), one-at-a-time sensitivity
# sweep (sigma, buffer cap, stall weight), real LTE traces, and fresh films (default setting). Curve lookups only.
#   base   : runs/buffer_sweep_base.txt   (8 settings: rule/vbv tuning if missing, then vbv2 + mpc tuning), at most 4 at a time
#   rl     : runs/buffer_sweep.txt        (24 runs: ppo_v2 L=2, 3 seeds x 8 settings), after all base tasks, at most 6 at a time
#   fresh  : default setting, baselines + all L=2 policies on fresh films n = 16 / 32, after rl
#   report : runs/buffer_sweep_report.txt (8), after fresh
# usage: bash tools/submit_buffer_sweep.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E RC_FRESHWORK=/scratch1/pbanga/rcwork_fresh/$E
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
sb() { sbatch --parsable --export=ALL $P "$@"; }
BA=$(sb --time=2:00:00 --array=0-7%4 --job-name=${E}_d39_base tools/buf_task.sbatch runs/buffer_sweep_base.txt)
RL=$(sb --time=2:00:00 --array=0-23%6 --dependency=afterok:$BA --job-name=${E}_d39_rl tools/buf_task.sbatch runs/buffer_sweep.txt)
FR=$(sb --time=1:00:00 --dependency=afterany:$RL --job-name=${E}_d39_fresh tools/step.sbatch experiments/buffer_rl.py --fresh)
REP=$(sb --time=0:30:00 --array=0-7 --dependency=afterany:$FR --job-name=${E}_d39_report tools/buf_task.sbatch runs/buffer_sweep_report.txt)
echo "$E d39 base $BA / rl (24) $RL / fresh $FR / report $REP"
