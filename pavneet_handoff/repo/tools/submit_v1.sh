#!/bin/bash
# Dataset v1, Stage 1 (D31) for one encoder: infos -> scenes -> controller plans -> hindsight search -> 26 RL runs -> report.
# Only reads Aayush's clips, GOP files and manifest; everything written goes to /scratch1/pbanga/rcwork_v1/<codec> and
# results/v1/<codec>, apart from the initial dataset's work dirs and reports.
# usage: bash tools/submit_v1.sh x265|x264
set -euo pipefail
E=$1
S=/scratch1/aayushso/rcwork_v1/x265_orig
export RC_V1=1 RC_PRESET=medium RC_BUDGETS=24,30,36,42 RC_CODEC=$E
export RC_WORK=/scratch1/pbanga/rcwork_v1/$E RC_REPORTS=/scratch1/pbanga/ee599/results/v1/$E
cd /scratch1/pbanga/ee599
mkdir -p "$RC_WORK/logs" "$RC_REPORTS"
[ -e "$RC_WORK/clips" ] || ln -s $S/clips "$RC_WORK/clips"
[ -e "$RC_WORK/gops" ] || ln -s $S/gops "$RC_WORK/gops"
[ -e "$RC_WORK/manifest.json" ] || cp $S/manifest.json "$RC_WORK/manifest.json"
P="--partition=main --account=rashidin_1753 --constraint=epyc-7513|epyc-7542 --output=$RC_WORK/logs/%x-%A_%a.out"
sb() { sbatch --parsable --export=ALL $P "$@"; }
say() { echo "$E $1 -> $2"; }

A=$(RC_NSHARDS=4 sb --cpus-per-task=20 --mem=32G --time=2:00:00 --array=0-3 --job-name=${E}v_infos tools/step.sbatch experiments/infos.py)
INF=$(RC_NSHARDS=4 sb --cpus-per-task=2 --mem=32G --time=0:30:00 --dependency=afterok:$A --job-name=${E}v_infos_gather tools/step.sbatch experiments/infos.py --stage gather)
SCN=$(sb --cpus-per-task=2 --mem=16G --time=1:00:00 --dependency=afterok:$INF --job-name=${E}v_scenes tools/step.sbatch experiments/scenes.py --stage fit)
SCA=$(sb --cpus-per-task=2 --mem=16G --time=1:00:00 --dependency=afterok:$SCN --job-name=${E}v_scenes_apply tools/step.sbatch experiments/scenes.py --stage apply)
PRE=$(sb --cpus-per-task=20 --mem=32G --time=3:00:00 --dependency=afterok:$SCA --job-name=${E}v_prep tools/step.sbatch experiments/v1_prep.py)
say "infos / gather / scenes / prep" "$A / $INF / $SCN+$SCA / $PRE"

declare -A NSH=([train]=16 [val]=4 [test]=6)
for s in train val test; do
  n=${NSH[$s]}
  A=$(RC_NSHARDS=$n sb --cpus-per-task=20 --mem=32G --time=4:00:00 --array=0-$((n-1)) --dependency=afterok:$PRE --job-name=${E}v_search_$s tools/step.sbatch experiments/search.py --split $s)
  G=$(RC_NSHARDS=$n sb --cpus-per-task=2 --mem=64G --time=1:00:00 --dependency=afterok:$A --job-name=${E}v_search_${s}_gather tools/step.sbatch experiments/search.py --split $s --stage gather)
  declare "SG_$s=$G"
  say "search $s" "$A + gather $G"
done

n=$(wc -l < runs/v1_stage1.txt)
RL=$(sb --cpus-per-task=20 --mem=64G --time=6:00:00 --array=0-$((n-1))%13 --dependency=afterok:$SG_train --job-name=${E}v_rl tools/rl_batch.sbatch runs/v1_stage1.txt)
REP=$(sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterany:$RL --job-name=${E}v_report tools/step.sbatch experiments/v1_report.py)
say "rl ($n runs) / report" "$RL / $REP"
