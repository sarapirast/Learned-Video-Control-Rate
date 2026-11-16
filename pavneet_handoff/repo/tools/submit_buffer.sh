#!/bin/bash
# D38: buffer / live-channel rate control, one encoder. Curve lookups only, no encodes.
#   baselines : tune rule and vbv on val, evaluate on val / test / test16 (once, before any learner)
#   learners  : runs/buffer.txt (ppo at L=2 and L=0, 3 seeds = 6), after the baselines
#   report    : after all learners (afterany)
# Reads rcwork_v1/<codec> (infos) and the v1 per-frame table (read-only). Writes rcwork_v1/<codec>/results_buffer,
# rcwork_v1/<codec>/results_yrd, rcwork_v1/<codec>/logs and results/v1_buffer/<codec>.
# usage: bash tools/submit_buffer.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
mkdir -p "$RC_WORK/logs"
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out"
sb() { sbatch --parsable --export=ALL $P "$@"; }
n=$(wc -l < runs/buffer.txt)
BA=$(sb --cpus-per-task=2 --mem=8G --time=1:00:00 --job-name=${E}_buf_base tools/step.sbatch experiments/buffer_rl.py --baselines)
RL=$(sb --cpus-per-task=2 --mem=8G --time=2:00:00 --array=0-$((n-1)) --dependency=afterok:$BA --job-name=${E}_buf_rl tools/step.sbatch experiments/buffer_rl.py --list runs/buffer.txt)
REP=$(sb --cpus-per-task=2 --mem=8G --time=0:30:00 --dependency=afterany:$RL --job-name=${E}_buf_report tools/step.sbatch experiments/buffer_rl.py --report)
echo "$E buffer baselines $BA / rl ($n runs) $RL / report $REP"
