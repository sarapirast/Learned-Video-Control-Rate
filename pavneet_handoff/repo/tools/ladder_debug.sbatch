#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=32G --time=0:55:00
#SBATCH --job-name=ladder_debug
#SBATCH --output=/scratch1/pbanga/tmp/%x-%j.out
# D44 debug test on the --quick subset (18 GOPs): prep, search, encoder RC, controller, two tiny learners.
# usage: RC_CODEC=x265 sbatch --export=ALL tools/ladder_debug.sbatch
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
export LADDER_DIR=/scratch1/pbanga/rcwork_ladder_debug
source /scratch1/pbanga/ee599/tools/ladder_env.sh
cd /scratch1/pbanga/ee599
run() { echo "=== $*"; "$@" 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='; echo "=== rc=${PIPESTATUS[0]}"; }
run python -W ignore experiments/ladder_prep.py --quick --src $LADDER_SRC
run python -W ignore experiments/search.py --quick --split train
run python -W ignore experiments/search.py --quick --split test
run python -W ignore experiments/baselines.py --quick --stage own_rc
run python -W ignore experiments/rl.py --quick --method ctrl --k 0 --seed 0
run python -W ignore experiments/rl.py --quick --method ctrl --k 5 --mode cut_trig --seed 0
run python -W ignore experiments/rl.py --quick --method lagr --k 0 --seed 0
run python -W ignore experiments/rl.py --quick --method cql_ppo --k 5 --mode cut_trig --seed 0
ls -R $RC_WORK | grep -E "eval.pkl|own_rc|search_t" | head -20
