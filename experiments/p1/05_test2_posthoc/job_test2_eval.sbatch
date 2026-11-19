#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=32G
#SBATCH --time=0:45:00
#SBATCH --job-name=r3k_test2
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%j.out
# job_test2_eval.sbatch: my R3 k0 / k29 models (seeds 3-5) on test2 via eval_test2_p1.py, val parity gate first.
# Steps run in the order given; set -e: a failed parity gate (or any error) stops the job before any test2 step.
# Run:
#   x264 (parity with Aayush's stored secondary-10 rows; shim, ~10 min):
#     sbatch --export=ALL,P1_ENC=x264 job_test2_eval.sbatch k0:val k29:val k0:test2 k29:test2
#   x265 (POST-HOC, only after all x265 seeds 3-5 are scored on val; CLI): one job per model and checkpoint, each
#   with its own val gate first (~1.2 h each; all four in one job would take ~5 h):
#     for m in k0 k29; do for c in final 20000; do
#       sbatch --export=ALL,P1_ENC=x265 --time=3:00:00 job_test2_eval.sbatch $m:val:$c $m:test2:$c; done; done
# Outputs: /scratch1/ahhanagu/ee599/results/test2_posthoc/r3k{0,29}_{val,test2}_<enc>.pkl; score with score_test2_p1.py.
set -euo pipefail
source /scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead/env.sh
E=$REPO/experiments/p1/05_test2_posthoc/eval_test2_p1.py
export RC_WORKERS=$(( SLURM_CPUS_PER_TASK - 2 ))
for step in "$@"; do                   # step = model:split[:ckpt], ckpt final (R3, default) or 20000 (its BC start)
  IFS=: read -r model split ckpt <<< "$step"; ckpt=${ckpt:-final}
  if [[ $split == val ]]; then export RC_WORK=/scratch1/aayushso/rcwork_v1/${RC_CODEC}_resh      # Aayush's, read only
  else export RC_WORK=/scratch1/aayushso/rcwork_t2/${RC_CODEC}_resh; fi                          # his test2, read only
  echo "$(date +%T) $RC_CODEC $model $split ckpt $ckpt (RC_WORK=$RC_WORK, backend $RC_BACKEND)"
  $PY -I -W ignore "$E" --model "$model" --split "$split" --ckpt "$ckpt" 2>&1 | grep -v -E 'elapsed'
done
rm -rf "$RC_TMP"
echo "$(date +%T) done"
