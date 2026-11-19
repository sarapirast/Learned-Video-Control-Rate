#!/bin/bash
# D54: VMAF of the encoder rate-control rows (stream-level ABR+VBV and two-pass; live-channel E2 ABR+VBV), one encoder.
# 3,496 re-encodes (32,768 GOPs) per encoder, ~70 s per 8-GOP stream incl. 1080p VMAF -> ~80 CPU-h per encoder.
# 128 tasks x 1 CPU (vmaf --threads 1), ~40 min each, no throttle. Writes only rcwork_v1/<codec>/results_enc_vmaf/.
# usage: bash tools/submit_enc_vmaf.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_V1=1 RC_PRESET=medium RC_NSHARDS=128 RC_WORK=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
J=$(sbatch --parsable --export=ALL --partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out \
    --cpus-per-task=1 --mem=6G --time=2:00:00 --array=0-127 --job-name=${E}_enc_vmaf \
    tools/step.sbatch experiments/encoder_vmaf.py)
echo "$E enc_vmaf $J"
