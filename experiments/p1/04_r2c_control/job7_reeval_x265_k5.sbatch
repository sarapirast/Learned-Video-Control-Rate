#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=32G
#SBATCH --time=0:45:00
#SBATCH --job-name=r3k_x265_reeval
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%j.out
# Evaluation-only x265 check (no training): Aayush's STORED x265 R3 k5 seed-3 model (360k, model.zip) evaluated on val
# with my x265 setup (env.sh P1_ENC=x265: CLI backend, his x265 4.1 build, work_x265 links) must give exactly his stored
# eval rows (QPs and scores, 560/560). Uses his own shifts file, which his run used. ~10-15 min.
# Run: sbatch --export=ALL,P1_ENC=x265 job7_reeval_x265_k5.sbatch     (submit_x265.sh does this)
# Output: printed result, /scratch1/ahhanagu/ee599/results/r3_kcurve/<run name>_reeval_check.txt
set -euo pipefail
export P1_ENC=x265
source /scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead/env.sh
export RC_SHIFTS=/scratch1/aayushso/ee599/results_v1/next/exp5/shifts_smooth.json RC_WORKERS=14
for x in clips gops manifest.json results_infos; do [[ -L $RC_WORK/$x ]] || { echo "job7: $RC_WORK/$x is not a link" >&2; exit 1; }; done
$PY -I -W ignore "$REPO/experiments/p1/04_r2c_control/reeval_stored_model.py" \
    res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s3 2>&1 | grep -v -E 'elapsed'
rm -rf "$RC_TMP"
