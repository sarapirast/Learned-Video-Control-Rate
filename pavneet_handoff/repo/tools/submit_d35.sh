#!/bin/bash
# D35 full runs for one encoder (v1 encoder settings: RC_V1=1, preset medium).
#  (a) encoder rate control on the D34 v1 test streams (724 cases at s = 1): curve check, 8 shards x 4 CPUs, gather + report
#  (b) fresh long-film set: curves for 384 GOPs (4 shards x 8 CPUs), gather, budgets (prep), then the D34 policies and
#      rule applied unchanged at N = 8 / 16 / 32, report. Manifest and GOP files already exist (debug run).
# Writes only to rcwork_v1/<codec>/results_own_rc_stream_v1, rcwork_fresh/<codec>, results/v1_stream/<codec>,
# results/fresh_stream/<codec>.   usage: bash tools/submit_d35.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_V1=1 RC_PRESET=medium RC_BUDGETS=24,30,36,42
cd /scratch1/pbanga/ee599
V=/scratch1/pbanga/rcwork_v1/$E F=/scratch1/pbanga/rcwork_fresh/$E
mkdir -p $V/logs $F/logs
sb() { local w=$1; shift; RC_WORK=$w sbatch --parsable --export=ALL --partition=main --account=rashidin_1753 --output=$w/logs/%x-%A_%a.out "$@"; }
CK=$(sb $V --cpus-per-task=2 --mem=8G --time=0:30:00 --job-name=${E}_ownrc_v1_check tools/step.sbatch experiments/own_rc_stream_v1.py --stage check)
A=$(RC_NSHARDS=8 sb $V --cpus-per-task=4 --mem=8G --time=1:30:00 --array=0-7 --job-name=${E}_ownrc_v1 tools/step.sbatch experiments/own_rc_stream_v1.py --stage run)
AG=$(RC_NSHARDS=8 sb $V --cpus-per-task=2 --mem=8G --time=0:30:00 --dependency=afterok:$A:$CK --job-name=${E}_ownrc_v1_gather tools/step.sbatch experiments/own_rc_stream_v1.py --stage gather)
I=$(RC_NSHARDS=4 sb $F --cpus-per-task=8 --mem=16G --time=1:00:00 --array=0-3 --job-name=${E}_fresh_infos tools/step.sbatch experiments/infos.py --stage infos)
IG=$(RC_NSHARDS=4 sb $F --cpus-per-task=2 --mem=16G --time=0:30:00 --dependency=afterok:$I --job-name=${E}_fresh_gather tools/step.sbatch experiments/infos.py --stage gather)
P=$(sb $F --cpus-per-task=2 --mem=8G --time=0:20:00 --dependency=afterok:$IG --job-name=${E}_fresh_prep tools/step.sbatch tools/fresh_streams.py --stage prep)
EV=$(RC_V1WORK=$V sb $F --cpus-per-task=2 --mem=8G --time=2:00:00 --dependency=afterok:$P --job-name=${E}_fresh_eval tools/step.sbatch experiments/stream_fresh.py)
R=$(RC_V1WORK=$V sb $F --cpus-per-task=2 --mem=8G --time=0:20:00 --dependency=afterok:$EV --job-name=${E}_fresh_report tools/step.sbatch experiments/stream_fresh.py --report)
echo "$E ownrc check $CK, run $A, gather $AG | fresh infos $I, gather $IG, prep $P, eval $EV, report $R"
