#!/bin/bash
# Copy the P2 files that belong in git from this workspace into the team repo, under p2_data/.
# The workspace stays the working copy; run this, review `git -C repo status`, then commit.
# Never copies data/, logs/, the job ledger or personal files (CLAUDE.md, PDFs, drafts).
#
#   scripts/sync_to_repo.sh            # sync into ./repo/p2_data
#   scripts/sync_to_repo.sh -n         # dry run: list what would change
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST=$ROOT/repo/p2_data
DRY=${1:-}

FILES=(
    scripts/*.py scripts/*.sh
    config/*.csv
    jobs/*.sbatch
    docs/clip-selection.md docs/p2-plan.md docs/p2-tracker.md docs/data-v1-README.md docs/feature-spec-draft.md
    docs/EXPERIMENTS.md docs/budget-estimator-v1.md docs/rd-native-summary.md docs/fp-stats-gate.md
    docs/lit-survey-features-2026-11-04.md docs/rl-models-review-2026-11-04.md docs/rl-field-guide.html
    docs/w4-hypotheses.md docs/report-w5-quality-vs-delay.md docs/final-writeup-2026-11-16.md docs/team-update-2026-11-16.txt docs/team-summary-aayush-2026-11-18.txt
    jobs/*.sh runs_v1/*.txt
    environment.yml environment.lock.txt
    p2_data_README.md:README.md
    p2_data_gitignore:.gitignore
)

cd "$ROOT"
for spec in "${FILES[@]}"; do
    src=${spec%%:*}
    dst=${spec#*:}
    [ "$dst" = "$spec" ] && dst=$src
    [ -f "$src" ] || { echo "missing: $src" >&2; exit 1; }
    if ! cmp -s "$src" "$DEST/$dst" 2>/dev/null; then
        echo "update $dst"
        if [ "$DRY" != "-n" ]; then
            mkdir -p "$(dirname "$DEST/$dst")"
            cp "$src" "$DEST/$dst"
        fi
    fi
done

# exp_next/ (next-experiments round, 11-13 on): code, pre-registrations, reports and small check logs only.
# Excludes the copies of teammates' code (src_*: already in the team repo), smoke-run models and caches.
RS=(rsync -a --prune-empty-dirs --exclude='src_pavneet/' --exclude='src_sara/' --exclude='smoke_resh_x264/'
    --exclude='__pycache__/' --include='*/' --include='*.py' --include='*.md' --include='*.json' --include='*.txt'
    --include='*.log' --include='*.patch' --include='*.sh' --exclude='*')
if [ "$DRY" = "-n" ]; then
    "${RS[@]}" -n -i "$ROOT/exp_next/" "$DEST/exp_next/" | grep -v '^\.d' | sed 's/^/exp_next: /' || true
else
    "${RS[@]}" "$ROOT/exp_next/" "$DEST/exp_next/"
fi

# report_pack/ (final-report results pack, 11-18): write-up, figures, tables, copied source reports, figure script.
RP=(rsync -a --exclude='__pycache__/')
if [ "$DRY" = "-n" ]; then
    "${RP[@]}" -n -i "$ROOT/report_pack/" "$DEST/report_pack/" | grep -v '^\.d' | sed 's/^/report_pack: /' || true
else
    "${RP[@]}" "$ROOT/report_pack/" "$DEST/report_pack/"
fi
