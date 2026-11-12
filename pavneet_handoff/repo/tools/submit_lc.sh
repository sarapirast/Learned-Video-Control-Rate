#!/bin/bash
# Learning curve: CQL->PPO on 12.5/25/50/100% of the training clips, k=0 and 5, 3 seeds, causal x265, five budgets.
# Results: /scratch1/pbanga/rcwork_wide_causal/results_rl_lc (separate from results_rl, so pending reports never see them).
set -euo pipefail
cd /scratch1/pbanga/ee599
export RC_CAUSAL=1 RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_wide_causal RC_BUDGETS=26,30,34,38,42 RC_REPORTS=results/x265_causal
n=$(wc -l < runs/learning_curve.txt)
sbatch --parsable --export=ALL --partition=main --account=rashidin_1753 "--constraint=epyc-7513|epyc-7542" \
  --cpus-per-task=20 --mem=64G --time=4:00:00 --array=0-$((n-1))%12 --job-name=x265c_lc tools/rl_batch.sbatch runs/learning_curve.txt
