#!/bin/bash
# D29 + D30 (2026-11-04): fair head-to-head, BC + feedback control, re-analysis, causal per-GOP rerun.
# usage: bash tools/submit_d30.sh part1          # D29 streams + BC+feedback + re-analysis (existing work dirs)
#        bash tools/submit_d30.sh bc_fb2         # remaining-budget BC+feedback + re-analysis (existing work dirs)
#        bash tools/submit_d30.sh causal x265    # D30 causal rerun for one encoder (5 budgets)
# Every job: account rashidin_1753, main partition, EPYC nodes only (xeon-4116 gives SIGBUS), module purge in job_env.sh.
set -euo pipefail
cd /scratch1/pbanga/ee599
P="--partition=main --account=rashidin_1753 --constraint=epyc-7513|epyc-7542"
sb() { sbatch --parsable --export=ALL $P "$@"; }
B5=26,30,34,38,42
declare -A WORK=([x265_2]=/scratch1/pbanga/rcwork [x264_2]=/scratch1/pbanga/rcwork_x264
                 [x265_5]=/scratch1/pbanga/rcwork_wide [x264_5]=/scratch1/pbanga/rcwork_x264_wide)

if [[ $1 == part1 ]]; then
  for E in x265 x264; do
    W=${WORK[${E}_2]}
    J=$(RC_CODEC=$E RC_WORK=$W RC_BUDGETS=30,38 RC_REPORTS=results/$E sb --cpus-per-task=20 --mem=32G --time=1:30:00 \
        --job-name=${E}_own_rc_stream tools/step.sbatch experiments/own_rc_stream.py)
    echo "$E own_rc_stream -> $J"
  done
  for key in x265_2 x264_2 x265_5 x264_5; do
    E=${key%_*}; W=${WORK[$key]}; BU=30,38; REP=results/$E
    [[ $key == *_5 ]] && BU=$B5 && REP=results/${E}_wide
    deps=""
    for k in 0 5; do
      J=$(RC_CODEC=$E RC_WORK=$W RC_BUDGETS=$BU RC_REPORTS=$REP sb --cpus-per-task=20 --mem=48G --time=4:00:00 \
          --job-name=${key}_bc_fb_k$k tools/step.sbatch experiments/bc_feedback.py --k $k)
      deps="$deps:$J"
    done
    R=$(RC_CODEC=$E RC_WORK=$W RC_BUDGETS=$BU RC_REPORTS=$REP sb --cpus-per-task=4 --mem=48G --time=1:00:00 \
        --dependency=afterany$deps --job-name=${key}_reanalysis tools/step.sbatch experiments/reanalysis.py)
    echo "$key bc_feedback$deps -> reanalysis $R"
  done
fi

if [[ $1 == bc_fb2 ]]; then   # remaining-budget feedback on the four original work dirs, then re-analysis (replaces 13729093)
  for key in x265_2 x264_2 x265_5 x264_5; do
    E=${key%_*}; W=${WORK[$key]}; BU=30,38; REP=results/$E
    [[ $key == *_5 ]] && BU=$B5 && REP=results/${E}_wide
    deps=""
    for k in 0 5; do
      J=$(RC_CODEC=$E RC_WORK=$W RC_BUDGETS=$BU RC_REPORTS=$REP sb --cpus-per-task=20 --mem=48G --time=4:00:00 \
          --job-name=${key}_bc_fb2_k$k tools/step.sbatch experiments/bc_feedback.py --k $k)
      deps="$deps:$J"
    done
    R=$(RC_CODEC=$E RC_WORK=$W RC_BUDGETS=$BU RC_REPORTS=$REP sb --cpus-per-task=4 --mem=48G --time=1:00:00 \
        --dependency=afterany$deps --job-name=${key}_reanalysis2 tools/step.sbatch experiments/reanalysis.py)
    echo "$key bc_fb2$deps -> reanalysis $R"
  done
fi

if [[ $1 == causal ]]; then
  E=$2
  W=/scratch1/pbanga/rcwork_wide_causal; [[ $E == x264 ]] && W=/scratch1/pbanga/rcwork_x264_wide_causal
  export RC_CAUSAL=1 RC_CODEC=$E RC_WORK=$W RC_BUDGETS=$B5 RC_REPORTS=results/${E}_causal
  PREP=$(sb --cpus-per-task=4 --mem=48G --time=1:00:00 --job-name=${E}c_prep tools/step.sbatch experiments/causal_prep.py)
  SPC=$(sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$PREP --job-name=${E}c_spend \
        tools/step.sbatch experiments/baselines.py --stage spend_curve)
  A=$(RC_NSHARDS=4 sb --cpus-per-task=20 --mem=32G --time=4:00:00 --array=0-3 --dependency=afterok:$PREP \
      --job-name=${E}c_own_rc tools/step.sbatch experiments/baselines.py --stage own_rc)
  OWN=$(RC_NSHARDS=4 sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$A --job-name=${E}c_own_rc_gather \
        tools/step.sbatch experiments/baselines.py --stage gather_own_rc)
  RUL=$(sb --cpus-per-task=64 --mem=96G --time=12:00:00 --dependency=afterok:$SPC --job-name=${E}c_rules \
        tools/step.sbatch experiments/baselines.py --stage rules)
  n=$(wc -l < runs/causal.txt)
  RL=$(sb --cpus-per-task=20 --mem=100G --time=12:00:00 --array=0-$((n-1))%25 --dependency=afterok:$PREP \
       --job-name=${E}c_rl tools/rl_batch.sbatch runs/causal.txt)
  F0=$(sb --cpus-per-task=20 --mem=48G --time=4:00:00 --dependency=afterany:$RL:$SPC --job-name=${E}c_bc_fb_k0 \
       tools/step.sbatch experiments/bc_feedback.py --k 0)
  F5=$(sb --cpus-per-task=20 --mem=48G --time=4:00:00 --dependency=afterany:$RL:$SPC --job-name=${E}c_bc_fb_k5 \
       tools/step.sbatch experiments/bc_feedback.py --k 5)
  BD=$(sb --cpus-per-task=4 --mem=64G --time=1:00:00 --dependency=afterany:$RL:$RUL:$OWN:$F0:$F5 --job-name=${E}c_breakdown \
       tools/step.sbatch experiments/breakdown.py)
  RA=$(sb --cpus-per-task=4 --mem=64G --time=1:00:00 --dependency=afterany:$BD --job-name=${E}c_reanalysis \
       tools/step.sbatch experiments/reanalysis.py)
  echo "$E causal: prep $PREP, spend $SPC, own_rc $A + $OWN, rules $RUL, rl $RL ($n runs), bc_fb $F0/$F5, breakdown $BD, reanalysis $RA"
fi
