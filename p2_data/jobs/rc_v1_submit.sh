#!/bin/bash
# Submit stages of Pavneet's pipeline on data v1, one encoder x budget arm at a time, with SLURM dependencies.
# Every submission is logged with scripts/joblog.sh.
#   lf (leak-free, 2026-11-09): run tools/lf_infos.py first; "AB" then submits only the search (RC_SPLITS to limit)
#   bash jobs/rc_v1_submit.sh <x265|x264> <orig|dec> AB     stage A (infos, scenes, own RC, STATIC pattern) + B (search)
#   [RC_DEP=<jobid>] [RC_TASKS=4,11,..] [RC_RUNS=list] [RC_PART=debug RC_TLIM=0:50:00] bash jobs/rc_v1_submit.sh <x265|x264> <orig|dec|lf|res> C
#       RL runs from runs_v1/<arm>.txt (needs B's train search); RC_TASKS reruns only those lines (0-based)
# Trimmed scope (Aayush, 2026-11-03): dec arm reuses the orig arm's stage A (tools/budget_arm.py) and searches
# train + test only. Allocated CPU-h per encoder: orig AB ~150, dec B ~150, orig C ~350, dec C ~180.
set -euo pipefail
E=$1 ARM=$2 WHAT=$3
ROOT=/scratch1/aayushso/ee599
# RC_WORKNAME: another work dir for the same arm (e.g. resq = res arm, dPSNR_B reward, retuned controller; 2026-11-10)
export RC_CODEC=$E RC_ARM=$ARM RC_WORK=/scratch1/aayushso/rcwork_v1/${E}_${RC_WORKNAME:-$ARM}
mkdir -p /scratch1/aayushso/rcwork_v1/logs "$RC_WORK"
cd "$ROOT"
S=jobs/rc_v1_step.sbatch
EXCL=$(scripts/bad_nodes.sh exclude)   # dated list in jobs/bad_nodes.txt (entries expire after 3 days)
[[ -n $EXCL ]] && echo "excluding nodes: $EXCL"
sb() { sbatch --parsable --export=ALL ${EXCL:+--exclude=$EXCL} ${RC_PART:+--partition=$RC_PART} "$@"; }
log() { scripts/joblog.sh add "$1" "$S" "rc_v1 $E/$ARM${RC_WORKNAME:+ ($RC_WORKNAME)}: $2" >/dev/null; echo "$E/$ARM $2 -> $1"; }

if [[ $WHAT == AB ]]; then
  if [[ $ARM == orig ]]; then
    A=$(RC_NSHARDS=4 sb --cpus-per-task=16 --mem=32G --time=1:00:00 --array=0-3 --job-name=${E}_${ARM}_infos $S experiments/infos.py)
    log "$A" "infos array (4 shards)"
    INF=$(RC_NSHARDS=4 sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$A --job-name=${E}_${ARM}_infos_gather $S experiments/infos.py --stage gather)
    log "$INF" "infos gather"
    SCN=$(sb --cpus-per-task=2 --mem=16G --time=1:00:00 --dependency=afterok:$INF --job-name=${E}_${ARM}_scenes $S experiments/scenes.py --stage fit)
    log "$SCN" "scene detector fit"
    SCA=$(sb --cpus-per-task=2 --mem=16G --time=1:00:00 --dependency=afterok:$SCN --job-name=${E}_${ARM}_scenes_apply $S experiments/scenes.py --stage apply)
    log "$SCA" "scene detector apply"
    for st in own_rc static_pattern; do
      A=$(RC_NSHARDS=4 sb --cpus-per-task=16 --mem=32G --time=2:00:00 --array=0-3 --dependency=afterok:$INF --job-name=${E}_${ARM}_$st $S experiments/baselines.py --stage $st)
      G=$(RC_NSHARDS=4 sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$A --job-name=${E}_${ARM}_${st}_gather $S experiments/baselines.py --stage gather_$st)
      log "$A" "$st array"; log "$G" "$st gather"
    done
    RUL=$(sb --cpus-per-task=16 --mem=48G --time=6:00:00 --dependency=afterok:$SCA --job-name=${E}_${ARM}_rules $S experiments/baselines.py --stage rules)
    log "$RUL" "hand rules (val tune + test)"
    SPLITS="train val test"; DEP=$SCA
  elif [[ $ARM == lf || $ARM == lfq ]]; then
    # leak-free arm (P2, 2026-11-09): infos built from P2's v1 data by tools/lf_infos.py (no encodes); all splits;
    # 4 budget levels -> twice the orig search time, so a longer limit
    [[ -s $RC_WORK/results_infos/infos.pkl ]] || { echo "run tools/lf_infos.py first"; exit 1; }
    SPLITS="${RC_SPLITS:-train val test}"; DEP=""; TLIM=8:00:00
  else
    # dec arm: derive infos from the finished orig arm (run tools/budget_arm.py by hand first; no encodes)
    [[ -s $RC_WORK/results_infos/infos.pkl ]] || { echo "run tools/budget_arm.py first"; exit 1; }
    SPLITS="train test"; DEP=""
  fi
  declare -A NSH=([train]=8 [val]=3 [test]=4)
  for s in $SPLITS; do
    n=${NSH[$s]}
    A=$(RC_NSHARDS=$n sb --cpus-per-task=16 --mem=32G --time=${TLIM:-4:00:00} --array=0-$((n-1)) ${DEP:+--dependency=afterok:$DEP} --job-name=${E}_${ARM}_search_$s $S experiments/search.py --split $s)
    G=$(RC_NSHARDS=$n sb --cpus-per-task=2 --mem=48G --time=1:00:00 --dependency=afterok:$A --job-name=${E}_${ARM}_search_${s}_gather $S experiments/search.py --split $s --stage gather)
    log "$A" "search $s ($n shards)"; log "$G" "search $s gather"
  done
elif [[ $WHAT == C ]]; then
  F=$(realpath "${RC_RUNS:-$ROOT/runs_v1/$ARM.txt}")   # RC_RUNS: another run list, e.g. runs_v1/shape.txt (made absolute: the job cds)
  [[ -s $F ]] || { echo "run list $F missing"; exit 1; }
  n=$(wc -l < "$F")
  # optional RC_DEP=<jobid>: start only after that job (e.g. the search train gather) succeeds
  A=$(RC_ENVS=14 sb --cpus-per-task=16 --mem=48G --time=${RC_TLIM:-4:00:00} --array=${RC_TASKS:-0-$((n-1))}%20 ${RC_DEP:+--dependency=afterok:$RC_DEP} --job-name=${E}_${ARM}_rl jobs/rc_v1_rl.sbatch "$F")
  scripts/joblog.sh add "$A" jobs/rc_v1_rl.sbatch "rc_v1 $E/$ARM${RC_WORKNAME:+ ($RC_WORKNAME, ${RC_METRIC:-default} metric)}: RL array (${RC_TASKS:+rerun tasks $RC_TASKS of }$n runs, $(basename "$F"))" >/dev/null
  echo "$E/$ARM RL (${RC_TASKS:+tasks $RC_TASKS of }$n runs) -> $A"
else
  echo "usage: $0 <x265|x264> <orig|dec|lf> <AB|C>"; exit 1
fi
