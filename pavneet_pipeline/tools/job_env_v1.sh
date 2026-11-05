# Data-v1 variant of tools/job_env.sh (Aayush's paths; local branch v1-data). Sourced by every v1 job script.
#   RC_CODEC  x265 | x264      RC_ARM  orig | dec  (budget arm; see tools/budget_arm.py)
module purge
module load ver/2506 gcc/14.3.0 x264/20250608   # x264 0.165.3222; gcc 14 libstdc++ also serves the x265 build
X264_BIN=$(dirname "$(command -v x264)")      # the module's x264, captured before the conda env goes on PATH
# conda-forge ffmpeg puts its own x264 0.164 / x265 3.5 in envs/rc/bin: the module x264 and the 4.1 build must win
export PATH=$X264_BIN:${RC_X265_BIN:-/scratch1/aayushso/envs/codecs/bin}:/scratch1/aayushso/envs/rc/bin:$PATH
case ${RC_CODEC:-x265} in
  x264) x264 --version 2>&1 | grep -q '0.165.' || { echo "wrong x264 on $(hostname): $(command -v x264): $(x264 --version 2>&1 | head -2)"; return 1 2>/dev/null || exit 1; } ;;
  x265) x265 --version 2>&1 | grep -q 'version 4.1' || { echo "wrong x265 on $(hostname): $(command -v x265): $(x265 --version 2>&1 | head -2)"; return 1 2>/dev/null || exit 1; } ;;
esac
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export RC_CODEC=${RC_CODEC:-x265}
export RC_ARM=${RC_ARM:-orig}
export RC_REPORTS=${RC_REPORTS:-/scratch1/aayushso/ee599/results_v1/${RC_CODEC}_${RC_ARM}}   # never his results/
export RC_WORK=${RC_WORK:-/scratch1/aayushso/rcwork_v1/${RC_CODEC}_${RC_ARM}}
export RC_WORKERS=${RC_WORKERS:-$(( ${SLURM_CPUS_PER_TASK:-4} - 2 ))}
export RC_ENVS=${RC_ENVS:-14}
export RC_TMP=${SLURM_JOB_ID:+/dev/shm/rc_$SLURM_JOB_ID}
export RC_TMP=${RC_TMP:-/scratch1/aayushso/tmp/rc}
export TMPDIR=/scratch1/aayushso/tmp
mkdir -p "$RC_TMP" "$TMPDIR" "$RC_WORK" "$RC_REPORTS"
trap 'rm -rf /dev/shm/rc_${SLURM_JOB_ID:-none}' EXIT
