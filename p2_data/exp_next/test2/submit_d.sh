#!/bin/bash
# test2 wave D: PREREG secondary 10, Ahhana's R3 k0 / k29 (x264, s3-5, 180k), evaluation only (models received 11-18).
#   bash exp_next/test2/submit_d.sh        dry run (prints the sbatch commands)
#   bash exp_next/test2/submit_d.sh go     submits; every job logged with scripts/joblog.sh
# Gate on READING: no test2 number of these models is looked at before both val PARITY lines are all equal
# (our env + her model.zip + mean[t] reproduce her stored eval.pkl val rows).
set -euo pipefail
GO=${1:-}
ROOT=/scratch1/aayushso/ee599
cd "$ROOT"
EXCL=d18-35,d18-14,d05-06,d05-07,d05-08,d05-09,d05-10,d05-11,d05-12,d05-13,d05-14,d05-15,d05-26,d05-27,d05-28,d05-29,d05-30,d05-31,d05-32,d05-33,d05-34,d05-35,d05-36,d05-37,d05-38,d05-39,d05-40,d05-41,d05-42
STEP=jobs/rc_v1_step.sbatch
run() {   # run <log text> <sbatch args...>; echoes the job id
  local text=$1; shift
  if [[ $GO == go ]]; then
    local id; id=$(sbatch --parsable --export=ALL --exclude=$EXCL "$@")
    scripts/joblog.sh add "$id" "$STEP" "test2 wave D: $text" >/dev/null
    echo "$id"
  else
    echo "DRY sbatch $*" >&2; echo "DRY$RANDOM"
  fi
}
export RC_CODEC=x264 RC_ARM=res RC_METRIC=dpsnr RC_RES_RANGE=6 RC_RES_RECAP=bit RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3
unset RC_ACT_RANGE
for m in r3k0a r3k29a; do
  # ---- parity on v1 val (v1 work dir, v1 data)
  ( unset P2_DATA P2_RCWORK
    export RC_WORK=/scratch1/aayushso/rcwork_v1/x264_resh RC_REPORTS=$ROOT/results_v1/x264_resh
    J=$(run "PARITY Ahhana $m x264 on v1 val vs her eval.pkl" --cpus-per-task=16 --mem=32G --time=0:30:00 \
          --job-name=t2d_par_$m $STEP $ROOT/exp_next/test2/eval_ahhana.py --model $m --split val)
    echo "$m val parity -> $J" )
  # ---- test2
  ( export P2_DATA=$ROOT/data/t2/320x180 P2_RCWORK=/scratch1/aayushso/rcwork_t2
    export RC_WORK=/scratch1/aayushso/rcwork_t2/x264_resh RC_REPORTS=$ROOT/results_v1/test2/x264_resh
    J=$(run "Ahhana $m x264 s3-5 on test2 (PREREG secondary 10)" --cpus-per-task=16 --mem=32G --time=1:00:00 \
          --job-name=t2d_$m $STEP $ROOT/exp_next/test2/eval_ahhana.py --model $m --split test2)
    echo "$m test2 -> $J" )
done
