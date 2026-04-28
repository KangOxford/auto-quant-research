#!/usr/bin/env python3
"""
Parse the last assistant turn from a Claude Code transcript JSONL,
extract every "★ Insight ─...─" block, and:
  (1) append to ~/.claude/insights-log.md with a timestamp + session prefix
  (2) append to the Overleaf tex (if the day-to-day Overleaf repo exists)
  (3) fire-and-forget git commit+push on the Overleaf repo

Original text (Chinese / English) is preserved verbatim via LaTeX's
\\begin{verbatim} environment. The only mutation is a defensive replace
of a literal "\\end{verbatim}" inside the body to prevent env break.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TRANSCRIPT = os.environ.get("CC_TRANSCRIPT", "")
SESSION = os.environ.get("CC_SESSION", "")
CWD = os.environ.get("CC_CWD", "")

MD_PATH = Path.home() / ".claude" / "insights-log.md"
TEX_PATH = Path.home() / "AlphaTrade" / "LOBS5" / "overleaf" / \
    "69b804b1b5022d27002331fa" / "drafts" / "kang" / "insights.tex"
OVERLEAF_REPO = Path.home() / "AlphaTrade" / "LOBS5" / "overleaf" / \
    "69b804b1b5022d27002331fa"
PUSH_ERR_LOG = Path.home() / ".claude" / "insights-push-errors.log"

# ★ Insight ───...(newline) body (newline) ───...
INSIGHT_RE = re.compile(
    r"★\s*Insight\s*─+\s*\n(.*?)\n─+",
    re.DOTALL,
)


def last_assistant_text(path: str) -> str | None:
    """Return the concatenated text of the most recent assistant message."""
    last = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message") or {}
                content = msg.get("content") or []
                parts = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        parts.append(c.get("text") or "")
                if parts:
                    last = "\n".join(parts)
    except Exception:
        return None
    return last


def extract_blocks(text: str) -> list[str]:
    seen: list[str] = []
    for m in INSIGHT_RE.findall(text):
        body = m.strip()
        if body and body not in seen:
            seen.append(body)
    return seen


def append_md(blocks: list[str], ts: str) -> None:
    MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not MD_PATH.exists()
    with open(MD_PATH, "a", encoding="utf-8") as f:
        if new_file:
            f.write("# ★ Insights Log\n\n")
            f.write("Automatically captured from Claude Code sessions. "
                    "Original Chinese/English text preserved verbatim.\n\n")
        for b in blocks:
            sid = SESSION[:8] if SESSION else "????????"
            f.write(f"\n## {ts}  session `{sid}`  cwd `{CWD}`\n\n")
            f.write("★ Insight ─────────────────────────────────────\n")
            f.write(b)
            f.write("\n─────────────────────────────────────────────────\n\n")
            f.write("---\n")


def append_tex(blocks: list[str], ts: str) -> bool:
    """Return True if the tex file was written to."""
    if not TEX_PATH.parent.is_dir():
        return False
    new_file = not TEX_PATH.exists()
    if new_file:
        TEX_PATH.write_text(
            "\\documentclass{article}\n"
            "\\input{drafts/kang/preamble}\n\n"
            "\\title{Claude Insights Log}\n"
            "\\date{\\today}\n\n"
            "\\begin{document}\n"
            "\\maketitle\n\n"
            "\\section{Insights (append-only)}\n\n",
            encoding="utf-8",
        )
    with open(TEX_PATH, "a", encoding="utf-8") as f:
        for b in blocks:
            # Defensive: prevent verbatim env break if body contains the close tag
            safe = b.replace("\\end{verbatim}", "\\end {verbatim}")
            sid = SESSION[:8] if SESSION else "????????"
            f.write(f"\n\\paragraph{{{ts} \\texttt{{{sid}}}}}\\mbox{{}}\n\n")
            f.write("\\begin{verbatim}\n")
            f.write(safe)
            f.write("\n\\end{verbatim}\n")
    return True


def async_push(sid_short: str) -> None:
    if not (OVERLEAF_REPO / ".git").is_dir():
        return
    script = (
        f'cd "{OVERLEAF_REPO}" || exit 0; '
        'git add drafts/kang/insights.tex 2>/dev/null; '
        'if git diff --cached --quiet; then exit 0; fi; '
        f'git commit -m "chore(insights): session {sid_short}" -q 2>/dev/null || exit 0; '
        f'(git push origin master -q 2>>"{PUSH_ERR_LOG}") || '
        f'(git pull --rebase origin master -q 2>>"{PUSH_ERR_LOG}" && '
        f'git push origin master -q 2>>"{PUSH_ERR_LOG}") || true'
    )
    subprocess.Popen(
        ["bash", "-c", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main() -> int:
    if not TRANSCRIPT or not os.path.isfile(TRANSCRIPT):
        return 0
    text = last_assistant_text(TRANSCRIPT)
    if not text:
        return 0
    blocks = extract_blocks(text)
    if not blocks:
        return 0

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    append_md(blocks, ts)
    wrote_tex = append_tex(blocks, ts)
    if wrote_tex:
        async_push(SESSION[:8] if SESSION else "unknown")

    print(json.dumps({
        "suppressOutput": True,
        "systemMessage": f"★ logged {len(blocks)} insight(s) → "
                         f"{MD_PATH.name}"
                         + (f" + overleaf" if wrote_tex else ""),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
