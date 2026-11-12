#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug
#SBATCH --constraint=epyc-7313
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=48G --time=0:45:00
#SBATCH --job-name=d30_debug
#SBATCH --output=/scratch1/pbanga/rcwork/logs/%x-%j.out
# D30 debug test (x265 only): causal prep + smoke test of the causal env (GOP-level rate-model base QP version).
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
cd /scratch1/pbanga/ee599
run() { echo "=== $*"; "$@" 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='; echo "=== rc=${PIPESTATUS[0]}"; }
CW=/scratch1/pbanga/rcwork_wide_causal
run env RC_CAUSAL=1 RC_WORK=$CW RC_BUDGETS=26,30,34,38,42 RC_REPORTS=results/x265_causal python -W ignore experiments/causal_prep.py
run env RC_CAUSAL=1 RC_WORK=$CW RC_BUDGETS=26,30,34,38,42 RC_REPORTS=results/x265_causal python -W ignore tools/causal_smoke.py /scratch1/pbanga/rcwork_wide
# re-analysis and BC+feedback quick run passed in 13726780
