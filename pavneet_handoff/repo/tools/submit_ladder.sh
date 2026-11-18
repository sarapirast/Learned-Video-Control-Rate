#!/bin/bash
# D44: TA-feedback rerun on the original dataset with decision-time budgets (fixed bitrate ladder) and the causal
# online controller as the base (residual RL), for one encoder. Writes only to /scratch1/pbanga/rcwork_ladder/<codec>
# and results/<codec>_ladder. usage: bash tools/submit_ladder.sh x265|x264
set -euo pipefail
export RC_CODEC=$1
cd /scratch1/pbanga/ee599
source tools/ladder_env.sh
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out"
sb() { sbatch --parsable --export=ALL $P "$@"; }
say() { echo "$RC_CODEC $1 -> $2"; }

PRE=$(sb --cpus-per-task=20 --mem=32G --time=3:00:00 --job-name=${RC_CODEC}L_prep tools/step.sbatch experiments/ladder_prep.py --src $LADDER_SRC)
say "prep (ladder budgets, controller plans)" "$PRE"

declare -A NSH=([train]=16 [test]=8)
for s in train test; do
  n=${NSH[$s]}
  A=$(RC_NSHARDS=$n sb --cpus-per-task=20 --mem=32G --time=4:00:00 --array=0-$((n-1)) --dependency=afterok:$PRE --job-name=${RC_CODEC}L_search_$s tools/step.sbatch experiments/search.py --split $s)
  G=$(RC_NSHARDS=$n sb --cpus-per-task=2 --mem=64G --time=1:00:00 --dependency=afterok:$A --job-name=${RC_CODEC}L_search_${s}_gather tools/step.sbatch experiments/search.py --split $s --stage gather)
  declare "SG_$s=$G"
  say "search $s" "$A + gather $G"
done

OWN=$(RC_NSHARDS=8 sb --cpus-per-task=20 --mem=32G --time=4:00:00 --array=0-7 --dependency=afterok:$PRE --job-name=${RC_CODEC}L_own tools/step.sbatch experiments/baselines.py --stage own_rc)
OWNG=$(RC_NSHARDS=8 sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$OWN --job-name=${RC_CODEC}L_own_gather tools/step.sbatch experiments/baselines.py --stage gather_own_rc)
say "encoder own RC" "$OWN + gather $OWNG"

n=$(wc -l < runs/ladder.txt)
RL=$(sb --cpus-per-task=20 --mem=64G --time=6:00:00 --array=0-$((n-1))%10 --dependency=afterok:$SG_train --job-name=${RC_CODEC}L_rl tools/rl_batch.sbatch runs/ladder.txt)
REP=$(sb --cpus-per-task=2 --mem=16G --time=0:45:00 --dependency=afterany:$RL:$SG_test:$OWNG --job-name=${RC_CODEC}L_report tools/step.sbatch experiments/quality_violations.py)
say "rl ($n runs, 10 at a time) / report" "$RL / $REP"
