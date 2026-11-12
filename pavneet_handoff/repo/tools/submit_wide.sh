#!/bin/bash
# Wide-budget study (D28): extend one encoder's finished two-budget run (30/38) to budget QPs 26,30,34,38,42 in a new
# work dir, retrain the core learners (runs/wide.txt), and write reports to results/<codec>_wide/.
# Only new work is computed: STATIC encodes + hindsight search at 26/34/42 (30/38 are reused from the source run).
# usage: bash tools/submit_wide.sh x265|x264
set -euo pipefail
E=$1
SRCW=/scratch1/pbanga/rcwork; [[ $E == x264 ]] && SRCW=/scratch1/pbanga/rcwork_x264
export RC_CODEC=$E RC_SRC_WORK=$SRCW RC_WORK=${SRCW}_wide RC_BUDGETS=26,30,34,38,42 RC_SRC_BUDGETS=30,38
export RC_REPORTS=/scratch1/pbanga/ee599/results/${E}_wide
mkdir -p "$RC_WORK/logs"
P="--partition=main --account=rashidin_1753 --constraint=epyc-7513|epyc-7542"   # xeon-4116 nodes give SIGBUS (135)
cd /scratch1/pbanga/ee599
sb() { sbatch --parsable --export=ALL $P "$@"; }
say() { echo "$E $1 -> $2"; }

PREP=$(sb --cpus-per-task=2 --mem=8G --time=0:20:00 --job-name=${E}w_prep tools/step.sbatch experiments/widen.py --stage prep)
A=$(RC_NSHARDS=8 sb --cpus-per-task=20 --mem=32G --time=2:00:00 --array=0-7 --dependency=afterok:$PREP --job-name=${E}w_infos tools/step.sbatch experiments/widen.py --stage infos)
INF=$(RC_NSHARDS=8 sb --cpus-per-task=2 --mem=32G --time=0:30:00 --dependency=afterok:$A --job-name=${E}w_infos_gather tools/step.sbatch experiments/widen.py --stage gather_infos)
say "prep / infos / gather" "$PREP / $A / $INF"

declare -A NSH=([train]=16 [val]=6 [test]=8)
for s in train val test; do
  n=${NSH[$s]}
  A=$(RC_NSHARDS=$n sb --cpus-per-task=20 --mem=32G --time=4:00:00 --array=0-$((n-1)) --dependency=afterok:$INF --job-name=${E}w_search_$s tools/step.sbatch experiments/widen.py --stage search --split $s)
  G=$(RC_NSHARDS=$n sb --cpus-per-task=2 --mem=96G --time=1:00:00 --dependency=afterok:$A --job-name=${E}w_search_${s}_gather tools/step.sbatch experiments/widen.py --stage gather --split $s)
  declare "SG_$s=$G"
  say "search $s" "$A + gather $G"
done

SPC=$(sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$INF --job-name=${E}w_spend tools/step.sbatch experiments/baselines.py --stage spend_curve)
A=$(RC_NSHARDS=4 sb --cpus-per-task=20 --mem=32G --time=4:00:00 --array=0-3 --dependency=afterok:$INF --job-name=${E}w_own_rc tools/step.sbatch experiments/baselines.py --stage own_rc)
OWN=$(RC_NSHARDS=4 sb --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$A --job-name=${E}w_own_rc_gather tools/step.sbatch experiments/baselines.py --stage gather_own_rc)
RUL=$(sb --cpus-per-task=64 --mem=96G --time=12:00:00 --dependency=afterok:$SPC --job-name=${E}w_rules tools/step.sbatch experiments/baselines.py --stage rules)
say "spend_curve / own_rc / rules" "$SPC / $OWN / $RUL"

n=$(wc -l < runs/wide.txt)
RL=$(sb --cpus-per-task=20 --mem=100G --time=12:00:00 --array=0-$((n-1))%25 --dependency=afterok:$SG_train --job-name=${E}w_rl tools/rl_batch.sbatch runs/wide.txt)
say "rl ($n runs)" "$RL"

REP=$(sb --cpus-per-task=4 --mem=64G --time=2:00:00 --dependency=afterany:$RL:$RUL:$OWN:$SG_val:$SG_test --job-name=${E}w_reports \
      tools/step.sbatch experiments/reports_wide.py)
say reports "$REP"
