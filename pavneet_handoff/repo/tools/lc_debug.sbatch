#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug
#SBATCH --constraint=epyc-7313
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=48G --time=0:30:00
#SBATCH --job-name=lc_debug
#SBATCH --output=/scratch1/pbanga/rcwork_v1/logs/%x-%j.out
# Learning-curve code check on the finished quick x264 v1 test folder. Writes only to its results_rl_lc_quick.
set -uo pipefail
export RC_V1=1 RC_PRESET=medium RC_BUDGETS=24,30,36,42 RC_CODEC=x264
export RC_WORK=/scratch1/pbanga/rcwork_v1/test_x264 RC_REPORTS=/scratch1/pbanga/rcwork_v1/test_reports/x264
source /scratch1/pbanga/ee599/tools/job_env.sh
cd /scratch1/pbanga/ee599
python -W ignore experiments/rl.py --quick --method cql_ppo --k 0 --seed 0 --train-frac 0.5 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps=' | grep -v -E 'elapsed'
echo "=== rc=${PIPESTATUS[0]}"
