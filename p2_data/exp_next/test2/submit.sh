#!/bin/bash
# test2 submissions in waves (exp_next/test2/PLAN.md section 4); every job logged with scripts/joblog.sh.
#   bash exp_next/test2/submit.sh <wave> [dep]        dry run: prints the sbatch commands
#   bash exp_next/test2/submit.sh <wave> [dep] go     submits (only with Aayush's OK)
# dep = job id the wave's first jobs wait for (afterok), e.g. the decode array for wave A.
# Wave B: flat GOPs, budgets -> final4 / final3 (tags t2final4 / t2final3; test2 in 8 shards, parity in 1) ->
#         previous-GOP base; rc manifest -> Pavneet's orig infos (8 shards) -> gather -> lf infos -> resh infos
#         (final4 history) and lfqp infos_learn (previous-GOP base). Work dirs: /scratch1/aayushso/rcwork_t2.
#         Before submitting: the lfq/lfqp/resh link setup (prepare_dirs below, run with "go").
# Wave A: manifest merge -> cut signals -> cut labels (rule + v1 verdicts for the parity clips) ->
#         { constant-QP curves + first pass (rd_native, 4 shards per encoder) -> gather,
#           first-pass stats (fp_stats, 2 shards per encoder) -> gather }
set -euo pipefail
WAVE=${1:?wave}
DEP=${2:-}
GO=${3:-}
[[ $DEP == go ]] && { GO=go; DEP=; }
ROOT=/scratch1/aayushso/ee599
cd "$ROOT"
export P2_DATA=$ROOT/data/t2/320x180
EXCL=$(scripts/bad_nodes.sh exclude)
run() {   # run <log text> <script> <sbatch args...> ; echoes the job id
  local text=$1 script=$2; shift 2
  if [[ $GO == go ]]; then
    local id; id=$(sbatch --parsable --export=ALL ${EXCL:+--exclude=$EXCL} ${PART:+--partition=$PART} "$@")
    scripts/joblog.sh add "$id" "$script" "test2: $text" >/dev/null
    echo "$id"
  else
    echo "DRY sbatch $*" >&2; echo "DRY$RANDOM"
  fi
}
after() { [[ -n ${1:-} ]] && echo "--dependency=afterok:$1" || true; }
prepare_dirs() {   # test2 work dirs: lfq (lfqp's link source) and the frozen v1 checkpoints for resh / lfqp
  local R=/scratch1/aayushso/rcwork_t2 V=/scratch1/aayushso/rcwork_v1 e
  for e in x264 x265; do
    local cmds=("mkdir -p $R/${e}_lfq/results_infos $R/${e}_resh $R/${e}_lfqp"
      "ln -sfn $R/${e}_lf/results_infos/infos.pkl $R/${e}_lfq/results_infos/infos.pkl"
      "ln -sfn $R/${e}_orig/clips $R/${e}_lfq/clips" "ln -sfn $R/${e}_orig/gops $R/${e}_lfq/gops"
      "ln -sfn $R/${e}_orig/manifest.json $R/${e}_lfq/manifest.json"
      "ln -sfn $V/${e}_resh/results_rl $R/${e}_resh/results_rl" "ln -sfn $V/${e}_lfqp/results_rl $R/${e}_lfqp/results_rl")
    local c; for c in "${cmds[@]}"; do if [[ $GO == go ]]; then $c; else echo "DRY $c" >&2; fi; done
  done
}

