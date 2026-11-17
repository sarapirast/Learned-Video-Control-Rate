#!/bin/bash
# go.sh <cli|shim> <final4|r3> [extra run.py args]   (Aayush's job env settings, outputs under my scratch only)
set -e
source /etc/profile >/dev/null 2>&1
module purge >/dev/null 2>&1
module load ver/2506 gcc/14.3.0 x264/20250608 ffmpeg/7.1.1 >/dev/null 2>&1
export PATH=$(dirname "$(command -v x264)"):$PATH
D=$(cd "$(dirname "$0")" && pwd)
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export RC_CODEC=x264 RC_ARM=res RC_METRIC=dpsnr RC_RES_RANGE=6 RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3
export RC_WORK=/scratch1/aayushso/rcwork_v1/x264_resh RC_WORKERS=1
export RC_REPORTS=/scratch1/ahhanagu/tmp/rc_reports RC_TMP=/dev/shm/rc_ahhanagu_${SLURM_JOB_ID:-none}
export TMPDIR=/scratch1/ahhanagu/tmp
export RC_BACKEND=$1
if [ "$2" = r3 ]; then export RC_RES_RECAP=bit; else export RC_RES_RECAP=0; fi
mkdir -p "$RC_TMP" "$RC_REPORTS"
/scratch1/aayushso/envs/rc/bin/python -I "$D/run.py" --method "$2" --out "$D/rows_$2_$1.pkl" "${@:3}"
