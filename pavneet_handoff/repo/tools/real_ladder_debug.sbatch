#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug --time=0:50:00 --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=8G
# D43 debug: run each line of runs/buffer_ladder_real_debug.txt in turn, timed. Line = "[RC_BUF_*=value ...|-] <script> args"
# (tiny --quick / --limit runs; outputs under results_buffer*/debug_rl2 and .../real_debug).
# usage: RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 sbatch --export=ALL --output=... tools/rl3_debug.sbatch
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
export RC_V1=1 RC_PRESET=medium
cd /scratch1/pbanga/ee599
while read -r line; do
  envs=(); args=()
  for w in $line; do
    if [[ ${#args[@]} -eq 0 && $w == RC_BUF_*=* ]]; then envs+=("$w"); elif [[ ${#args[@]} -eq 0 && $w == - ]]; then :; else args+=("$w"); fi
  done
  echo "=== ${envs[*]} ${args[*]}"
  t0=$SECONDS; env "${envs[@]}" python -W ignore experiments/"${args[@]}"; rc=$?
  echo "line took $((SECONDS - t0)) s (rc $rc)"
done < runs/buffer_ladder_real_debug.txt
