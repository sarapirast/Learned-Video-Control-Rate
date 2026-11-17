#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=48G
#SBATCH --time=1:00:00
#SBATCH --array=0-2
#SBATCH --job-name=r3k_rl
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%A_%a.out
# Stage 1: R3 (x264, seed 3, 180k PPO steps) at k = 5 / 0 / 29 = line SLURM_ARRAY_TASK_ID+1 of runs.txt.
# Recipe = the stored R3 run (rl.py --method res, lam 0.17, f4, drop level, res-mean pooled, BC actor, 20k critic-only
# warm-up), 14 envs on 16 cores as the team's RL jobs, rclib on the shim backend. Checkpoints at 20k (= the BC start:
# the actor is frozen during the warm-up), 60k, 120k; final model at 180k. All are evaluated on val (560 episodes).
# rl.py cannot resume: a failed task is rerun from the start (a finished one is skipped: eval.pkl exists).
set -uo pipefail
source /scratch1/ahhanagu/ee599/results/r3_kcurve/scripts/env.sh
# optional: $1 = run list (default runs.txt), $2 = shifts json for --res-mean (default env.sh's RC_SHIFTS)
RUNS=${1:-$B/scripts/runs.txt}
[[ -n ${2:-} ]] && export RC_SHIFTS=$2
ARGS=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$RUNS")
[[ -n $ARGS ]] || { echo "no line $((SLURM_ARRAY_TASK_ID + 1)) in $RUNS"; exit 2; }
echo "runs $RUNS, RC_SHIFTS $RC_SHIFTS"
echo "$(date +%F\ %T) START $SLURM_ARRAY_JOB_ID[$SLURM_ARRAY_TASK_ID] $(hostname) RC_ENVS=$RC_ENVS RC_WORKERS=$RC_WORKERS: $ARGS"
unset SLURM_ARRAY_TASK_ID   # rl.py runs are not shards
cd "$REPO/pavneet_pipeline"
$PY -W ignore experiments/rl.py $ARGS 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='
rc=${PIPESTATUS[0]}
rm -rf "$RC_TMP"
echo "$(date +%F\ %T) END rc=$rc"
exit $rc
