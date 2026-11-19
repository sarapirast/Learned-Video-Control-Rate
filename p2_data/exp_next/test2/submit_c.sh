#!/bin/bash
# test2 wave C: evaluation-only passes of the frozen models (exp_next/test2/PREREG.md, frozen 11-17).
#   bash exp_next/test2/submit_c.sh        dry run (prints the sbatch commands)
#   bash exp_next/test2/submit_c.sh go     submits; every job logged with scripts/joblog.sh
# Parity jobs (v1 test clips through the test2 path) and test2 jobs go in together; the gate is on READING: no test2
# number is looked at before every parity line is OK (parity.py abr shift + the eval_t2 PARITY lines + bc --check).
# slim infos were pre-built 11-17 (no race between jobs). seq_history needs r3k5 test2's rows -> afterok.
set -euo pipefail
GO=${1:-}
ROOT=/scratch1/aayushso/ee599
cd "$ROOT"
F4=1.0:6:1.0:2:3:4:1:1:1:0:3
RCT=/scratch1/aayushso/rcwork_t2
export P2_DATA=$ROOT/data/t2/320x180 P2_RCWORK=$RCT
EXCL=d18-35,d18-14,d05-06,d05-07,d05-08,d05-09,d05-10,d05-11,d05-12,d05-13,d05-14,d05-15,d05-26,d05-27,d05-28,d05-29,d05-30,d05-31,d05-32,d05-33,d05-34,d05-35,d05-36,d05-37,d05-38,d05-39,d05-40,d05-41,d05-42
STEP=jobs/rc_v1_step.sbatch
run() {   # run <log text> <script> <sbatch args...>; echoes the job id
  local text=$1 script=$2; shift 2
  if [[ $GO == go ]]; then
    local id; id=$(sbatch --parsable --export=ALL --exclude=$EXCL "$@")
    scripts/joblog.sh add "$id" "$script" "test2 wave C: $text" >/dev/null
    echo "$id"
  else
    echo "DRY sbatch $*" >&2; echo "DRY$RANDOM"
  fi
}
envres() { export RC_CODEC=$1 RC_ARM=res RC_METRIC=dpsnr RC_RES_RANGE=6 RC_RES_RECAP=bit RC_CTRL_SETTING=$F4 \
                  RC_WORK=$RCT/$1_resh RC_REPORTS=$ROOT/results_v1/test2/$1_resh; unset RC_ACT_RANGE; }
envlfq() { export RC_CODEC=$1 RC_ARM=lfq RC_ACT_RANGE=10 RC_WORK=$RCT/$1_lfqp RC_REPORTS=$ROOT/results_v1/test2/$1_lfqp
           unset RC_METRIC RC_RES_RANGE RC_RES_RECAP RC_CTRL_SETTING; }
