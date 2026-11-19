#!/bin/bash
# Final-week submissions (exp_next/fw/PLAN.md). Every job is logged with scripts/joblog.sh. Run from anywhere:
#   bash exp_next/fw/submit.sh            prints the commands only (dry run)
#   bash exp_next/fw/submit.sh go         submits
# Per encoder:
#   item 2   seq_history --mode own (R3 k5 s3-5, own previous-GOP history, val)                      no dependency
#   item 4   R3 k5 without the critic warm-up, s3-5, 180k (runs_v1/fw_nowu.txt)                      no dependency
#   item 3   R3 k5 s3 re-run with checkpoints 20608/40000/60000/90000/120000 (runs_v1/fw_curve.txt)  no dependency
#   item 1   BC alone, val: k0 s0-2 (existing classifiers)                                            no dependency
#            k2 chain: build v1 k2 -> mean[t] k2 (both encoders) -> build v2 k2 -> BC k2 s3-5 ->
#            { R3 k2 s3-5 180k (runs_v1/fw_r3_k2.txt), BC alone val k2 + k5 s3-5 }
set -euo pipefail
GO=${1:-}
ROOT=/scratch1/aayushso/ee599
cd "$ROOT"
F4=1.0:6:1.0:2:3:4:1:1:1:0:3
EXCL=$(scripts/bad_nodes.sh exclude)
STEP=jobs/rc_v1_step.sbatch
run() {   # run <log text> <sbatch args...>; echoes the job id
  local text=$1; shift
  if [[ $GO == go ]]; then
    local id; id=$(sbatch --parsable --export=ALL ${EXCL:+--exclude=$EXCL} "$@")
    scripts/joblog.sh add "$id" "$STEP" "$text" >/dev/null
    echo "$id"
  else
    echo "DRY $*" >&2; echo "DRY$RANDOM"
  fi
}
envres() {   # the R3 / resh environment for encoder $1
  export RC_CODEC=$1 RC_ARM=res RC_METRIC=dpsnr RC_RES_RANGE=6 RC_CTRL_SETTING=$F4 \
         RC_WORK=/scratch1/aayushso/rcwork_v1/$1_resh RC_REPORTS=$ROOT/results_v1/$1_resh
}
declare -A TL=([x264]=4:00:00 [x265]=8:00:00) B1
for e in x264 x265; do
  envres $e
  export RC_RES_RECAP=bit
  J=$(run "final week item 2: R3 own previous-GOP history, val, $e" --cpus-per-task=16 --mem=32G --time=${TL[$e]} \
        --job-name=${e}_fw_seqhist $STEP $ROOT/exp_next/fw/seq_history.py --mode own); echo "$e item 2 seqhist -> $J"
  J=$(run "final week item 1: BC alone val k0 s0-2, $e" --cpus-per-task=16 --mem=16G --time=2:00:00 \
        --job-name=${e}_fw_bc0 $STEP $ROOT/exp_next/exp5/bc_eval.py --split val --ks 0 --seeds 0,1,2 --tag k0_s012)
  echo "$e item 1 BC alone k0 -> $J"
  if [[ $GO == go ]]; then
    for f in fw_nowu fw_curve; do
      (unset RC_REPORTS RC_WORK; RC_WORKNAME=resh RC_RUNS=runs_v1/$f.txt RC_TLIM=${TL[$e]} bash jobs/rc_v1_submit.sh $e res C)
    done
  else
    echo "DRY RC_WORKNAME=resh RC_RUNS=runs_v1/{fw_nowu,fw_curve}.txt RC_TLIM=${TL[$e]} bash jobs/rc_v1_submit.sh $e res C" >&2
  fi
  unset RC_RES_RECAP
  export EXP5_KS=2
  B1[$e]=$(run "final week item 1: BC dataset v1 k2, $e" --cpus-per-task=16 --mem=64G --time=1:00:00 \
        --job-name=${e}_fw_build_k2 $STEP $ROOT/exp_next/exp5/build.py); echo "$e item 1 build v1 k2 -> ${B1[$e]}"
  unset EXP5_KS
done
# mean[t] at k2 for both encoders (adds keys to shifts_smooth.json; refuses to change existing ones); ee599 env
export EXP5_KS=2
SS=$(run "final week item 1: smooth shift mean[t] k2 (both encoders)" --cpus-per-task=2 --mem=16G \
      --time=0:30:00 --dependency=afterok:${B1[x264]}:${B1[x265]} --job-name=fw_shift_k2 jobs/p2_step.sbatch \
      -I exp_next/exp5/shift_smooth.py); echo "shift k2 -> $SS"
unset EXP5_KS
for e in x264 x265; do
  envres $e
  export EXP5_KS=2
  B2=$(run "final week item 1: BC dataset v2 k2, $e" --cpus-per-task=16 --mem=64G --time=1:00:00 \
        --dependency=afterok:$SS --job-name=${e}_fw_build2_k2 $STEP $ROOT/exp_next/exp5/build.py --v2)
  echo "$e build v2 k2 -> $B2"
  unset EXP5_KS
  BT=$(run "final week item 1: BC train k2 s3-5, $e" --cpus-per-task=16 --mem=32G --time=2:00:00 \
        --dependency=afterok:$B2 --job-name=${e}_fw_bc_k2 $STEP $ROOT/exp_next/exp5/bc_train.py --ks 2 --seeds 3,4,5 \
        --tag k2_s345); echo "$e BC train k2 -> $BT"
  export RC_RES_RECAP=bit
  J=$(run "final week item 1: BC alone val k2+k5 s3-5, $e" --cpus-per-task=16 --mem=16G --time=2:00:00 \
        --dependency=afterok:$BT --job-name=${e}_fw_bc25 $STEP $ROOT/exp_next/exp5/bc_eval.py --split val --ks 2,5 \
        --seeds 3,4,5 --tag k25_s345); echo "$e BC alone k2/k5 -> $J"
  if [[ $GO == go ]]; then
    (unset RC_REPORTS RC_WORK; RC_DEP=$BT RC_WORKNAME=resh RC_RUNS=runs_v1/fw_r3_k2.txt RC_TLIM=${TL[$e]} bash jobs/rc_v1_submit.sh $e res C)
  else
    echo "DRY RC_DEP=$BT RC_WORKNAME=resh RC_RUNS=runs_v1/fw_r3_k2.txt RC_TLIM=${TL[$e]} bash jobs/rc_v1_submit.sh $e res C" >&2
  fi
  unset RC_RES_RECAP
done
