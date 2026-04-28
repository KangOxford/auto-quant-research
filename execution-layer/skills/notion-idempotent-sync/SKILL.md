---
name: notion-idempotent-sync
description: Archive-then-rewrite pattern for idempotent markdown to Notion push. Re-running yields same final state instead of duplicating blocks. Required when notion-push-via-rest (append-only) would duplicate content on re-run, or when notion-md-sync v0.16.0 fails on table blocks.
version: 1.0.0
allowed-tools: Bash, Read, Write
alwaysApply: false
---

# Notion Idempotent Sync via Archive-then-Rewrite

## When to Use

Trigger this skill when ALL of:
1. You have local markdown files that already correspond to **existing** Notion pages (page_id known)
2. You need to re-push content (because md was edited) WITHOUT duplicating blocks on the Notion side
3. The naive PATCH /v1/blocks/{page_id}/children would append duplicate copies

Specifically:
- "Sync md to Notion idempotently"
- "Re-push wiki content without duplicating"
- "Update existing Notion page from markdown source"
- After failure of `notion-md-sync` (Go CLI v0.16.0 has table block bug)
- When `notion-push-via-rest` skill's append-only PATCH is causing duplication

NOT for:
- Creating new pages from scratch (use `notion-bulk-multi-agent-pipeline` Strategy 1)
- One-time push where re-run isn't expected (use `notion-push-via-rest`)
- Bidirectional sync (Notion -> md): need a separate puller

## Core Pattern

```
local md (with optional YAML frontmatter)
        |
        v
  strip_frontmatter(content)        # remove YAML head if present
  blocks = md_to_blocks(content)    # use verified converter
        |
        v
  GET /v1/blocks/{page_id}/children # paginated, all existing
  for each block: DELETE /v1/blocks/{block_id}   # archive (soft)
  sleep 1.5s                                     # let Notion register
  PATCH /v1/blocks/{page_id}/children            # batches of 100
        |
        v
  Notion page now matches md (idempotent)
```

## Process

### Step 1: Verify Page IDs Already Mapped

You need a mapping `{md_file: page_id}`. Typical sources:
- `schema_with_ids.json` from earlier bulk creation (see `notion-bulk-multi-agent-pipeline`)
- YAML frontmatter `notion_id:` field in each md (compatible with notion-md-sync style)

If no mapping exists, this skill does NOT apply. You need to create pages first.

### Step 2: Strip Frontmatter Before Conversion

Critical step. If you leave YAML frontmatter in the md content fed to converter:
- Converter renders `---` as horizontal divider
- YAML body becomes garbage paragraphs
- Page header gets polluted with `title: "..."` etc.

```python
def strip_frontmatter(content: str) -> str:
    if not content.startswith("---\n"):
        return content
    end_idx = content.find("\n---\n", 4)
    if end_idx < 0:
        return content
    return content[end_idx + 5:]  # past the closing ---\n
```

### Step 3: Use Verified md_to_notion Converter

DO NOT use `notion-md-sync` v0.16.0 for tables. It has a bug:
```
body.children[N].table.children should be defined, instead was undefined
```

The bug archives existing blocks (success) then fails to insert new (validation error). Page ends up empty (0 blocks). Recovery requires our own converter.

Verified safe converter: `/projects/s5e/quant/notion_figures/02d_complex_negative/md_to_notion.py`
Function: `md_to_blocks(content: str, base_dir: pathlib.Path) -> list[dict]`

This was validated on 18 pages x 640 blocks (heading, paragraph, quote, callout, code, table, bulleted/numbered list) with 0 errors.

### Step 4: Archive Existing Children (Pagination + Rate Limit)

```python
def get_all_children(page_id):
    out, cursor = [], None
    while True:
        path = f"/blocks/{page_id}/children?page_size=100"
        if cursor: path += f"&start_cursor={cursor}"
        data = api("GET", path)
        out.extend(data["results"])
        if not data.get("has_more"): break
        cursor = data["next_cursor"]
        time.sleep(0.35)
    return out

def archive_all_children(page_id):
    children = get_all_children(page_id)
    for blk in children:
        api("DELETE", f"/blocks/{blk['id']}")  # archive, not hard delete
        time.sleep(0.35)  # 3 RPS limit
    return len(children)
```

