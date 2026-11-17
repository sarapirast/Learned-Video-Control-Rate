# Sourced by every r3_kcurve step: modules, Aayush's rc Python env, rclib from p1-fast-backend with the shim backend.
# All writes go to /scratch1/ahhanagu/ee599/results/r3_kcurve (RC_WORK links Aayush's x264_resh inputs read-only).
_opts=$-; set +eu                 # /etc/profile and Lmod are not safe under set -eu (lang.sh: LC_ALL unbound)
source /etc/profile >/dev/null 2>&1
module purge >/dev/null 2>&1
module load ver/2506 gcc/14.3.0 x264/20250608 ffmpeg/7.1.1 >/dev/null 2>&1
[[ $_opts == *e* ]] && set -e; [[ $_opts == *u* ]] && set -u
command -v x264 >/dev/null || { echo "env.sh: module x264 not loaded" >&2; return 1; }
B=/scratch1/ahhanagu/ee599/results/r3_kcurve
REPO=/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate
PY=/scratch1/aayushso/envs/rc/bin/python
export PYTHONPATH=$REPO                       # x264env for the shim backend
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export RC_CODEC=x264 RC_ARM=res RC_METRIC=dpsnr RC_RES_RANGE=6 RC_RES_RECAP=bit RC_BACKEND=shim
export RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3
export RC_WORK=$B/work RC_REPORTS=$B/work/reports RC_SHIFTS=$B/exp5/shifts_smooth.json
export RC_ENVS=${RC_ENVS:-14} RC_WORKERS=${RC_WORKERS:-$(( ${SLURM_CPUS_PER_TASK:-4} - 2 ))}
export RC_TMP=/dev/shm/rc_ahhanagu_${SLURM_JOB_ID:-none} TMPDIR=/scratch1/ahhanagu/tmp
mkdir -p "$RC_TMP" "$TMPDIR"
