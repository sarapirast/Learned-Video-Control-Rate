#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=debug --time=0:40:00 --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=8G
# D49 debug: one GOP's VMAF curve (33 QPs) at native resolution and at 1080p, timed. Outputs under results_vmaf/*_debug.
# usage: RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 sbatch --export=ALL --output=... tools/vmaf_debug.sbatch
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
export RC_V1=1 RC_PRESET=medium
cd /scratch1/pbanga/ee599
/scratch1/pbanga/envs/vmaf/bin/vmaf --version
for s in native 1080; do
  t0=$SECONDS; python -W ignore experiments/vmaf_curves.py --scale $s --shard 0 --nshards 1 --limit 1; echo "$s took $((SECONDS - t0)) s (rc $?)"
done
