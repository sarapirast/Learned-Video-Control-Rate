#!/bin/bash
# D36: meta-RL for stream rate control, one encoder. Curve lookups only, no encodes.
#   learners : runs/stream_meta.txt (rppo_fb / rppo / ppo_fb at L=2, rppo_fb at L=0, 3 seeds = 12), at most 6 at a time
#   report   : after all learners (afterany)
# Reads rcwork_v1/<codec> (infos, D34 baselines and policies) and rcwork_fresh/<codec> (fresh infos, D35 results).
# Writes only to rcwork_v1/<codec>/results_stream_meta, rcwork_v1/<codec>/logs and results/v1_stream_meta/<codec>.
# usage: bash tools/submit_meta.sh x265|x264
set -euo pipefail
E=$1
export RC_CODEC=$E RC_WORK=/scratch1/pbanga/rcwork_v1/$E RC_FRESHWORK=/scratch1/pbanga/rcwork_fresh/$E
cd /scratch1/pbanga/ee599
mkdir -p "$RC_WORK/logs"
P="--partition=main --account=rashidin_1753 --output=$RC_WORK/logs/%x-%A_%a.out"
sb() { sbatch --parsable --export=ALL $P "$@"; }
n=$(wc -l < runs/stream_meta.txt)
RL=$(sb --cpus-per-task=2 --mem=8G --time=3:00:00 --array=0-$((n-1))%6 --job-name=${E}_meta_rl tools/step.sbatch experiments/stream_meta.py --list runs/stream_meta.txt)
REP=$(sb --cpus-per-task=2 --mem=8G --time=0:30:00 --dependency=afterany:$RL --job-name=${E}_meta_report tools/step.sbatch experiments/stream_meta.py --report)
echo "$E meta rl ($n runs) $RL / report $REP"
