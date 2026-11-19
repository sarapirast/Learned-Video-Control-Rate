#!/bin/bash
# D49 VMAF constant-QP curves, one encoder: native 320x180 (8 shards, ~7 min each) and 1080p upscaled (40 shards,
# ~45 min each, at most 10 at a time). 1 CPU per task (vmaf --threads 1). Outputs: rcwork_v1/<codec>/results_vmaf/.
# usage: bash tools/submit_vmaf.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=1 --mem=4G"
N=$(sbatch --parsable --export=ALL $P --time=1:00:00 --array=0-7 --job-name=${E}_vmaf_native tools/vmaf_task.sbatch runs/vmaf_native.txt)
U=$(sbatch --parsable --export=ALL $P --time=2:00:00 --array=0-39%10 --job-name=${E}_vmaf_1080 tools/vmaf_task.sbatch runs/vmaf_1080.txt)
echo "$E vmaf native $N / 1080 $U"
