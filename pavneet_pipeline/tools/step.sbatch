#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --nodes=1 --ntasks=1
#SBATCH --output=/scratch1/pbanga/rcwork/logs/%x-%A_%a.out
# Generic job: one python stage. Partition, CPUs, memory, time and array range are given on the sbatch command line.
# usage: RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork RC_NSHARDS=N \
#        sbatch --export=ALL --partition=oneweek --cpus-per-task=20 --mem=48G --time=8:00:00 \
#               [--array=0-N-1] --job-name=x265_search tools/step.sbatch experiments/search.py --split train
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
cd /scratch1/pbanga/ee599
L=$RC_WORK/logs/${SLURM_JOB_NAME}.log
echo "$(date +%F\ %T) START job $SLURM_JOB_ID task ${SLURM_ARRAY_TASK_ID:-} on $(hostname) cpus $SLURM_CPUS_PER_TASK: $RC_CODEC $*" >> "$L"
python -W ignore "$@" 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='
rc=${PIPESTATUS[0]}
echo "$(date +%F\ %T) END   job $SLURM_JOB_ID task ${SLURM_ARRAY_TASK_ID:-} rc=$rc" >> "$L"
exit $rc