Notes:
- `DELETE /v1/blocks/{id}` is soft delete (archive). Blocks remain in Notion backend.
- Rate limit: ~3 RPS (set sleep 0.35s after each call). 429 retries with exponential backoff.
- Pagination required: Notion returns max 100 children per GET.

### Step 5: Wait Then PATCH New Blocks

```python
time.sleep(1.5)  # let Notion fully register the archives
def patch_children_chunked(page_id, blocks):
    for i in range(0, len(blocks), 100):
        chunk = blocks[i:i+100]
        api("PATCH", f"/blocks/{page_id}/children", {"children": chunk})
        time.sleep(0.35)
```

### Step 6: Single-File Canary Before Bulk

CRITICAL pattern. Before running on N pages, run on 1 page first:
1. GET baseline block count + icon + title
2. Run sync_one(num)
3. GET after, compare
4. If block count or block-type histogram matches expectation, proceed to bulk
5. If failure, use recovery script (just step 1-3 of this skill on the single page)

Without canary: a converter bug or rate-limit cascade can wipe N pages simultaneously. Recovery is N times harder.

## Reference Implementation

Working production script (validated 2026-04-28):
`/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/LOBS5/tasks/mihai_review_dump/step_b_idempotent.py`

CLI:
```bash
python3 step_b_idempotent.py              # process all
python3 step_b_idempotent.py --num 17     # canary single
python3 step_b_idempotent.py --dry-run    # plan only, no API write
```

## Key Insights

1. **Notion API has no efficient in-place block update**. The only path to "edit page content" is archive-old + insert-new. Tools like notion-md-sync, n2y, etc. all wrap this archive-then-rewrite primitive.

2. **Archive is soft delete, NOT recovery-loss-safe**. `DELETE /v1/blocks/{id}` archives the block. It still exists in Notion backend (no quota cost). To restore: PATCH page with archived=False on each block. But: archived blocks DO NOT show in `GET children`, so re-syncing works correctly without "ghost" blocks.

3. **Frontmatter pollution is silent**. If you forget to strip YAML head, page accumulates garbage paragraphs at top. Symptom: page shows literal `---\ntitle: "..."\nnotion_id: "..."` etc. Fix: `strip_frontmatter()` before `md_to_blocks()`.

4. **notion-md-sync v0.16.0 table bug**. Direct quote of error:
   `body.children[N].table.children should be defined, instead was undefined`
   When pushing markdown with `| col | col |` tables, the Go tool fails to populate Notion's required `table.children` field. It archives existing blocks BEFORE attempting insert, so failure leaves page at 0 blocks. AVOID this tool until v0.17+ confirms fix.

5. **Block IDs always change after sync**. archive-then-rewrite means new block IDs. Risk: any manual annotation, comment, or mention added directly in Notion will be archived (hidden but recoverable). Document this to users before bulk re-sync.

6. **Single-file canary is mandatory**. The 4-minute bulk process for N pages can wipe all N if converter has bug. Run on 1 page (the smallest, simplest, lowest-risk one), GET-verify, then proceed.

7. **archive count vs push count diff is acceptable**. Old append-only pushes may have left trailing blocks. After first idempotent run, count converges (e.g., 27 archived / 26 pushed). Subsequent runs match exactly.

## Verification Checklist

After bulk sync:
1. Each page reports `archived == pushed` (or close, with diff < 5)
2. `GET parent.children` shows expected child_page count
3. Spot-check 1-2 pages visually in Notion: title, icon, top-level structure correct
4. Re-run sync (no md changes): block counts identical to first run = truly idempotent

## Anti-Patterns

- DO NOT use `notion-md-sync` for any markdown containing tables (v0.16.0 confirmed broken)
- DO NOT skip the canary on bulk operations of 5+ pages
- DO NOT skip frontmatter strip if md uses YAML headers
- DO NOT remove the 1.5s wait between archive and PATCH (race with Notion registry)
- DO NOT parallelize archive DELETE calls (you will hit 429 even with backoff)
- DO NOT mistake archive for hard delete (it's recoverable; tell users)

## Integration with Existing Skills

- Build on `notion-bulk-multi-agent-pipeline` Strategy 1: pre-allocate pages, get IDs, then this skill takes over for content updates.
- Replaces `notion-push-via-rest` for repeat-sync scenarios. Use `notion-push-via-rest` for one-shot append (e.g., progress posts to a thread).
- Compatible with `notion-icon-emoji-safe-list`: page icon survives archive-then-rewrite (icon is page metadata, not in children).
