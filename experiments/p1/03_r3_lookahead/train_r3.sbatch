#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=48G
#SBATCH --time=1:00:00
#SBATCH --array=0-2
#SBATCH --job-name=r3k_rl
#SBATCH --output=/scratch1/ahhanagu/ee599/results/r3_kcurve/logs/%x-%A_%a.out
# train_r3.sbatch: one rl.py run per array task (task i = line i+1 of the run list). Used for R3 (03) and R2c (04).
# Run: sbatch [--array=0-<n-1>] train_r3.sbatch [<run list>] [<shifts json>]; normally via a submit_*.sh.
#   run list default: runs_batch1_k5_k0_k29_seed3.txt (3 lines -> the header's --array=0-2)
#   shifts json default: env.sh's RC_SHIFTS ($B/exp5/shifts_smooth.json: k0, k5, k29)
# Inputs: BC networks named in the run list (--init-bc), Aayush's x264_resh infos/GOPs via $B/work.
# Outputs: $B/work/results_rl/<run name>/ (model.zip, model_<step>.zip, eval.pkl, eval_ckpt.pkl, train_curve.npy).
# Recipe = the stored R3 run (rl.py --method res, lam 0.17, f4, drop level, res-mean pooled, BC actor, 20k critic-only
# warm-up), 14 envs on 16 cores as the team's RL jobs, rclib on the shim backend. Checkpoints at 20k (= the BC start:
# the actor is frozen during the warm-up), 60k, 120k; final model at 180k. All are evaluated on val (560 episodes).
# rl.py cannot resume: a failed task is rerun from the start (a finished one is skipped: eval.pkl exists).
set -uo pipefail
source /scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1/03_r3_lookahead/env.sh
# optional: $1 = run list (default runs_batch1_k5_k0_k29_seed3.txt), $2 = shifts json for --res-mean (default env.sh's RC_SHIFTS)
RUNS=${1:-$S/runs_batch1_k5_k0_k29_seed3.txt}
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
