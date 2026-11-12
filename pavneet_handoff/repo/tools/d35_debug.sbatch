#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=16G --time=0:50:00
#SBATCH --job-name=d35_debug
#SBATCH --output=/scratch1/pbanga/rcwork_v1/logs/%x-%j.out
# Debug for the two hole-closing runs, one encoder:
#  (a) encoder rate control on v1 test streams (dB metric): check stage + 16 quick cases + report
#  (b) fresh long-film set: manifest (384 GOP files, shared by both encoders), then the quick infos subset (6 GOPs) to time the encodes
# usage: RC_CODEC=x265 sbatch --export=ALL tools/d35_debug.sbatch
set -uo pipefail
export RC_PRESET=medium RC_V1=1
source /scratch1/pbanga/ee599/tools/job_env.sh
cd /scratch1/pbanga/ee599
run() { echo "=== $*"; /usr/bin/time -f "=== %e s" "$@" 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='; echo "=== rc=${PIPESTATUS[0]}"; }
export RC_WORK=/scratch1/pbanga/rcwork_v1/$RC_CODEC
run python -W ignore experiments/own_rc_stream_v1.py --quick
export RC_WORK=/scratch1/pbanga/rcwork_fresh/$RC_CODEC RC_V1=1 RC_BUDGETS=24,30,36,42
run python -W ignore tools/fresh_streams.py --stage manifest
run python -W ignore experiments/infos.py --stage infos --quick   # 6 GOPs, quick results dir
