#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --nodes=1 --ntasks=1
#SBATCH --output=/scratch1/pbanga/rcwork/logs/%x-%A_%a.out
# Array of RL runs: line $SLURM_ARRAY_TASK_ID+1 of the run-list file holds the rl.py arguments for this task.
# usage: RC_CODEC=x265 RC_WORK=... sbatch --export=ALL --partition=oneweek --cpus-per-task=20 --mem=48G \
#        --time=12:00:00 --array=0-N-1%M --job-name=x265_rl tools/rl_batch.sbatch runs/<list>.txt
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
cd /scratch1/pbanga/ee599
ARGS=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$1")
L=$RC_WORK/logs/${SLURM_JOB_NAME}.log
echo "$(date +%F\ %T) START $SLURM_ARRAY_JOB_ID[$SLURM_ARRAY_TASK_ID] $(hostname): $RC_CODEC rl.py $ARGS" >> "$L"
unset SLURM_ARRAY_TASK_ID   # rl.py runs are not shards
python -W ignore experiments/rl.py $ARGS 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='
rc=${PIPESTATUS[0]}
echo "$(date +%F\ %T) END   $SLURM_ARRAY_JOB_ID rc=$rc: $ARGS" >> "$L"
exit $rc
