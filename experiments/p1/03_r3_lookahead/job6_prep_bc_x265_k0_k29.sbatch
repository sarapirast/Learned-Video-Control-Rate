#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G
#SBATCH --time=1:30:00
#SBATCH --job-name=r3k_x265_prep
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%j.out
# Job 6 of 03_r3_lookahead (x265): BC data and mean shift at k29 (with the k5 reproduction checks), then the BC networks
# for R3 at k29 and k0, seeds 3-5, ONE AFTER THE OTHER (two bc_train.py at once oversubscribe the cores ~20x).
# Same chain as x264 k29 (job 1 + job 2), with P1_ENC=x265. No encodes, ~30 min.
# Run: bash submit_x265.sh (job 6 -> R3 array), or P1_ENC=x265 sbatch --export=ALL,P1_ENC=x265 job6_prep_bc_x265_k0_k29.sbatch
# Inputs (read-only): Aayush's x265 search plans / infos / fold, his shifts_smooth.json and x265 k0/k5 BC data.
# Outputs: $B/exp5_x265/ (data_x265_k{5,29}.npz, data_v2_x265_k{5,29}.npz, plans*.pkl, shifts_smooth.json with x265|29,
# bc/bc_x265_k{29,0}_s{3,4,5}.pt), $B/work_x265/ (links to Aayush's x265_resh inputs), logs in $B/logs.
#   1. bc_data_build.py v1 at k5,29 -> k5 smooth shift must equal Aayush's x265|5 (else stop)
#   2. k29 shift -> exp5_x265/shifts_smooth.json = Aayush's file + x265|29
#   3. bc_data_build.py --v2 at k5,29 -> k5 v2 data must equal Aayush's data_v2_x265_k5.npz as a set of rows (else stop)
#   4. bc_train.py: k29 seeds 3,4,5 (new data), then k0 seeds 3,4,5 (Aayush's data); networks that exist are skipped
set -euo pipefail
export P1_ENC=x265
source /scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead/env.sh
E=$B/exp5_x265; W=$(( SLURM_CPUS_PER_TASK - 1 ))
BC=$REPO/p2_data/exp_next/exp5/bc_train.py
A=/scratch1/aayushso/rcwork_v1/x265_resh
mkdir -p "$E/bc" "$RC_WORK/results_rl" "$RC_WORK/logs"
# read-only inputs as links. A real file/dir in their place means something created it (rclib's data.gop_path() makes
# gops/ and extracts GOPs into it if the link is missing), so stop instead of silently re-extracting.
for x in clips gops manifest.json results_infos; do
  if [[ -L $RC_WORK/$x ]]; then continue
  elif [[ -e $RC_WORK/$x ]]; then echo "job6: $RC_WORK/$x exists but is not a link to $A/$x; remove it first" >&2; exit 1
  else ln -s "$A/$x" "$RC_WORK/$x"; fi
done
cd "$S"
if [[ ! -f $E/shifts_smooth.json ]]; then
  echo "$(date +%T) step 1: v1 data k5,29 (x265)"
  EXP5_KS=5,29 $PY -W ignore bc_data_build.py --workers $W --out "$E" | tail -2
  EXP5_KS=5 $PY -I bc_shift_fit.py "$E" --check
  echo "$(date +%T) step 2: k29 shift"
  EXP5_KS=29 $PY -I bc_shift_fit.py "$E"          # base = Aayush's current shifts file (has x265|0/2/5)
fi
if [[ ! -f $E/data_v2_x265_k29.npz ]]; then
  echo "$(date +%T) step 3: v2 data k5,29"
  RC_SHIFTS=$E/shifts_smooth.json EXP5_KS=5,29 $PY -W ignore bc_data_build.py --v2 --workers $W --out "$E" | tail -2
  $PY -I bc_data_compare.py "$E" v2 5
fi
train() {   # train <k> <data dir>: missing seeds of 3,4,5 in one process (data loaded once, 16 threads)
  local todo=()
  for s in 3 4 5; do [[ -f $E/bc/bc_x265_k$1_s$s.pt ]] && echo "k$1 s$s: exists, skipped" || todo+=($s); done
  (( ${#todo[@]} )) || return 0
  local seeds; seeds=$(IFS=,; echo "${todo[*]}")
  echo "$(date +%T) step 4: BC x265 k$1 seeds $seeds"
  $PY -W ignore "$BC" --ks "$1" --seeds "$seeds" --data "$2" --out "$E/bc" --tag "k$1_s${seeds//,/}" \
      > "$B/logs/bc_x265_k$1-$SLURM_JOB_ID.log" 2>&1
  grep -E '^\| [0-9]+ \| [0-9]' "$B/logs/bc_x265_k$1-$SLURM_JOB_ID.log" || true
}
train 29 "$E"
train 0 /scratch1/aayushso/ee599/results_v1/next/exp5
for k in 29 0; do for s in 3 4 5; do test -f "$E/bc/bc_x265_k${k}_s$s.pt"; done; done
rm -rf "$RC_TMP"
echo "$(date +%T) x265 prep done"
