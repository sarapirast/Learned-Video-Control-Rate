#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main,oneweek
#SBATCH --nodes=1 --ntasks=1
#SBATCH --output=/scratch1/aayushso/ee599/logs/%x-%A_%a.out
#SBATCH --requeue --open-mode=append
# One P2 Python step on data v1 with the encoder stack (x264 module, x265 4.1, ffmpeg) and the ee599 env.
# Args: the script path and its arguments, e.g. scripts/controller_real.py --encoder x264 --nshards 8 (shard = array task id).
# Node excludes come from jobs/bad_nodes.txt at submit time.
set -uo pipefail
# ---- node-trouble auto-retry (same block in rc_v1_step.sbatch and rc_v1_rl.sbatch; kept inline because it must work
# when /scratch1 is broken). On SIGBUS (135), a failed scratch check (75), or any failure while scratch is unreadable:
# submit a tiny helper job to debug, requeue+hold this job (same job ID, so dependencies stay valid); the helper adds
# this node to the job's ExcNodeList and to jobs/bad_nodes.txt, then releases it. At most 2 retries per job.
# RC_RETRY_TEST=1 skips the bad_nodes.txt entry (for testing the mechanism).
scratch_ok() {
  local P=/scratch1/aayushso/rcwork_v1/logs/.probe_${SLURM_JOB_ID}_$1
  timeout 60 sh -c 'echo ok > "$1" && grep -q ok "$1"' _ "$P" || return 1
  rm -f -- "$P"
}
retry_elsewhere() {   # $1 = reason
  local id=$SLURM_JOB_ID h n=${SLURM_RESTART_COUNT:-0} helper
  h=$(hostname -s)
  if (( n >= 2 )); then echo "node trouble on $h ($1): already retried $n times, giving up" >&2; return 1; fi
  helper="for i in \$(seq 60); do [ \"\$(squeue -h -j $id -o %T)\" = PENDING ] && break; sleep 5; done
X=\$(scontrol show job $id -o | grep -o 'ExcNodeList=[^ ]*' | cut -d= -f2); [ \"\$X\" = '(null)' ] && X=
scontrol update JobId=$id ExcNodeList=\${X:+\$X,}$h
scontrol release $id"
  [[ -z ${RC_RETRY_TEST:-} ]] && helper="timeout 60 /scratch1/aayushso/ee599/scripts/bad_nodes.sh add $h 'auto-retry: $1 (job $id)'
$helper"
  sbatch --account=rashidin_1753 --partition=debug --time=0:10:00 --cpus-per-task=1 --mem=1G --export=NONE \
    --job-name=retry_$id --output=/dev/null --wrap "$helper" >&2 || { echo "retry helper submit failed" >&2; return 1; }
  echo "$(date +%T) node trouble on $h ($1): requeue+hold, attempt $((n + 1)), helper will exclude $h" >&2
  scontrol requeuehold "$id" && sleep 120   # slurm ends this run here
}
scratch_ok start || { retry_elsewhere "scratch check failed at start"; exit 75; }
# ---- end auto-retry block
module purge
module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1 x264/20250608
export PATH=$(dirname "$(command -v x264)"):/scratch1/aayushso/envs/codecs/bin:/scratch1/aayushso/envs/ee599/bin:$PATH
x264 --version 2>&1 | grep -q '0.165.' || { echo "wrong x264 on $(hostname): $(command -v x264)"; exit 1; }
x265 --version 2>&1 | grep -q 'version 4.1' || { echo "wrong x265 on $(hostname): $(command -v x265)"; exit 1; }
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 TMPDIR=/scratch1/aayushso/tmp
export RC_TMP=/dev/shm/p2_$SLURM_JOB_ID
mkdir -p "$RC_TMP" "$TMPDIR"
trap 'rm -rf /dev/shm/p2_${SLURM_JOB_ID:-none}' EXIT
cd /scratch1/aayushso/ee599 || { retry_elsewhere "cd failed"; exit 75; }
echo "$(date +%F\ %T) START job $SLURM_JOB_ID task ${SLURM_ARRAY_TASK_ID:-} on $(hostname): $*"
python "$@"
rc=$?
echo "$(date +%F\ %T) END rc=$rc"
if (( rc != 0 )) && { (( rc == 135 || rc == 75 )) || ! scratch_ok end; }; then retry_elsewhere "rc $rc"; fi
exit $rc
