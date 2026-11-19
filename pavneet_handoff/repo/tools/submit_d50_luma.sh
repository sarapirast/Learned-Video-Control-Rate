#!/bin/bash
# D50: the D35 stream-level encoder rate-control comparison re-encoded and scored in luma PSNR of pooled MSE
# (RC_OWN_LUMA=1), plus the D34 RL / rule rows rescored in luma from their stored per-GOP QPs. One encoder.
# Writes only rcwork_v1/<codec>/results_own_rc_stream_v1_luma and results/v1_stream/<codec>/own_rc_stream_v1_luma_report.md.
# usage: bash tools/submit_d50_luma.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_V1=1 RC_PRESET=medium RC_OWN_LUMA=1
V=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
sb() { RC_WORK=$V sbatch --parsable --export=ALL --partition=main --account=rashidin_1753 --output=$V/logs/%x-%A_%a.out "$@"; }
A=$(RC_NSHARDS=8 sb --cpus-per-task=4 --mem=8G --time=1:30:00 --array=0-7 --job-name=${E}_d50_luma tools/step.sbatch experiments/own_rc_stream_v1.py --stage run)
G=$(RC_NSHARDS=8 sb --cpus-per-task=2 --mem=8G --time=0:30:00 --dependency=afterok:$A --job-name=${E}_d50_gather tools/step.sbatch experiments/own_rc_stream_v1.py --stage gather)
echo "$E d50 luma run $A / gather $G"
