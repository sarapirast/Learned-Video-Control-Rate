#!/bin/bash
# Submit one encoder's full pipeline with SLURM dependencies (all sbatch calls go through tools/step.sbatch or
# tools/rl_batch.sbatch). Prints every job id; append them to docs/JOBS.md.
# usage: bash tools/submit_chain.sh x265|x264 [existing_infos_gather_jobid]
set -euo pipefail
E=$1
W=/scratch1/pbanga/rcwork; [[ $E == x264 ]] && W=/scratch1/pbanga/rcwork_x264
export RC_CODEC=$E RC_WORK=$W
P="--partition=main --account=rashidin_1753"   # oneweek QOS caps a user at 50 submitted jobs / 208 CPUs
cd /scratch1/pbanga/ee599

sb() { sbatch --parsable --export=ALL $P "$@"; }
say() { echo "$E $1 -> $2"; }

# 1. infos (unless an infos gather job is given)
if [[ ${2:-} ]]; then INF=$2; else
  A=$(RC_NSHARDS=4 sb --cpus-per-task=20 --mem=32G --time=2:00:00 --array=0-3 --job-name=${E}_infos tools/step.sbatch experiments/infos.py)
  INF=$(RC_NSHARDS=4 sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$A --job-name=${E}_infos_gather tools/step.sbatch experiments/infos.py --stage gather)
  say infos "$A + gather $INF"
fi

# 2. scene detector fit + apply (rewrites cut flags in infos.pkl; must precede rules and RL)
SCN=$(sb --cpus-per-task=2 --mem=16G --time=1:00:00 --dependency=afterok:$INF --job-name=${E}_scenes tools/step.sbatch experiments/scenes.py --stage fit)
SCA=$(sb --cpus-per-task=2 --mem=16G --time=1:00:00 --dependency=afterok:$SCN --job-name=${E}_scenes_apply tools/step.sbatch experiments/scenes.py --stage apply)
say scenes "$SCN, apply $SCA"

# 3. hindsight search, sharded (train keeps logs for offline RL)
declare -A NSH=([train]=16 [val]=6 [test]=8)
for s in train val test; do
  n=${NSH[$s]}
  A=$(RC_NSHARDS=$n sb --cpus-per-task=20 --mem=32G --time=8:00:00 --array=0-$((n-1)) --dependency=afterok:$INF --job-name=${E}_search_$s tools/step.sbatch experiments/search.py --split $s)
  G=$(RC_NSHARDS=$n sb --cpus-per-task=2 --mem=48G --time=1:00:00 --dependency=afterok:$A --job-name=${E}_search_${s}_gather tools/step.sbatch experiments/search.py --split $s --stage gather)
  declare "SG_$s=$G"
  say "search $s" "$A + gather $G"
done

# 4. baselines: own RC + fixed-pattern refit (sharded), rules (after scene apply), teacher-around-cuts (after search)
A=$(RC_NSHARDS=4 sb --cpus-per-task=20 --mem=32G --time=4:00:00 --array=0-3 --dependency=afterok:$INF --job-name=${E}_own_rc tools/step.sbatch experiments/baselines.py --stage own_rc)
OWN=$(RC_NSHARDS=4 sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$A --job-name=${E}_own_rc_gather tools/step.sbatch experiments/baselines.py --stage gather_own_rc)
A=$(RC_NSHARDS=4 sb --cpus-per-task=20 --mem=32G --time=4:00:00 --array=0-3 --dependency=afterok:$INF --job-name=${E}_static_pattern tools/step.sbatch experiments/baselines.py --stage static_pattern)
PAT=$(RC_NSHARDS=4 sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$A --job-name=${E}_static_pattern_gather tools/step.sbatch experiments/baselines.py --stage gather_static_pattern)
RUL=$(sb --cpus-per-task=32 --mem=48G --time=12:00:00 --dependency=afterok:$SCA --job-name=${E}_rules tools/step.sbatch experiments/baselines.py --stage rules)
TCH=$(sb --cpus-per-task=2 --mem=48G --time=1:00:00 --dependency=afterok:$SCA:$SG_train --job-name=${E}_scenes_teacher tools/step.sbatch experiments/scenes.py --stage teacher)
say baselines "own_rc $OWN, static_pattern $PAT, rules $RUL, teacher $TCH"

# 5. RL arrays (each task = one run; throttled so each study keeps ~25 jobs running)
RL=""
for f in core methods features scenes; do
  n=$(wc -l < runs/$f.txt)
  A=$(sb --cpus-per-task=20 --mem=60G --time=12:00:00 --array=0-$((n-1))%25 --dependency=afterok:$SG_train:$SCA --job-name=${E}_rl_$f tools/rl_batch.sbatch runs/$f.txt)
  RL="$RL:$A"
  say "rl $f ($n runs)" "$A"
done

# 6. all reports once everything above has ended (afterany: partial failures still get reported)
REP=$(sb --cpus-per-task=4 --mem=48G --time=2:00:00 --dependency=afterany$RL:$RUL:$OWN:$PAT:$TCH:$SG_test:$SG_val --job-name=${E}_reports tools/step.sbatch experiments/reports.py)
say reports "$REP"
echo "$REP" > "$W/last_reports_job"
