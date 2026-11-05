# Sourced by every job script: clean module env, the project's conda prefix, temp dirs. Never sources ~/.bashrc (D3).
module purge
module load gcc/13.3.0   # x265 (C++) was built with it and needs its libstdc++ (GLIBCXX_3.4.32)
export PATH=/scratch1/pbanga/envs/codecs/bin:/scratch1/pbanga/envs/rc/bin:$PATH
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export RC_CODEC=${RC_CODEC:-x265}
export RC_WORK=${RC_WORK:-/scratch1/pbanga/rcwork}
export RC_WORKERS=${RC_WORKERS:-$(( ${SLURM_CPUS_PER_TASK:-4} - 2 ))}
export RC_ENVS=${RC_ENVS:-14}
# encoder temp output: node-local RAM disk inside jobs (counts against job memory; files are tiny and removed)
export RC_TMP=${SLURM_JOB_ID:+/dev/shm/rc_$SLURM_JOB_ID}
export RC_TMP=${RC_TMP:-/scratch1/pbanga/tmp}
export TMPDIR=/scratch1/pbanga/tmp
mkdir -p "$RC_TMP" "$TMPDIR" "$RC_WORK"
trap 'rm -rf /dev/shm/rc_${SLURM_JOB_ID:-none}' EXIT
