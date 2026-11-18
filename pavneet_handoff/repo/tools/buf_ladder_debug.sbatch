#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=8G --time=0:55:00
#SBATCH --job-name=buf_ladder_debug
#SBATCH --output=/scratch1/pbanga/tmp/%x-%j.out
# Leak-fixed live stream (RC_BUF_LADDER=1): quick versions of every stage, AR(1) channel. Outputs only under
# rcwork_v1/<codec>/results_buffer_ladder (files with _quick) and debug_rl2. usage: RC_CODEC=x265 sbatch --export=ALL ...
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
export RC_WORK=/scratch1/pbanga/rcwork_v1/$RC_CODEC RC_FRESHWORK=/scratch1/pbanga/rcwork_fresh/$RC_CODEC RC_BUF_LADDER=1
cd /scratch1/pbanga/ee599
run() { echo "=== $*"; "$@" 2>&1 | grep --line-buffered -v -i -E 'warning'; echo "=== rc=${PIPESTATUS[0]}"; }
run python -W ignore experiments/buffer_rl.py --baselines2 --quick
run python -W ignore experiments/buffer_rl.py --baselines2-wide --quick
run python -W ignore experiments/buffer_rl.py --method ppo_v2 --look 2 --seed 0 --quick
RC_V1=1 run python -W ignore experiments/buffer_rl2.py --method il --seed 0 --quick
