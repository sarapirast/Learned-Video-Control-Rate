#!/bin/bash
# Dataset v1, Stage 2 (D31) for one encoder: Lagrangian PPO at k = 0, 1, 2, 5, 10, 29 with 5 seeds, plus the controller at
# the new k values. Runs finished in Stage 1 are skipped by rl.py. The report is rewritten with all runs, Stage 1 included.
# usage: bash tools/submit_v1_stage2.sh x265|x264
set -euo pipefail
E=$1
export RC_V1=1 RC_PRESET=medium RC_BUDGETS=24,30,36,42 RC_CODEC=$E
export RC_WORK=/scratch1/pbanga/rcwork_v1/$E RC_REPORTS=/scratch1/pbanga/ee599/results/v1/$E
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --constraint=epyc-7513|epyc-7542 --output=$RC_WORK/logs/%x-%A_%a.out"
sb() { sbatch --parsable --export=ALL $P "$@"; }
n=$(wc -l < runs/v1_stage2.txt)
RL=$(sb --cpus-per-task=20 --mem=64G --time=6:00:00 --array=0-$((n-1))%13 --job-name=${E}v2_rl tools/rl_batch.sbatch runs/v1_stage2.txt)
REP=$(sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterany:$RL --job-name=${E}v2_report tools/step.sbatch experiments/v1_report.py)
echo "$E stage 2 rl ($n lines) / report -> $RL / $REP"