case $WAVE in
A)
  M=$(run "decode merge -> data/t2/320x180/manifest.csv" jobs/p2_step.sbatch $(after "$DEP") --cpus-per-task=1 --mem=2G \
        --time=0:10:00 --job-name=t2_merge jobs/p2_step.sbatch -I scripts/decode_clips.py --merge --out "$P2_DATA")
  echo "merge -> $M"
  S=$(run "cut signals (hist / scdet / luma), 96 clips" jobs/p2_step.sbatch $(after "$M") --cpus-per-task=2 --mem=8G \
        --time=2:00:00 --job-name=t2_cutsig jobs/p2_step.sbatch -I scripts/cut_labels.py --signals)
  echo "cut signals -> $S"
  L=$(run "cut labels (rule; v1 verdicts apply to the parity clips) -> gops.csv" jobs/p2_step.sbatch $(after "$S") \
        --cpus-per-task=1 --mem=4G --time=0:20:00 --job-name=t2_cutlab jobs/p2_step.sbatch -I scripts/cut_labels.py --label)
  echo "cut labels -> $L"
  RD=()
  for e in x264 x265; do
    J=$(run "constant-QP curves 18-50 + first pass, $e, 4 shards" jobs/rd_native.sbatch $(after "$L") --array=0-3 \
          --cpus-per-task=16 --mem=32G --time=2:00:00 --job-name=t2_rd_$e jobs/rd_native.sbatch --encoder $e --nshards 4)
    echo "rd $e -> $J"; RD+=("$J")
    F=$(run "first-pass stats, $e, 2 shards" jobs/p2_step.sbatch $(after "$L") --array=0-1 --cpus-per-task=16 --mem=16G \
          --time=1:00:00 --job-name=t2_fpst_$e jobs/p2_step.sbatch -I scripts/fp_stats.py --encoder $e --nshards 2)
    echo "fp_stats $e -> $F"; RD+=("$F")
  done
  G=$(run "rd gather -> rd_native / rd_frames / fp_bits" jobs/rd_native.sbatch --dependency=afterok:${RD[0]}:${RD[2]} \
        --cpus-per-task=2 --mem=32G --time=0:30:00 --job-name=t2_rd_gather jobs/rd_native.sbatch --gather)
  echo "rd gather -> $G"
  H=$(run "fp_stats gather -> features/fp_stats.parquet" jobs/p2_step.sbatch --dependency=afterok:${RD[1]}:${RD[3]} \
        --cpus-per-task=2 --mem=16G --time=0:30:00 --job-name=t2_fpst_gather jobs/p2_step.sbatch -I scripts/fp_stats.py --gather)
  echo "fp_stats gather -> $H"
  ;;
