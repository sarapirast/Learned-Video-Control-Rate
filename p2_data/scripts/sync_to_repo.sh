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
