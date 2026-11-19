#!/bin/bash
# D41 hindsight oracle in the leak-fixed setting (RC_BUF_LADDER=1, D45), one encoder: debug (3 tiny lines, debug
# partition) -> 16 shards (after the debug passes) -> report per channel. Outputs: results_buffer{,_trace}_ladder/oracle*.
# usage: bash tools/submit_buffer_ladder_oracle.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E
cd /scratch1/pbanga/ee599
O="--account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out --cpus-per-task=2 --mem=8G"
DB=$(sbatch --parsable --export=ALL $O --partition=debug --time=0:30:00 --array=0-2 --job-name=${E}_lad_orc_dbg tools/oracle_task.sbatch runs/buffer_ladder_oracle_debug.txt)
RU=$(sbatch --parsable --export=ALL $O --partition=main --time=1:00:00 --array=0-15%6 --dependency=afterok:$DB --job-name=${E}_lad_oracle tools/oracle_task.sbatch runs/buffer_ladder_oracle.txt)
REP=$(sbatch --parsable --export=ALL $O --partition=main --time=0:20:00 --array=0-1 --dependency=afterany:$RU --job-name=${E}_lad_orc_rep tools/oracle_task.sbatch runs/buffer_ladder_oracle_report.txt)
echo "$E ladder oracle: debug $DB / run $RU / report $REP"
