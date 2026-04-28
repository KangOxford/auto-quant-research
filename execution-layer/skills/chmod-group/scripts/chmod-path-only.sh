#!/bin/bash
# chmod-path-only.sh - Add traversal permission to specified directories (execute only)

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 <dir1> [dir2] [dir3] ..."
    echo "Function: Add group execute permission (traversal access) to specified directories"
    echo "  - Only modifies the specified directories"
    echo "  - Does not modify subdirectories or files"
    echo "  - Group users can cd through but cannot ls to list contents"
    echo ""
    echo "Examples:"
    echo "  $0 ~/AlphaTrade ~/AlphaTrade/LOBS5"
    exit 1
fi

echo "Starting permission modification (path-only mode)"
echo "Action: adding g+x (traversal permission, listing not allowed)"
echo ""

SUCCESS=0
FAILED=0

for DIR in "$@"; do
    if [ ! -d "$DIR" ]; then
        echo "⚠️  Skipping: '$DIR' (not a directory)"
        ((FAILED++))
        continue
    fi

    BEFORE=$(stat -c "%a %A" "$DIR")
    chmod g+x "$DIR"
    AFTER=$(stat -c "%a %A" "$DIR")

    echo "✅ $DIR"
    echo "   Before: $BEFORE"
    echo "   After:  $AFTER"
    echo ""
    ((SUCCESS++))
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Done! Succeeded: $SUCCESS, Failed: $FAILED"

if [ $SUCCESS -gt 0 ]; then
    echo ""
    echo "Verification: Group users can now cd through these directories"
    echo "Note: Group users cannot ls to list directory contents (only x, no r)"
fi
