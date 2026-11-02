#!/bin/bash
# Ledger of sbatch submissions, so every job can be traced to its script and purpose.
#
# Submit and log in one line (sbatch stays visible, so it still gets reviewed before running):
#   jid=$(sbatch --parsable jobs/foo.sbatch) && scripts/joblog.sh add "$jid" jobs/foo.sbatch "purpose"
#
#   scripts/joblog.sh status            every logged job: state, elapsed, exit code, purpose (from sacct)
#   scripts/joblog.sh active            your pending/running jobs (from squeue)
#   scripts/joblog.sh note <jid> "txt"  record the outcome (output path, failure reason, ...)
#   scripts/joblog.sh left              time left in the current interactive allocation
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEDGER=${JOBLOG_LEDGER:-$ROOT/jobs/jobs.tsv}
SNAPDIR=$(dirname "$LEDGER")/submitted

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

cmd=${1:-}
case $cmd in
add)
    [ $# -eq 4 ] || usage
    jid=$2 script=$3 purpose=$4
    mkdir -p "$SNAPDIR"
    [ -f "$LEDGER" ] || printf 'submitted\tjob_id\tscript\tpurpose\tnotes\n' > "$LEDGER"
    # Keep a copy of the exact script that ran; the original may be edited later.
    cp "$script" "$SNAPDIR/$jid.sbatch"
    printf '%s\t%s\t%s\t%s\t\n' "$(date '+%F %T')" "$jid" "$script" "$purpose" >> "$LEDGER"
    echo "logged $jid"
    ;;
status)
    [ -f "$LEDGER" ] || { echo "no jobs logged yet ($LEDGER)"; exit 0; }
    ids=$(awk -F'\t' 'NR>1 {print $2}' "$LEDGER" | paste -sd,)
    [ -n "$ids" ] || { echo "no jobs logged yet"; exit 0; }
    # -X: one line per job (array tasks are listed as <jid>_<task>); joined back to the ledger by base id.
    sacct -X -n -P -j "$ids" -o JobID,JobName,State,Elapsed,ExitCode \
        | awk 'NR==FNR { if (FNR > 1) { p[$2] = $4; n[$2] = $5 }; next }
               { base = $1; sub(/_.*/, "", base); print $1, $2, $3, $4, $5, p[base], n[base] }' \
              FS='\t' "$LEDGER" FS='|' OFS='\t' - \
        | (printf 'JOBID\tNAME\tSTATE\tELAPSED\tEXIT\tPURPOSE\tNOTES\n'; cat) | column -t -s $'\t'
    ;;
active)
    squeue --me -o '%.18i %.24j %.10T %.10M %.10L %.6D %R'
    ;;
note)
    [ $# -eq 3 ] || usage
    jid=$2 text=$3
    tmp=$LEDGER.tmp
    awk -F'\t' -v OFS='\t' -v j="$jid" -v t="$text" \
        'NR > 1 && $2 == j { $5 = ($5 == "" ? t : $5 "; " t); found = 1 } { print }
         END { if (!found) { print "no such job: " j > "/dev/stderr"; exit 1 } }' "$LEDGER" > "$tmp" \
        || { rm -f "$tmp"; exit 1; }
    mv "$tmp" "$LEDGER"
    ;;
left)
    [ -n "${SLURM_JOB_ID:-}" ] || { echo "not inside a SLURM allocation"; exit 1; }
    squeue -h -j "$SLURM_JOB_ID" -o '%L'
    ;;
*)
    usage
    ;;
esac
