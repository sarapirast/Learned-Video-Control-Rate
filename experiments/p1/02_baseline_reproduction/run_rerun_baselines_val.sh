#!/bin/bash
# run_rerun_baselines_val.sh: run rerun_baselines_val.py (x264, shim backend, Aayush's rc env).
# Run (on a compute node, ~10 min each): bash run_rerun_baselines_val.sh final4   and   ... r3
# Outputs: /scratch1/ahhanagu/ee599/results/baselines_val/rows_final4_k<k>.pkl, rows_r3_s<seed>.pkl
set -e
source /etc/profile >/dev/null 2>&1
module purge >/dev/null 2>&1
module load ver/2506 gcc/14.3.0 x264/20250608 ffmpeg/7.1.1 >/dev/null 2>&1
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export RC_CODEC=x264 RC_ARM=res RC_METRIC=dpsnr RC_RES_RANGE=6 RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3
export RC_WORK=/scratch1/aayushso/rcwork_v1/x264_resh RC_WORKERS=1 RC_BACKEND=shim
export RC_REPORTS=/scratch1/ahhanagu/tmp/rc_reports RC_TMP=/dev/shm/rc_ahhanagu_${SLURM_JOB_ID:-none}
export TMPDIR=/scratch1/ahhanagu/tmp
if [ "$1" = r3 ]; then export RC_RES_RECAP=bit; else export RC_RES_RECAP=0; fi
/scratch1/aayushso/envs/rc/bin/python -I "$(dirname "$0")/rerun_baselines_val.py" --method "$@"
