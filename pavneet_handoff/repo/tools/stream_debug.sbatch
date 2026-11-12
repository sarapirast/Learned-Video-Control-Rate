#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=16G --time=0:50:00
#SBATCH --job-name=stream_debug
#SBATCH --output=/scratch1/pbanga/rcwork_v1/logs/%x-%j.out
# D34 debug: stream-level RL on dataset v1, dB metric. Full baselines (margin tuning on val, hindsight ceiling; no
# training, curve lookups only) + every method at quick size + quick report. No encodes.
# usage: RC_CODEC=x265 sbatch --export=ALL tools/stream_debug.sbatch
set -uo pipefail
export RC_WORK=/scratch1/pbanga/rcwork_v1/${RC_CODEC}
source /scratch1/pbanga/ee599/tools/job_env.sh
cd /scratch1/pbanga/ee599
run() { echo "=== $*"; "$@" 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='; echo "=== rc=${PIPESTATUS[0]}"; }
run python -W ignore experiments/stream_rl.py --baselines
for m in bc ppo bc_ppo bc_ppo_lag; do run python -W ignore experiments/stream_rl.py --quick --method $m --look 2 --seed 0; done
run python -W ignore experiments/stream_rl.py --quick --report
