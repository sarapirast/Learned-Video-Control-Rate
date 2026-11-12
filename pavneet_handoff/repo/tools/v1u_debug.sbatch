#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug
#SBATCH --constraint=epyc-7313
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=48G --time=0:55:00
#SBATCH --job-name=v1u_debug
#SBATCH --output=/scratch1/pbanga/rcwork_v1/logs/%x-%j.out
# D33 debug: v1 quick subset with the under-budget penalty. Reuses test2_<codec>'s quick infos/scenes/controller plans
# (read only), rescoring them; then search, one Lagrangian run and the controller. usage: RC_CODEC=x265 sbatch --export=ALL tools/v1u_debug.sbatch
set -uo pipefail
export RC_V1=1 RC_PRESET=medium RC_BUDGETS=24,30,36,42 RC_UNDER_PENALTY=1 RC_UNDER_TOL=3
SRC=${RC_SRC:-/scratch1/pbanga/rcwork_v1/test2_${RC_CODEC}}   # x264: test_x264 holds its passing debug run
export RC_WORK=/scratch1/pbanga/rcwork_v1/testu_${RC_CODEC} RC_REPORTS=/scratch1/pbanga/rcwork_v1/testu_reports/${RC_CODEC}
mkdir -p "$RC_WORK" "$RC_REPORTS"
source /scratch1/pbanga/ee599/tools/job_env.sh
cd /scratch1/pbanga/ee599
S=/scratch1/aayushso/rcwork_v1/x265_orig      # read-only: clips, GOP files and manifest of dataset v1
[ -e "$RC_WORK/clips" ] || ln -s $S/clips "$RC_WORK/clips"
[ -e "$RC_WORK/gops" ] || ln -s $S/gops "$RC_WORK/gops"
[ -e "$RC_WORK/manifest.json" ] || cp $S/manifest.json "$RC_WORK/manifest.json"
run() { echo "=== $*"; "$@" 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='; echo "=== rc=${PIPESTATUS[0]}"; }
run python -W ignore experiments/v1_rescore.py --quick --src $SRC
run python -W ignore experiments/search.py --quick --split train
run python -W ignore experiments/rl.py --quick --method ctrl --k 0 --seed 0
run python -W ignore experiments/rl.py --quick --method lagr --k 0 --seed 0
run python -W ignore experiments/v1_report.py --quick