declare -A M=([x264]=0.90 [x265]=0.93) S=([x264]=1 [x265]=2)   # S: time scale (x265 encodes ~2x slower)
h() { echo "$(( $1 * ${S[$e]} )):00:00"; }
for e in x264 x265; do
  # ---- parity (3 v1 test clips; must equal the stored v1 test rows)
  envres $e
  J=$(run "PARITY R3 k5 s3-5 $e" $STEP --cpus-per-task=16 --mem=32G --time=0:30:00 --job-name=t2c_par_r3k5_$e \
        $STEP $ROOT/exp_next/test2/eval_t2.py --model r3k5 --split parity); echo "$e parity r3k5 -> $J"
  J=$(run "CHECK BC env on test2 (offset 0 + mean 0 = final4 stored rows) $e" $STEP --cpus-per-task=8 --mem=16G \
        --time=0:30:00 --job-name=t2c_bccheck_$e $STEP $ROOT/exp_next/exp5/bc_eval.py --split test2 --check --n 8 \
        --ks 0,2,5); echo "$e bc check -> $J"
  if [[ $e == x265 ]]; then
    J=$(run "PARITY final4 + per-qbin shift k5 $e" $STEP --cpus-per-task=8 --mem=16G --time=0:30:00 \
          --job-name=t2c_par_shift_$e $STEP $ROOT/exp_next/exp5/shift_eval.py --split parity --variants perqbin:bit \
          --ks 5 --tag qbin_k5 --out $ROOT/results_v1/test2); echo "$e parity shift -> $J"
  fi
  envlfq $e
  J=$(run "PARITY CQL->PPO 540k @prev k0/k5 $e" $STEP --cpus-per-task=16 --mem=32G --time=0:30:00 \
        --job-name=t2c_par_cqlppo_$e $STEP $ROOT/exp_next/test2/eval_t2.py --model cqlppo --split parity --ks 0,5)
  echo "$e parity cqlppo -> $J"
  J=$(run "PARITY ABR+VBV m${M[$e]} k0/5 $e" jobs/p2_step.sbatch --cpus-per-task=8 --mem=16G --time=0:30:00 \
        --job-name=t2c_par_abr_$e jobs/p2_step.sbatch -I exp_next/exp10/abr_margin.py --encoder $e --split parity \
        --margins ${M[$e]} --ks 0,5); echo "$e parity abr -> $J"
  # ---- test2
  envres $e
  R3=$(run "R3 k5 s3-5 (PRIMARY) $e" $STEP --cpus-per-task=16 --mem=32G --time=$(h 2) --job-name=t2c_r3k5_$e \
        $STEP $ROOT/exp_next/test2/eval_t2.py --model r3k5 --split test2); echo "$e r3k5 -> $R3"
  J=$(run "R3 k2 s3-5 $e" $STEP --cpus-per-task=16 --mem=32G --time=$(h 2) --job-name=t2c_r3k2_$e \
        $STEP $ROOT/exp_next/test2/eval_t2.py --model r3k2 --split test2); echo "$e r3k2 -> $J"
  J=$(run "BC alone k2+k5 s3-5 $e" $STEP --cpus-per-task=16 --mem=16G --time=$(h 2) --job-name=t2c_bc25_$e \
        $STEP $ROOT/exp_next/exp5/bc_eval.py --split test2 --ks 2,5 --seeds 3,4,5 --tag k25_s345 \
        --out $ROOT/results_v1/test2); echo "$e bc k2/k5 -> $J"
  J=$(run "BC alone k0 s0-2 $e" $STEP --cpus-per-task=16 --mem=16G --time=$(h 2) --job-name=t2c_bc0_$e \
        $STEP $ROOT/exp_next/exp5/bc_eval.py --split test2 --ks 0 --seeds 0,1,2 --tag k0_s012 \
        --out $ROOT/results_v1/test2); echo "$e bc k0 -> $J"
  J=$(run "final4 + per-qbin shift k5 $e" $STEP --cpus-per-task=16 --mem=16G --time=$(h 1) --job-name=t2c_shift_$e \
        $STEP $ROOT/exp_next/exp5/shift_eval.py --split test2 --variants perqbin:bit --ks 5 --tag qbin_k5 \
        --out $ROOT/results_v1/test2); echo "$e shift -> $J"
  J=$(run "R3 k5 own history (secondary 8) $e" $STEP --dependency=afterok:$R3 --cpus-per-task=16 --mem=32G \
        --time=$(h 4) --job-name=t2c_seqhist_$e $STEP $ROOT/exp_next/fw/seq_history.py --mode own --split test2)
  echo "$e seqhist -> $J"
  envlfq $e
  J=$(run "CQL->PPO 540k @prev k0/k5 s0-2 $e" $STEP --cpus-per-task=16 --mem=32G --time=$(h 3) \
        --job-name=t2c_cqlppo_$e $STEP $ROOT/exp_next/test2/eval_t2.py --model cqlppo --split test2 --ks 0,5)
  echo "$e cqlppo -> $J"
  J=$(run "ABR+VBV m${M[$e]} k0/5 $e" jobs/p2_step.sbatch --cpus-per-task=8 --mem=16G --time=1:00:00 \
        --job-name=t2c_abr_$e jobs/p2_step.sbatch -I exp_next/exp10/abr_margin.py --encoder $e --split test2 \
        --margins ${M[$e]} --ks 0,5); echo "$e abr -> $J"
done
