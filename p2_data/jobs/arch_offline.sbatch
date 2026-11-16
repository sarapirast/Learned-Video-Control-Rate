#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=4:00:00
#SBATCH --array=0-1
#SBATCH --job-name=arch_offline
#SBATCH --output=/scratch1/aayushso/ee599/logs/arch_offline_%A_%a.out
# Day-1 offline architecture test (tracker item 36): BC imitation of held-out search plans, flat MLP vs shared
# per-frame encoder (repo-pavneet tools/arch_offline.py). No encodes. Task 0 = x264, task 1 = x265.
# Args: extra arguments for arch_offline.py (default: all k, all three nets, seeds 0,1, 20000 steps, tag d1).
set -euo pipefail
CODECS=(x264 x265)
export RC_CODEC=${CODECS[$SLURM_ARRAY_TASK_ID]} RC_ARM=lfq RC_ACT_RANGE=10 RC_METRIC=dpsnr
export RC_WORK=/scratch1/aayushso/rcwork_v1/${RC_CODEC}_lfqp
cd /scratch1/aayushso/ee599/repo-pavneet
source tools/job_env_v1.sh
python -I tools/arch_offline.py --seeds 0,1 --steps 20000 --tag d1 "$@"
