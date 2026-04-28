#!/usr/bin/env python3
"""
PostToolUse hook: append every sbatch submission as a row in the Google Sheets 'alljobs' tab.

Reads hook input JSON from stdin. Exits silently if not an sbatch call.
Reuses /projects/s5e/quant/.google-sa-key.json for auth.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

SA_KEY = "/projects/s5e/quant/.google-sa-key.json"
SHEET_ID = "1LmXyNFWLTMlPReA_tReR_DVoqZAk9iG3GfLIECgjz08"
TAB = "alljobs"
LOG_ERR = "/tmp/log-sbatch-hook.err"


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        return 0

    if data.get("tool_name") != "Bash":
        return 0

    tool_input = data.get("tool_input", {}) or {}
    command = tool_input.get("command", "") or ""
    if "sbatch" not in command.lower():
        return 0

    tool_response = data.get("tool_response", {}) or {}
    if isinstance(tool_response, dict):
        out = (tool_response.get("stdout") or "") + "\n" + (tool_response.get("output") or "")
    else:
        out = str(tool_response)

    m = re.search(r"Submitted batch job (\d+)", out)
    if not m:
        return 0
    jobid = m.group(1)

    def grep(pat, default=""):
        mm = re.search(pat, command)
        return mm.group(1) if mm else default

    job_name = grep(r"--job-name[= ]+[\"']?([^\"' ]+)")
    nodes = grep(r"--nodes[= ]+(\d+)")
    time_lim = grep(r"--time[= ]+[\"']?([0-9:]+)")

    script = ""
    for tok in reversed(command.split()):
        if tok.endswith((".batch", ".sh", ".sbatch")):
            script = tok
            break

    user = os.environ.get("USER", "")
    cwd = data.get("cwd") or os.getcwd()

    def git(cmd):
        try:
            return subprocess.check_output(
                ["git", "-C", cwd, *cmd], text=True, timeout=5,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            return ""

    branch = git(["rev-parse", "--abbrev-ref", "HEAD"])
    commit = git(["rev-parse", "--short", "HEAD"])

    gpus = str(int(nodes) * 4) if nodes.isdigit() else ""

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        SA_KEY,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    row = [ts, jobid, job_name, nodes, gpus, time_lim, script, user, branch, commit, cwd, "SUBMITTED"]

    svc.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{TAB}!A:L",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        try:
            with open(LOG_ERR, "a") as f:
                f.write(f"{datetime.now().isoformat()} ERROR: {e}\n")
        except Exception:
            pass
        sys.exit(0)
