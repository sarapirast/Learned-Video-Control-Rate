#!/bin/bash
# Aayush's checks 1-2 on the live-stream results: widen the vbv2 / mpc grids and retune on val, for all 8 settings of
# one encoder (curve lookups, no encodes, no RL training). Writes baselines2_wide.pkl next to each setting's results.
# usage: bash tools/submit_buffer_wide.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E RC_FRESHWORK=/scratch1/pbanga/rcwork_fresh/$E   # as D39 (submit_buffer_sweep.sh)
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
BW=$(sbatch --parsable --export=ALL $P --time=2:00:00 --array=0-7%4 --job-name=${E}_bufwide tools/buf_task.sbatch runs/buffer_wide.txt)
echo "$E widened baselines (8 settings, 4 at a time): $BW"
