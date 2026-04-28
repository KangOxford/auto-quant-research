#!/usr/bin/env bash
# pull-aramis-thesis.sh
# Triggered by post-merge hook in main quant overleaf repo.
# Only runs when git pull actually brings new commits, not on every session.
#
# Flow:
#   1. Pull aramis thesis upstream (4yp-thesis Overleaf)
#   2. Rsync upstream → drafts/aramis/ (file mirror, no .git)
#   3. Commit + push to main Overleaf if files changed
#
# Runs in background subshell; does not block the triggering git pull.

set +e
LOG="${HOME}/.claude/hooks/aramis-pull.log"
MAIN="/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/LOBS5/overleaf/69b804b1b5022d27002331fa"
UPSTREAM="/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/LOBS5/overleaf/_aramis_thesis_upstream"

(
  exec >> "$LOG" 2>&1
  echo "=== $(date -Iseconds) trigger=post-merge ==="

  # Step 1: Pull aramis thesis upstream
  if [ -d "$UPSTREAM/.git" ]; then
    cd "$UPSTREAM" || { echo "FAIL: cd $UPSTREAM"; exit 0; }
    if ! timeout 30 git pull --ff-only --quiet; then
      echo "WARN: aramis upstream pull failed; continuing with existing snapshot"
    fi
  else
    echo "SKIP: $UPSTREAM/.git not found"
    exit 0
  fi

  # Step 2: Rsync upstream → drafts/aramis/ (file mirror, no .git)
  if ! rsync -a --delete --exclude='.git/' \
       "$UPSTREAM/" \
       "$MAIN/drafts/aramis/"; then
    echo "WARN: rsync failed"
    exit 0
  fi

  # Step 3: Commit + push if changed
  cd "$MAIN" || exit 0
  if [ -n "$(git status --porcelain drafts/aramis/)" ]; then
    git add drafts/aramis/
    UPSTREAM_SHA=$(git -C "$UPSTREAM" rev-parse --short HEAD 2>/dev/null || echo unknown)
    if git commit -m "sync aramis thesis from upstream @ ${UPSTREAM_SHA}" --quiet; then
      if ! timeout 30 git push origin master --quiet; then
        echo "WARN: push failed; local commit kept"
      else
        echo "synced upstream @ ${UPSTREAM_SHA} → main overleaf"
      fi
    else
      echo "WARN: commit failed"
    fi
  else
    echo "no changes; skipping commit"
  fi

  echo "done at $(date -Iseconds)"
) &

exit 0
