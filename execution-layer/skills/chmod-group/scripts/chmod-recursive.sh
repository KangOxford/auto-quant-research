#!/bin/bash
# chmod-recursive.sh - Recursively modify directory permissions to make them group-readable

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <directory>"
    echo "Function: Recursively add group read permissions to a directory"
    echo "  - Directories: g+rx (readable and executable)"
    echo "  - Files: g+r,g-x (readable, not executable)"
    exit 1
fi

DIR="$1"

if [ ! -d "$DIR" ]; then
    echo "Error: '$DIR' is not a valid directory"
    exit 1
fi

echo "Starting permission modification: $DIR"
echo "Mode: recursive (directories g+rx, files g+r,g-x)"
echo ""

# Directories: add rx permission
echo "Step 1/2: Modifying directory permissions (g+rx)..."
find "$DIR" -type d -exec chmod g+rx {} +

# Files: add r permission, remove x
echo "Step 2/2: Modifying file permissions (g+r,g-x)..."
find "$DIR" -type f -exec chmod g+r,g-x {} +

echo ""
echo "✅ Permission modification complete!"
echo ""
echo "Verification:"
stat -c "%a %A %n" "$DIR" | head -1

echo ""
echo "Checking subdirectory/file permissions:"
find "$DIR" -maxdepth 2 | head -5 | xargs stat -c "%a %A %n" 2>/dev/null || true

echo ""
echo "Summary:"
DIR_COUNT=$(find "$DIR" -type d | wc -l)
FILE_COUNT=$(find "$DIR" -type f | wc -l)
echo "  - Directories: $DIR_COUNT"
echo "  - Files: $FILE_COUNT"