B)
  # dep = the two wave-A gathers, "rdgather:fpgather"
  F4=1.0:6:1.0:2:3:4:1:1:1:0:3; F3=1.0:9:1.0:2:3:4:0:1:1:0
  RCT=/scratch1/aayushso/rcwork_t2
  FL=$(run "flat GOPs (QP-50 YUV PSNR rule)" jobs/p2_step.sbatch $(after "$DEP") --cpus-per-task=1 --mem=8G --time=0:15:00 \
        --job-name=t2_flat jobs/p2_step.sbatch -I scripts/flat_gops_v1.py); echo "flat -> $FL"
  BU=$(run "budgets + causal base-QP estimate (v1-train fit)" jobs/p2_step.sbatch $(after "$DEP") --cpus-per-task=2 \
        --mem=16G --time=0:30:00 --job-name=t2_budgets jobs/p2_step.sbatch -I exp_next/test2/budgets_t2.py)
  echo "budgets -> $BU"
  declare -A F3J=([x264]="" [x265]="")
  F4J=""
  prepare_dirs
  for e in x264 x265; do
    for sp in test2 parity; do
      n=$([[ $sp == test2 ]] && echo 8 || echo 1)
      J=$(run "controller final4 (h=3, clip-sequential), $e $sp, k 0/2/5/10/29, tag t2final4" jobs/p2_step.sbatch \
            --dependency=afterok:$BU --array=0-$((n - 1)) --cpus-per-task=16 --mem=16G --time=1:00:00 \
            --job-name=t2_f4_${e}_$sp jobs/p2_step.sbatch -I scripts/controller_real.py --encoder $e --split $sp \
            --settings $F4 --nshards $n --tag t2final4); echo "final4 $e $sp -> $J"; F4J+=":$J"
      J=$(run "controller final3, $e $sp, k 0/2/5/10/29, tag t2final3 (history for CQL->PPO @prev)" jobs/p2_step.sbatch \
            --dependency=afterok:$BU --array=0-$((n - 1)) --cpus-per-task=16 --mem=16G --time=1:00:00 \
            --job-name=t2_f3_${e}_$sp jobs/p2_step.sbatch -I scripts/controller_real.py --encoder $e --split $sp \
            --settings $F3 --nshards $n --tag t2final3); echo "final3 $e $sp -> $J"; F3J[$e]+=":$J"
    done
    BP=$(run "previous-GOP base (frozen v1 fit), $e" jobs/p2_step.sbatch --dependency=afterok${F3J[$e]} --cpus-per-task=2 \
          --mem=8G --time=0:20:00 --job-name=t2_bprev_$e jobs/p2_step.sbatch -I exp_next/test2/base_prev_t2.py $e)
    echo "base_prev $e -> $BP"
    # Pavneet's orig infos (his pixel scene analysis an, first pass, curves, STATIC encodes), rc env
    MJ=$(run "rc manifest + clip links -> $RCT/${e}_orig" jobs/p2_step.sbatch $(after "$DEP") --cpus-per-task=1 --mem=2G \
          --time=0:10:00 --job-name=t2_rcman_$e jobs/p2_step.sbatch -I scripts/v1_rc_manifest.py $RCT/${e}_orig)
    echo "rc manifest $e -> $MJ"
    IJ=$(export RC_CODEC=$e RC_ARM=orig RC_WORK=$RCT/${e}_orig RC_REPORTS=$ROOT/results_v1/test2/${e}_orig RC_NSHARDS=8
         run "Pavneet orig infos (an, curves, STATIC), $e, 8 shards" jobs/rc_v1_step.sbatch --dependency=afterok:$MJ \
         --array=0-7 --cpus-per-task=16 --mem=32G --time=1:00:00 --job-name=t2_infos_$e jobs/rc_v1_step.sbatch \
         experiments/infos.py --stage infos); echo "orig infos $e -> $IJ"
    GJ=$(export RC_CODEC=$e RC_ARM=orig RC_WORK=$RCT/${e}_orig RC_REPORTS=$ROOT/results_v1/test2/${e}_orig RC_NSHARDS=8
         run "Pavneet orig infos gather, $e" jobs/rc_v1_step.sbatch --dependency=afterok:$IJ --cpus-per-task=2 --mem=16G \
         --time=0:30:00 --job-name=t2_infosg_$e jobs/rc_v1_step.sbatch experiments/infos.py --stage gather)
    echo "orig infos gather $e -> $GJ"
    LF=$(run "lf infos (P2 curves / budgets) $e" jobs/p2_step.sbatch --dependency=afterok:$GJ:$BU --cpus-per-task=2 \
          --mem=16G --time=0:30:00 --job-name=t2_lf_$e jobs/p2_step.sbatch -I repo-pavneet/tools/lf_infos.py $e \
          $RCT/${e}_orig $RCT/${e}_lf); echo "lf infos $e -> $LF"
    RS=$(run "resh infos (final4 history, dPSNR_B) $e" jobs/p2_step.sbatch --dependency=afterok:$LF:$FL$F4J \
          --cpus-per-task=2 --mem=16G --time=0:30:00 --job-name=t2_resh_$e jobs/p2_step.sbatch -I \
          repo-pavneet/tools/res_infos.py $e $RCT/${e}_lf $RCT/${e}_resh --tag t2final4 --setting $F4 --metric dpsnr)
    echo "resh infos $e -> $RS"
    LQ=$(export P2_RCWORK=$RCT; run "lfqp infos_learn (previous-GOP base, no search) $e" jobs/p2_step.sbatch \
          --dependency=afterok:$LF:$FL:$BP --cpus-per-task=2 --mem=16G --time=0:30:00 --job-name=t2_lfqp_$e \
          jobs/p2_step.sbatch -I repo-pavneet/tools/lfq_infos.py $e --workname lfqp \
          --base-csv $P2_DATA/budgets_prev_$e.csv --allow-missing train,val,test,test2,parity)
    echo "lfqp infos $e -> $LQ"
    F4J=""
  done
  ;;
