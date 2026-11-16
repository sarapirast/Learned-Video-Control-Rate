#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --nodes=1 --ntasks=1
# D43: one line of a list file per array task: "[RC_BUF_*=value ...|-] args for experiments/buffer_rl3.py".
# usage: RC_CODEC=x265 RC_WORK=... sbatch --export=ALL ... --array=0-N tools/rl3_task.sbatch runs/<list>.txt
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
export RC_V1=1
cd /scratch1/pbanga/ee599
line=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$1")
envs=(); args=()
for w in $line; do
  if [[ ${#args[@]} -eq 0 && $w == RC_BUF_*=* ]]; then envs+=("$w"); elif [[ ${#args[@]} -eq 0 && $w == - ]]; then :; else args+=("$w"); fi
done
L=$RC_WORK/logs/${SLURM_JOB_NAME}.log
echo "$(date +%F\ %T) START job $SLURM_JOB_ID task $SLURM_ARRAY_TASK_ID on $(hostname): $RC_CODEC ${envs[*]} ${args[*]}" >> "$L"
env "${envs[@]}" python -W ignore experiments/buffer_rl3.py "${args[@]}" 2>&1 | grep --line-buffered -v -i 'warning'
rc=${PIPESTATUS[0]}
echo "$(date +%F\ %T) END   job $SLURM_JOB_ID task $SLURM_ARRAY_TASK_ID rc=$rc" >> "$L"
exit $rc
