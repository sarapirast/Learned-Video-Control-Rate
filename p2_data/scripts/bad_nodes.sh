#!/bin/bash
# Dated list of flaky nodes (jobs/bad_nodes.txt), so excludes expire instead of being hard-coded in sbatch files.
#   scripts/bad_nodes.sh exclude            comma list of nodes added in the last BAD_NODE_DAYS days (default 3)
#   scripts/bad_nodes.sh add <node> <reason> append an entry dated today
#   scripts/bad_nodes.sh failed <jobid>...  nodes where these jobs/arrays ended FAILED / NODE_FAIL / scratch check (rc 75)
#   scripts/bad_nodes.sh list               all entries, marked active / expired
F=/scratch1/aayushso/ee599/jobs/bad_nodes.txt
DAYS=${BAD_NODE_DAYS:-3}
cut=$(date -d "-$DAYS days" +%F)
case ${1:-} in
  exclude) awk -F'\t' -v c="$cut" '!/^#/ && NF>=2 && $2>=c {print $1}' "$F" | sort -u | paste -sd, ;;
  add)     [[ $# -ge 3 ]] || { echo "usage: $0 add <node> <reason>"; exit 1; }
           printf '%s\t%s\t%s\n' "$2" "$(date +%F)" "${*:3}" >> "$F" ;;
  failed)  shift; [[ $# -ge 1 ]] || { echo "usage: $0 failed <jobid>..."; exit 1; }
           sacct -X -n -P -j "$(IFS=,; echo "$*")" --format=JobID,NodeList,State,ExitCode |
             awk -F'|' '$3 ~ /FAILED|NODE_FAIL/ || $4 ~ /^75:/ {print $2 "\t" $1 "\t" $3 " " $4}' ;;
  list)    awk -F'\t' -v c="$cut" '!/^#/ && NF>=2 {print ($2>=c ? "active " : "expired"), $0}' "$F" ;;
  *)       sed -n '2,6p' "$0"; exit 1 ;;
esac