B265)
  # resubmission of wave B's x265 jobs rejected on 11-17 by the oneweek QOS limit (50 queued jobs per user; the
  # sbatch files list main,oneweek): PART=main, reusing budgets 14324218/14324219 and x265 final4 14324231/14324232.
  PART=main
  F4=1.0:6:1.0:2:3:4:1:1:1:0:3; F3=1.0:9:1.0:2:3:4:0:1:1:0
  RCT=/scratch1/aayushso/rcwork_t2; e=x265; FL=14324218; BU=14324219; F4J=":14324231:14324232"; F3J=""
  for sp in test2 parity; do
    n=$([[ $sp == test2 ]] && echo 8 || echo 1)
    J=$(run "controller final3, $e $sp, k 0/2/5/10/29, tag t2final3 (history for CQL->PPO @prev)" jobs/p2_step.sbatch \
          --dependency=afterok:$BU --array=0-$((n - 1)) --cpus-per-task=16 --mem=16G --time=1:00:00 \
          --job-name=t2_f3_${e}_$sp jobs/p2_step.sbatch -I scripts/controller_real.py --encoder $e --split $sp \
          --settings $F3 --nshards $n --tag t2final3); echo "final3 $e $sp -> $J"; F3J+=":$J"
  done
  BP=$(run "previous-GOP base (frozen v1 fit), $e" jobs/p2_step.sbatch --dependency=afterok$F3J --cpus-per-task=2 \
        --mem=8G --time=0:20:00 --job-name=t2_bprev_$e jobs/p2_step.sbatch -I exp_next/test2/base_prev_t2.py $e)
  echo "base_prev $e -> $BP"
  MJ=$(run "rc manifest + clip links -> $RCT/${e}_orig" jobs/p2_step.sbatch $(after "$DEP") --cpus-per-task=1 --mem=2G \
        --time=0:10:00 --job-name=t2_rcman_$e jobs/p2_step.sbatch -I scripts/v1_rc_manifest.py $RCT/${e}_orig)
  echo "rc manifest $e -> $MJ"
  IJ=$(export RC_CODEC=$e RC_ARM=orig RC_WORK=$RCT/${e}_orig RC_REPORTS=$ROOT/results_v1/test2/${e}_orig RC_NSHARDS=8
       run "Pavneet orig infos (an, curves, STATIC), $e, 8 shards" jobs/rc_v1_step.sbatch --dependency=afterok:$MJ \
       --array=0-7 --cpus-per-task=16 --mem=32G --time=1:00:00 --job-name=t2_infos_$e jobs/rc_v1_step.sbatch \
       experiments/infos.py --stage infos); echo "orig infos $e -> $IJ"
  GJ=$(export RC_CODEC=$e RC_ARM=orig RC_WORK=$RCT/${e}_orig RC_REPORTS=$ROOT/results_v1/test2/${e}_orig RC_NSHARDS=8
       run "Pavneet orig infos gather, $e" jobs/rc_v1_step.sbatch --dependency=afterok:$IJ --cpus-per-task=2 --mem=16G \
       --time=0:30:00 --job-name=t2_infosg_$e jobs/rc_v1_step.sbatch experiments/infos.py --stage gather)
  echo "orig infos gather $e -> $GJ"
  LF=$(run "lf infos (P2 curves / budgets) $e" jobs/p2_step.sbatch --dependency=afterok:$GJ:$BU --cpus-per-task=2 \
        --mem=16G --time=0:30:00 --job-name=t2_lf_$e jobs/p2_step.sbatch -I repo-pavneet/tools/lf_infos.py $e \
        $RCT/${e}_orig $RCT/${e}_lf); echo "lf infos $e -> $LF"
  RS=$(run "resh infos (final4 history, dPSNR_B) $e" jobs/p2_step.sbatch --dependency=afterok:$LF:$FL$F4J \
        --cpus-per-task=2 --mem=16G --time=0:30:00 --job-name=t2_resh_$e jobs/p2_step.sbatch -I \
        repo-pavneet/tools/res_infos.py $e $RCT/${e}_lf $RCT/${e}_resh --tag t2final4 --setting $F4 --metric dpsnr)
  echo "resh infos $e -> $RS"
  LQ=$(export P2_RCWORK=$RCT; run "lfqp infos_learn (previous-GOP base, no search) $e" jobs/p2_step.sbatch \
        --dependency=afterok:$LF:$FL:$BP --cpus-per-task=2 --mem=16G --time=0:30:00 --job-name=t2_lfqp_$e \
        jobs/p2_step.sbatch -I repo-pavneet/tools/lfq_infos.py $e --workname lfqp \
        --base-csv $P2_DATA/budgets_prev_$e.csv --allow-missing train,val,test,test2,parity)
  echo "lfqp infos $e -> $LQ"
  ;;
*)
  echo "unknown wave $WAVE"; exit 1 ;;
esac
