---
name: notion-auto-sync-md
description: Auto-sync markdown files to Notion via a PostToolUse Claude Code hook — whenever Edit/Write touches a registered md file, a shell+python hook pushes it to Notion (archive old page + create new page). Zero Claude tokens used per sync. Use when you want specific md reports/results/docs to stay up-to-date on Notion without manual "push to notion" commands. Trigger on "auto sync to notion", "notion hook", "sync md to notion automatically", "notion manifest".
---

# Notion Auto-Sync for Markdown

## When to Use

You have specific markdown files (experiment results, status reports, running docs) that change often and need to reflect on Notion, AND:

- Don't want to burn Claude tokens running `python3 push_notion.py` manually each time.
- Don't want to remember to push after every edit.
- Are OK with a "one live page per md file" model (old versions archive to Notion trash).

This skill complements `notion-push-via-rest` (one-off pushes) by making pushes automatic and persistent.

## Architecture

```
Edit/Write tool finishes
        │
        ▼
PostToolUse hook (matcher: Edit|Write|MultiEdit)
        │
        ▼
notion-sync-md.sh (reads stdin JSON)
        │
        ├── extracts tool_input.file_path  AND  top-level session_id
        ├── file_path not .md? exit 0
        ▼
notion-sync-md.py <file_path> [session_id]
        │
        ├── Load ~/.claude/notion-sync-manifest.json
        ├── file_path not in manifest? log SKIP, exit
        ▼
Archive old page (if last_page_id)
Build blocks = session_header_blocks(session_id) + md_to_blocks(content)
Create new page (header rides in first 100-block batch)
Save new page_id (+ last_session_id) to manifest
Log result to ~/.claude/notion-sync.log
```

All async (`&` + `async: true`), so Claude's main flow never waits on Notion.

## Files

| Path | Purpose |
|------|---------|
| `~/.claude/hooks/notion-sync-md.sh` | Shell wrapper — extracts file_path from stdin JSON, filters .md, invokes python helper |
| `~/.claude/hooks/notion-sync-md.py` | Python helper — md→blocks conversion, Notion REST calls, manifest read/write |
| `~/.claude/notion-sync-manifest.json` | Registry of sync targets — `files: {abs_path: {title_prefix, last_page_id}}` |
| `~/.claude/notion-sync.log` | Append-only log, one line per sync attempt/result |
| `~/.notion_token` | Internal Integration Token (bearer, chmod 600) |

## Setup (one-time)

### Step 1 — Notion token

If `~/.notion_token` doesn't exist, follow `notion-push-via-rest` skill Step 1-3 to obtain it and share parent page with the integration.

### Step 2 — Install hook scripts

Copy `notion-sync-md.sh` and `notion-sync-md.py` to `~/.claude/hooks/`, chmod +x both.

### Step 3 — Register PostToolUse hook in settings.json

```json
"hooks": {
  "PostToolUse": [
    {
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [
        {
          "type": "command",
          "command": "bash ${HOME}/.claude/hooks/notion-sync-md.sh",
          "timeout": 15,
          "async": true
        }
      ]
    }
  ]
}
```

### Step 4 — Create manifest

`~/.claude/notion-sync-manifest.json`:

```json
{
  "default_parent_id": "<PARENT-PAGE-ID-WITH-HYPHENS>",
  "files": {
    "/abs/path/to/RESULTS.md": {
      "title_prefix": "Experiment Results",
      "last_page_id": "",
      "last_session_id": ""
    }
  }
}
```

Add new md files to sync by editing the `files` object. `last_page_id` and `last_session_id` are bookkeeping fields — leave them empty on first registration; the helper writes them after each successful push.

## Adding a New Sync Target

```bash
python3 -c "
import json, sys
p = '$HOME/.claude/notion-sync-manifest.json'
with open(p) as f: m = json.load(f)
m['files']['<NEW_ABS_PATH>'] = {
    'title_prefix': '<Short Title>',
    'last_page_id': ''
}
with open(p, 'w') as f: json.dump(m, f, indent=2)
"
```

Next Edit/Write of that file will trigger an initial sync.

## Sync Semantics

- **First sync**: create Notion page with title `<title_prefix> — YYYY-MM-DD HH:MM`, store page_id.
- **Subsequent sync**: `PATCH /v1/pages/{old_id} archived=true` (moves to trash), then create new page, update manifest.
- **Only one "live" page per md file** in the parent. Trash holds the audit trail.
- **Granularity**: every Edit/Write/MultiEdit triggers one sync. Spamming small edits → many archived pages. That's fine; Notion trash has 30-day retention by default.

### Session header (provenance)

Every page synced via the hook is prepended with a small header block:

```
Claude Code session: <session-id>  ·  Resume: claude --resume <session-id>
─────────────────────────────────────────────────
<original markdown body>
```

- Source: `session_id` is read from the top-level field of the PostToolUse hook JSON, forwarded as `argv[2]` to the python helper.
- Rendering: a single `paragraph` block (bold label, code-styled IDs) followed by a `divider`. No emoji, no callout, no required icon.
- Manual invocation (`python3 notion-sync-md.py /tmp/foo.md` with no 2nd arg) emits **no** header — backward compatible.
- The same `session_id` is also persisted as `last_session_id` inside the file's manifest entry, so you can later look up "which session pushed this page?" without scraping the page body.

## Verify

After an edit:

```bash
tail -5 ~/.claude/notion-sync.log
cat ~/.claude/notion-sync-manifest.json | python3 -m json.tool
```

Expect: log entry for `PUSH`, `archived old page`, `created new page`, `manifest updated`.

Browse the new page:

```
https://www.notion.so/<hyphenless-page-id>
```

## Debugging

| Symptom | Cause / Fix |
|---------|-------------|
| No log entry after edit | Hook didn't fire — check `matcher` includes your tool, check `settings.json` syntax |
| `SKIP: not in manifest` | File not registered — edit manifest |
| `HTTP 404 on PATCH /pages/{id}` | Old page already deleted; harmless (hook continues to create new) |
| `HTTP 401` | Token expired or revoked — regenerate at notion.so/my-integrations |
| `object_not_found` on POST /pages | Parent not shared with integration — re-share in Notion UI |
| New page empty / broken tables | md_to_blocks bug — copy to `/tmp/foo.md`, run `python3 notion-sync-md.py /tmp/foo.md` interactively, inspect log |

## Known Limitations

**Parallel push race condition**: The python helper reads manifest, modifies one entry, writes back. If multiple files are pushed concurrently (e.g., initial backfill of several files at once via `for F in ... do python3 helper.py &`), only the last writer's `last_page_id` update survives — others are lost. Pages are created correctly on Notion, but manifest may miss IDs.

Mitigation: push sequentially (no `&`), OR fix manually in manifest using log entries (the new page IDs are logged). A proper fix would use `fcntl.flock` on the manifest file; not implemented here because single-file edits (the 99% case) don't race.

## Costs

- Claude tokens per sync: **0** (hook runs in shell, fully outside Claude context).
- Notion API calls per sync: 1 (archive) + 1 (create page) + ceil(blocks/100) (append batches) ≈ 2-3 calls.
- Typical sync latency: 1-3 seconds (async, doesn't block Claude).

## Related

- `notion-push-via-rest` — manual one-off push, covers token setup steps.
- `auto-approve-skills-edits.sh` (existing hook) — pattern for per-directory auto-approve.
