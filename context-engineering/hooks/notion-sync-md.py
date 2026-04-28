#!/usr/bin/env python3
"""Auto-sync a markdown file to Notion via REST API.

Triggered by notion-sync-md.sh (PostToolUse hook). Reads
~/.claude/notion-sync-manifest.json to determine which files sync where.

Strategy for "update in place":
  1. If last_page_id exists in manifest, archive it via PATCH /v1/pages/{id}.
  2. Always create a new page with timestamp-suffixed title.
  3. Update manifest with new page_id (and last_session_id when supplied).

This keeps Notion showing ONE live page per md file (latest), with
archived versions available in trash for audit.

When a session_id is supplied (forwarded from the PostToolUse hook stdin),
a small "session header" block is prepended to the page body so the page
records which Claude Code session produced it and exposes the resume command.

Usage:
  python3 notion-sync-md.py <FILE_PATH> [SESSION_ID]
"""
import json, os, re, sys, time, urllib.request
from pathlib import Path
from datetime import datetime

HOME = Path(os.environ.get("HOME", "/lus/lfs1aip2/projects/s5e/quant"))
TOKEN_PATH = HOME / ".notion_token"
MANIFEST_PATH = HOME / ".claude/notion-sync-manifest.json"
LOG_PATH = HOME / ".claude/notion-sync.log"

NOTION_BASE = "https://api.notion.com/v1"


def log(msg):
    with open(LOG_PATH, "a") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")


def api(method, path, data=None, token=""):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{NOTION_BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:400]}")
        raise


def rich_text(content, bold=False, code=False):
    if not content:
        return []
    out = []
    while content:
        chunk = content[:1900]
        content = content[1900:]
        out.append({
            "type": "text",
            "text": {"content": chunk},
            "annotations": {"bold": bold, "code": code},
        })
    return out


def session_header_blocks(session_id):
    """Build a small provenance header: 'Session: <id>  ·  Resume: claude --resume <id>'
    rendered as a paragraph (with code-styled IDs) followed by a divider.
    Returns [] when session_id is empty so manual invocations stay backward-compatible."""
    if not session_id:
        return []
    return [
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": "Claude Code session: "},
                     "annotations": {"bold": True, "code": False}},
                    {"type": "text", "text": {"content": session_id},
                     "annotations": {"bold": False, "code": True}},
                    {"type": "text", "text": {"content": "  \u00b7  Resume: "},
                     "annotations": {"bold": False, "code": False}},
                    {"type": "text", "text": {"content": f"claude --resume {session_id}"},
                     "annotations": {"bold": False, "code": True}},
                ],
            },
        },
        {"type": "divider", "divider": {}},
    ]


