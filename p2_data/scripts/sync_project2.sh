#!/bin/bash
# Copy P2 data and a private backup from /scratch1 (working copy, no backups, can be purged) to /project2
# (VAST, 2 weeks of snapshots, more reliable for teammates). Re-run after big runs; only changed files are copied.
#
#   scripts/sync_project2.sh shared     data v1 -> /project2/rashidin_1753/aayushso/ee599_data (group read-only)
#   scripts/sync_project2.sh backup     everything else -> /project2/rashidin_1753/aayushso/ee599_backup (owner only)
#   scripts/sync_project2.sh all        both
#   add -n as 2nd arg for a dry run
#
# rsync -rlt on purpose: no -a / -p / -g / -o, so files take the setgid group of /project2/rashidin_1753 and the
# modes set by --chmod (CARC: cp -a / -p into /project2 charges the wrong group's quota).
# Scratch stays the working copy; nothing is deleted on either side (no --delete).
set -euo pipefail
P=/project2/rashidin_1753
S=/scratch1/aayushso
SH=$P/aayushso/ee599_data
BK=$P/aayushso/ee599_backup
what=${1:-all}
dry=${2:-}

shared() {
  mkdir -p "$SH/v1"; chmod 2710 "$P/aayushso"
  chmod 2750 "$SH" "$SH/v1"
  rsync -rlt $dry --info=stats1 --chmod=D2750,F640 \
    --exclude 'smoke*/' --exclude '*.tmp' \
    "$S/ee599/data/v1/" "$SH/v1/"
  if [[ -z $dry ]]; then
    cp "$S/ee599/docs/data-v1-README.md" "$SH/README-data-v1.md"
    chmod 640 "$SH/README-data-v1.md"
  fi
}

backup() {
  mkdir -p "$BK"
  chmod 2710 "$P/aayushso"   # group may pass through but not list (no ACLs on VAST)
  chmod 700 "$BK"
  rsync -rlt $dry --info=stats1 --chmod=go= \
    --exclude 'data/v1/' --exclude 'tmp/' --exclude '__pycache__/' --exclude 'smoke*/' \
    "$S/ee599/" "$BK/ee599/"
  rsync -rlt $dry --info=stats1 --chmod=go= --exclude '__pycache__/' "$S/rcwork_v1/" "$BK/rcwork_v1/"
}

case $what in
  shared) shared ;;
  backup) backup ;;
  all) shared; backup ;;
  *) echo "usage: $0 shared|backup|all [-n]" >&2; exit 2 ;;
esac
echo "$(date +%F\ %T) sync_project2 $what ${dry:-} done"
