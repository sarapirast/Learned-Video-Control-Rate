#!/bin/bash
# D34: stream-level RL on dataset v1 (dB metric), one encoder. Curve lookups only, no encodes.
#   baselines : rule / equal split tuned on val (8 margins x 5 slopes x 3 prior weights), best constant QP, hindsight
#   learners  : runs/stream.txt (bc, ppo, bc_ppo, bc_ppo_lag x L 0/2 x 3 seeds = 24), at most 8 at a time
#   report    : val + test tables, after both finish
# Writes only to rcwork_v1/<codec>/results_stream, rcwork_v1/<codec>/logs and results/v1_stream/<codec>.
# usage: bash tools/submit_stream.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
mkdir -p "$RC_WORK/logs"
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out"
sb() { sbatch --parsable --export=ALL $P "$@"; }
BL=$(sb --cpus-per-task=2 --mem=8G --time=2:00:00 --job-name=${E}_stream_base tools/step.sbatch experiments/stream_rl.py --baselines)
n=$(wc -l < runs/stream.txt)
RL=$(sb --cpus-per-task=2 --mem=8G --time=3:00:00 --array=0-$((n-1))%8 --job-name=${E}_stream_rl tools/step.sbatch experiments/stream_rl.py --list runs/stream.txt)
REP=$(sb --cpus-per-task=2 --mem=8G --time=0:30:00 --dependency=afterok:$BL,afterany:$RL --job-name=${E}_stream_report tools/step.sbatch experiments/stream_rl.py --report)
echo "$E baselines $BL / rl ($n runs) $RL / report $REP"
