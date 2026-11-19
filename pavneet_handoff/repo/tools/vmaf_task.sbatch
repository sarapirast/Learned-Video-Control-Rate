#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --nodes=1 --ntasks=1
# D49: one line of a list file per array task: args for experiments/vmaf_curves.py.
# usage: RC_CODEC=x265 RC_WORK=... sbatch --export=ALL ... --array=0-N tools/vmaf_task.sbatch runs/<list>.txt
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
export RC_V1=1 RC_PRESET=medium
cd /scratch1/pbanga/ee599
args=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$1")
L=$RC_WORK/logs/${SLURM_JOB_NAME}.log
echo "$(date +%F\ %T) START job $SLURM_JOB_ID task $SLURM_ARRAY_TASK_ID on $(hostname): $RC_CODEC $args" >> "$L"
python -W ignore experiments/vmaf_curves.py $args
rc=$?
echo "$(date +%F\ %T) END   job $SLURM_JOB_ID task $SLURM_ARRAY_TASK_ID rc=$rc" >> "$L"
exit $rc
