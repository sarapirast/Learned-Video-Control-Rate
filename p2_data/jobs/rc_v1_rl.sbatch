#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1
#SBATCH --output=/scratch1/aayushso/rcwork_v1/logs/%x-%A_%a.out
#SBATCH --requeue --open-mode=append
# Array of RL runs on data v1: line $SLURM_ARRAY_TASK_ID+1 of the run list holds experiments/rl.py's arguments.
# Node excludes come from jobs/bad_nodes.txt via jobs/rc_v1_submit.sh (dated, they expire).
# 4 h cap: Pavneet's runs took 12-57 min; one hung for 6.9 h, so the cap keeps a hang from burning the slot.
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
cd /scratch1/aayushso/ee599/repo-pavneet || { retry_elsewhere "cd failed"; exit 75; }
source tools/job_env_v1.sh || exit 1
ARGS=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$1")
L=$RC_WORK/logs/${SLURM_JOB_NAME}.log
mkdir -p "$RC_WORK/logs"
echo "$(date +%F\ %T) START $SLURM_ARRAY_JOB_ID[$SLURM_ARRAY_TASK_ID] $(hostname): $RC_CODEC/$RC_ARM rl.py $ARGS" >> "$L"
unset SLURM_ARRAY_TASK_ID   # rl.py runs are not shards
python -W ignore experiments/rl.py $ARGS 2>&1 | grep --line-buffered -v -i -E 'warning|batch_size|n_steps='
rc=${PIPESTATUS[0]}
echo "$(date +%F\ %T) END   $SLURM_ARRAY_JOB_ID rc=$rc: $ARGS" >> "$L"
if (( rc != 0 )) && { (( rc == 135 || rc == 75 )) || ! scratch_ok end; }; then retry_elsewhere "rc $rc"; fi
exit $rc