def md_to_blocks(md):
    """Convert markdown to Notion block array. Supports headings, code, lists,
    tables, paragraphs, dividers. Limits: 100 blocks per children request."""
    blocks = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # Heading
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            key = f"heading_{level}"
            blocks.append({"type": key, key: {"rich_text": rich_text(m.group(2))}})
            i += 1
            continue
        # Code fence
        if line.startswith("```"):
            lang = line[3:].strip() or "plain text"
            lang_map = {"bash": "bash", "sh": "bash", "python": "python", "py": "python", "json": "json", "javascript": "javascript"}
            lang = lang_map.get(lang.lower(), "plain text")
            content = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                content.append(lines[i])
                i += 1
            blocks.append({"type": "code", "code": {"rich_text": rich_text("\n".join(content)), "language": lang}})
            i += 1
            continue
        # Table
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i+1]):
            rows = [line]
            i += 2  # skip header and separator
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            # parse header + data rows; rows[0] is header, rows[1:] are data
            header_cells = [c.strip() for c in rows[0].strip("|").split("|")]
            data_rows = [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]
            ncols = len(header_cells)
            table_rows = [{"type": "table_row", "table_row": {"cells": [rich_text(c) for c in header_cells]}}]
            for r in data_rows:
                while len(r) < ncols:
                    r.append("")
                table_rows.append({"type": "table_row", "table_row": {"cells": [rich_text(c) for c in r[:ncols]]}})
            blocks.append({
                "type": "table",
                "table": {"table_width": ncols, "has_column_header": True, "has_row_header": False, "children": table_rows},
            })
            continue
        # Bullet list
        if re.match(r"^\s*[-*]\s+", line):
            m = re.match(r"^\s*[-*]\s+(.*)", line)
            blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rich_text(m.group(1))}})
            i += 1
            continue
        # Numbered list
        if re.match(r"^\s*\d+\.\s+", line):
            m = re.match(r"^\s*\d+\.\s+(.*)", line)
            blocks.append({"type": "numbered_list_item", "numbered_list_item": {"rich_text": rich_text(m.group(1))}})
            i += 1
            continue
        # Divider
        if line.strip() in ("---", "***"):
            blocks.append({"type": "divider", "divider": {}})
            i += 1
            continue
        # Empty line
        if not line.strip():
            i += 1
            continue
        # Paragraph (gather non-blank consecutive lines)
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3}\s|\||```|---|\s*[-*]\s|\s*\d+\.\s)", lines[i]):
            para.append(lines[i])
            i += 1
        blocks.append({"type": "paragraph", "paragraph": {"rich_text": rich_text(" ".join(para))}})
    return blocks


def push_file(md_path, entry, default_parent, token, session_id=""):
    md_path = Path(md_path)
    if not md_path.exists():
        log(f"SKIP {md_path}: file not found")
        return None

    md = md_path.read_text()
    body_blocks = md_to_blocks(md)
    # Prepend a session-provenance header so each Notion page records
    # which Claude Code session authored it (and how to resume).
    blocks = session_header_blocks(session_id) + body_blocks
    log(f"PUSH {md_path}: {len(body_blocks)} body blocks (+{len(blocks) - len(body_blocks)} header) session={session_id or '-'}")

    parent = entry.get("parent_id") or default_parent
    title_prefix = entry.get("title_prefix", md_path.stem)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"{title_prefix} — {timestamp}"

    # Archive old page if exists
    old_page_id = entry.get("last_page_id", "")
    if old_page_id:
        try:
            api("PATCH", f"/pages/{old_page_id}", {"archived": True}, token)
            log(f"  archived old page: {old_page_id}")
        except Exception as e:
            log(f"  archive failed (continuing): {e}")

    # Create new page (slice operates on combined header+body so the
    # header always rides in the first request even when body > 100 blocks)
    page = api("POST", "/pages", {
        "parent": {"page_id": parent},
        "properties": {"title": [{"type": "text", "text": {"content": title}}]},
        "children": blocks[:100],
    }, token)
    page_id = page["id"]
    log(f"  created new page: {page_id}")

    # Append remaining blocks in batches of 100
    for start in range(100, len(blocks), 100):
        batch = blocks[start:start + 100]
        api("PATCH", f"/blocks/{page_id}/children", {"children": batch}, token)
        log(f"  appended {len(batch)} more blocks")

    return page_id


def main():
    if not TOKEN_PATH.exists():
        log(f"SKIP: {TOKEN_PATH} not found")
        return 0
    token = TOKEN_PATH.read_text().strip()

    if not MANIFEST_PATH.exists():
        log(f"SKIP: {MANIFEST_PATH} not found")
        return 0
    manifest = json.loads(MANIFEST_PATH.read_text())

    if len(sys.argv) < 2:
        log("SKIP: no file path arg")
        return 0
    file_path = sys.argv[1]
    # Optional 2nd arg: Claude Code session_id, plumbed by notion-sync-md.sh
    # from the PostToolUse hook stdin (top-level "session_id" field).
    session_id = sys.argv[2] if len(sys.argv) >= 3 else ""

    # Normalize path for manifest lookup
    if file_path not in manifest.get("files", {}):
        log(f"SKIP {file_path}: not in manifest")
        return 0

    entry = manifest["files"][file_path]
    default_parent = manifest.get("default_parent_id")
    try:
        new_page_id = push_file(file_path, entry, default_parent, token, session_id)
        if new_page_id:
            # Update manifest (record session_id when we have one for forensics)
            manifest["files"][file_path]["last_page_id"] = new_page_id
            if session_id:
                manifest["files"][file_path]["last_session_id"] = session_id
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
            log(f"  manifest updated: {file_path} -> {new_page_id} (session={session_id or '-'})")
    except Exception as e:
        log(f"ERROR pushing {file_path}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
