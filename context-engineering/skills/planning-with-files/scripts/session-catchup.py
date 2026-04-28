#!/usr/bin/env python3
"""
session-catchup.py — planning-with-files skill helper
Checks for unsynced context from a previous session by comparing
task_plan.md modification time with git log.
Always exits 0 (non-blocking).
"""

import sys
import os
import subprocess
from pathlib import Path


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    plan_file = Path(project_dir) / "task_plan.md"

    if not plan_file.exists():
        # No plan file — fresh session
        sys.exit(0)

    # Get last git commit time
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=project_dir, capture_output=True, text=True, timeout=5
        )
        last_commit_ts = int(result.stdout.strip()) if result.stdout.strip() else 0
    except Exception:
        last_commit_ts = 0

    plan_mtime = int(plan_file.stat().st_mtime)

    # Read current phase from plan
    current_phase = "unknown"
    incomplete = 0
    try:
        content = plan_file.read_text()
        for line in content.splitlines():
            if "## Current Phase" in line:
                pass
            elif current_phase == "unknown" and line.strip() and not line.startswith("#"):
                current_phase = line.strip()
                break
            if "- [ ]" in line:
                incomplete += 1
    except Exception:
        pass

    # Check if plan was modified after last commit (unsaved progress)
    if plan_mtime > last_commit_ts + 60:
        print(f"[planning-with-files] ⚠️  Unsynced session context detected!")
        print(f"  task_plan.md modified after last git commit.")
        print(f"  Incomplete items: {incomplete}")
        print(f"  Review task_plan.md to restore session state.")
    else:
        print(f"[planning-with-files] Session context in sync.")
        print(f"  Incomplete items: {incomplete}")

    sys.exit(0)


if __name__ == "__main__":
    main()
