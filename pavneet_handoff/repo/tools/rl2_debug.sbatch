#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug --time=0:40:00 --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=8G
# D42 debug: run each line of runs/buffer_rl2_debug.txt in turn (tiny --quick runs, timed; outputs under results_buffer*/debug_rl2).
# usage: RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 sbatch --export=ALL --output=... tools/rl2_debug.sbatch
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
export RC_V1=1
cd /scratch1/pbanga/ee599
while read -r line; do
  envs=(); args=()
  for w in $line; do
    if [[ ${#args[@]} -eq 0 && $w == RC_BUF_*=* ]]; then envs+=("$w"); elif [[ ${#args[@]} -eq 0 && $w == - ]]; then :; else args+=("$w"); fi
  done
  t0=$SECONDS; env "${envs[@]}" python -W ignore experiments/buffer_rl2.py "${args[@]}"
  echo "line took $((SECONDS - t0)) s"
done < runs/buffer_rl2_debug.txt
