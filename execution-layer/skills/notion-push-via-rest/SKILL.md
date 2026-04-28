---
name: notion-push-via-rest
description: Push markdown content to Notion via REST API using Internal Integration Token. Default content language is Chinese unless target thread is already English. Use when the user wants to sync status/reports/docs to Notion and Notion MCP OAuth is failing, or as the primary path for reliable one-way pushes. Trigger on "push to notion", "sync to notion", "update notion page", "notion mcp broken", or any Notion OAuth "No OAuth flow is in progress" / reconnection failure error.
version: 1.1.0
allowed-tools: Read, Write, Bash
alwaysApply: false
default-language: zh-CN
default-parent-page: 34d12c45-68fd-8080-a773-e9d5de348efe  # "tasks april 2026", kang.li workspace
---

# Notion Push via REST API

## When to Use

- User wants to push markdown content to a Notion page and Notion MCP's `mcp__notion__*` real tools aren't loaded (only bootstrap `authenticate`/`complete_authentication` available).
- Notion MCP OAuth flow fails with `No OAuth flow is in progress for notion` (Claude Code issue #10250, #46140).
- As the default path for programmatic Notion pushes: Internal Integration Token doesn't expire, no PKCE state loss risk across MCP reconnects.
- One-off status reports, experiment snapshots, or CSV/markdown → Notion table conversions.

## Default Language: Chinese (restated: this is a hard default, not a suggestion)

**For this user (kang.li), Notion page content defaults to Chinese on the very first push.** Set per global memory `feedback_notion_thread_auto_push.md` and reinforced multiple times by direct correction:
- 2026-04-23: "in chinese!! update the notion skill"
- 2026-04-26: "remember in claude.md and update the skill to use chinese as defaults"

If the next push you draft is in English without an explicit thread-language reason, **stop and rewrite in Chinese before sending the API call**.

| Situation | Language |
|---|---|
| New page created by Claude (push, subpage, status report) | **Chinese** for headings, paragraphs, ASCII chain annotations |
| Reply/append to existing thread with ≥2 prior English replies | **English** (match thread tone) |
| Code blocks (commands, paths, JSON, SLURM job IDs) | **Untranslated** — `sbatch`, `claude --resume`, `/lus/...` paths stay verbatim |
| Page title | Mixed OK (e.g. `mamba3 mimo 79M training`) but lean toward Chinese keywords |

**Implementation pattern**: Body in Chinese natural language, keep technical identifiers (job IDs, W&B slugs, SLURM commands, file paths, error names like `ScopeParamShapeError`) in original form. Never translate code/paths.

**Anti-pattern**: writing English content first then "translating later". User explicitly corrected this 2026-04-23. Write Chinese on the first push.

## Reading Notion Pages: Inline `[...]` Instructions Are Hidden Tasks

**Mandated by global CLAUDE.md (2026-04-25 "Inline instruction convention in user documents").** When the user shares a Notion page URL or asks you to act on its content, **scan every block for `[...]` square-bracketed text** before responding. These are not visual emphasis. They are commands the user has embedded in the document for you to execute.

### Detection

Walk `GET /v1/blocks/{page_id}/children` results and inspect every `rich_text[].plain_text` segment for a pattern like:

```
some prose ... [imperative phrase here] ... more prose
```

Each `[...]` is one task. Plus, **bold + underline phrases adjacent to a `[...]`** are also commands. Treat the entire set as a task list and execute in document order.

### Examples of inline commands

| Bracketed phrase | Action |
|---|---|
| `[do a profiling and find the bottleneck]` | run profiling, write findings back |
| `[depth-3 investigate this claim]` | spawn Explore subagent, drill in |
| `[make a subpage with results]` | `POST /v1/pages` under this page, not append |
| `[push to slack #channel]` | use slack push helper, not Notion |
| `[answer here in chinese]` | reply in Chinese, in this page |

### Mandatory workflow when reading a user-shared Notion page

1. Fetch the full page (and any embedded images via the `image_blocks` rule already in `feedback_notion_read_image_blocks.md`).
2. Build a list of every `[...]` bracketed phrase in document order.
3. Treat each as a TaskCreate item.
4. Execute in order. Use `submit-job`, `Bash`, sub-agents, or other skills as the bracketed phrase requires.
5. Write results back (subpage if instructed, append otherwise — see decision matrix below).
6. **Mark each `[...]` done by editing the original block from `[xxx]` to `[xxx ✓ <one-line result summary>]`** so the user can scan the page and see what was completed.

**Anti-pattern**: treating `[...]` as ordinary text and ignoring it. The user has corrected this multiple times. Brackets are a contract — every one is an explicit task. Even small ones.

**Auto mode does not relax this rule.** If a `[...]` involves a destructive action (deleting files, force-pushing, running > 12 h × > 2 nodes), pause and confirm per the global safety rules. But the *parsing* and *enumeration* of bracketed tasks must always happen.

## Subpage vs Append Decision

**User says "create a subpage in this page"** → `POST /v1/pages` with `parent.page_id=<PARENT>`. New page.

**User says "reply" / "append" / "update this page"** → `PATCH /v1/blocks/{page_id}/children`. Append-only.

**Wrong page created by mistake** → `PATCH /v1/pages/{id}` with `{"archived": true}` to archive (page goes to trash but URL still accessible), then re-create. See `push_to_notion.py` archive_old() helper at the end of this skill for example.

**Recipe location**: Save the push script under the active task directory at `tasks/<topic>/push_to_notion.py` so each task's Notion publishing is self-contained and reproducible. The script doubles as documentation of what was published.

## Progress Push Template (Append-mode, 2026-04-26)

When pushing a "task complete" / "milestone" reply to a thread via `PATCH /v1/blocks/{page_id}/children`, mirror the **Completion Summary template** from global CLAUDE.md (Three-Layer Model section). Drop the chat-only `★ Insight` block, keep the other 6 segments. This guarantees parity between what the user sees in chat and what lands in the Notion record.

### Structure (mandatory, in order)

| # | Block type | Content |
|---|---|---|
| 0 | `divider()` | Visual separator from prior reply |
| 1 | bold paragraph | `[Kang  YYYY-MM-DD, response] <one-line summary with commit hash>` (Slack-style header, two spaces after name) |
| 2 | paragraph | Decision rationale: 1-2 sentences citing the constraint chosen vs rejected, with `file:line` refs |
| 3 | bold paragraph + bullets | "Files changed (N files, +A / -B):" then one bullet per file as `path:line -- <effect>`. Effect-level, not raw diff |
| 4 | bold paragraph + bullets (optional) | "Files NOT touched (intentional):" — surgical scope reassurance. Skip when not relevant |
| 5 | paragraph | Robustness / mechanism note (e.g. "existing try/except routes to fallback when ..." ) |
| 6 | bold paragraph + bullets | "Performance caveat:" or "Caveat / Tradeoff:" — known regression regime, override instructions, evidence (numbers from session log if available) |
| 7 | bold paragraph + bullets | "Open items (awaiting your direction):" — verification pending GPU, push pending user confirm, deferred followups |
| 8 | empty paragraph | Trailing whitespace so the next reply inserts cleanly |

ASCII architecture diagrams from chat **do not** translate to Notion well (paragraph-level box-and-arrow renders as monospace blob). When the chat reply has a diagram, replace it with a `code(text, language="plain text")` block in Notion using the same ASCII content; render quality is acceptable inside a code fence.

### Code template

```python
children = [
    divider(),
    para("[Kang  2026-04-26, response] <feature> done (commit abc1234)", bold=True),
    para("Decision: <chose X / rejected Y>. Reason: <constraint at file:line>."),
    para("Files changed (N files, +A / -B):", bold=True),
    bullet("path/to/file:LINE -- <effect, not diff>"),
    # ...
    para("Files NOT touched (intentional):", bold=True),
    bullet("<file> -- <why>"),
    # ...
    para("<robustness / mechanism sentence>"),
    para("Performance caveat:", bold=True),
    bullet("<regime where this wins, with numbers>"),
    bullet("<regime where this regresses, with override instruction>"),
    para("Open items (awaiting your direction):", bold=True),
    bullet("◻ <verification step that costs GPU>"),
    bullet("◻ git push <branch> pending user confirmation"),
    para(""),
]
```

### Why this structure (the 30-second test)

A reader hitting this thread cold should answer all of these in under 30 seconds:
- What got done? (block 1 + block 3)
- Why this approach over alternatives? (block 2)
- What's the regression risk? (block 6)
- What still needs to happen? (block 7)

Skipping any of these creates a gap that costs the user a round-trip clarification.

### Anti-patterns

| Bad | Why bad |
|---|---|
| One giant paragraph instead of bullets | unscannable, can't reference individual files |
| Pasting raw `git diff` output as a code block | duplicates `git show`, costs API budget, no semantic value |
| Skipping the caveat section | user uses the new default in the wrong regime, hits regression, loses node-hours |
| Skipping "Open items" | user thinks 100% done, doesn't run smoke test, doesn't push |
| Forgetting `divider()` at top | reply visually merges with prior block, hard to delineate |
| Including the chat-only `★ Insight` bullets | duplicates info that's already in chat; clutter in Notion record |
| Using English when thread is Chinese (or vice versa) | breaks `feedback_notion_thread_auto_push.md` language rule (≥2 prior English replies → English; otherwise Chinese) |

## Why not MCP?

MCP OAuth for Notion is broken in Claude Code as of 2026-04:
- `authenticate` tool creates in-progress state tied to a per-connection MCP session.
- Every Claude Code turn may drop/reopen the MCP sub-connection.
- By the time user pastes callback URL and I call `complete_authentication`, the server-side state is gone → "No OAuth flow is in progress".
- Known issues: [#10250](https://github.com/anthropics/claude-code/issues/10250), [#46140](https://github.com/anthropics/claude-code/issues/46140).
- Workaround requires Claude Code restart; still fragile across `/compact`.

Internal Integration Token is a stable bearer token, no session state, just `Authorization: Bearer ntn_...` header on each `curl`.

## Process

### Step 1 — Obtain Integration Token (one-time per workspace)

Ask user to:
1. Visit https://www.notion.so/my-integrations
2. "New integration" → name it (e.g., `cc`) → pick workspace → Submit
3. Copy the `ntn_...` secret

Store it:
```bash
umask 077
printf '%s' '<user-pasted-token>' > ~/.notion_token
chmod 600 ~/.notion_token
```

**NEVER** echo the token to logs, NEVER commit `~/.notion_token` to git, NEVER pass it on command-line (avoid `ps` leak). Read into env var from file.

### Step 2 — Verify token

```bash
curl -sS -H "Authorization: Bearer $(cat ~/.notion_token)" \
     -H "Notion-Version: 2022-06-28" \
     https://api.notion.com/v1/users/me
```

Should return `{"object":"user","type":"bot",...,"workspace_name":"..."}`.

### Step 3 — Share parent page with integration (critical, manual step)

Integration has access to ZERO pages by default. User must:
1. Open target parent page in Notion UI
2. Click `...` → `Connections` → search integration name → Confirm

Once a page is shared, all its descendants inherit access.

Ask user for the parent page URL after sharing. Extract page ID from URL:
- `https://www.notion.so/Page-Title-34912c4568fd8096a17ce8c4600487d5` → ID `34912c4568fd8096a17ce8c4600487d5`
- Reformat with hyphens for API: `34912c45-68fd-8096-a17c-e8c4600487d5`

### Step 4 — Verify access to parent

```bash
PAGE_ID="34912c45-68fd-8096-a17c-e8c4600487d5"
curl -sS -H "Authorization: Bearer $(cat ~/.notion_token)" \
     -H "Notion-Version: 2022-06-28" \
     https://api.notion.com/v1/pages/$PAGE_ID
```

If you get `{"object":"error","code":"object_not_found"}`, the user hasn't shared the page yet.

### Step 5 — Push markdown via Python script

Use the template at `push_notion.py` in this skill directory. Core flow:

1. Read markdown file.
2. Convert to Notion blocks (`md_to_blocks`).
3. `POST /v1/pages` with `parent.page_id=<PARENT>`, `properties.title=[{...}]`, `children=first_100_blocks`.
4. If more than 100 blocks: `PATCH /v1/blocks/{child_id}/children` in batches of 100.

Invoke:
```bash
# Edit MD_PATH, TITLE, PARENT constants at top of push_notion.py
python3 /lus/lfs1aip2/projects/s5e/quant/.claude/skills/notion-push-via-rest/push_notion.py
```

Or copy script to `/tmp` and edit inline.

## Key Insights

### Notion API quirks

| Quirk | Detail |
|---|---|
| Children cap per request | 100 blocks. Batch with `PATCH /v1/blocks/{id}/children`. |
| rich_text content cap | 2000 chars per element. Split long strings into multiple rich_text entries. |
| Table block structure | `table.table_width` = column count; each row is `table_row` child; each cell is a `rich_text` array. |
| Code block languages | Enum only: `python`, `bash`, `javascript`, `json`, `plain text`, etc. Unknown → fall back to `plain text`. |
| Heading levels | Only `heading_1`, `heading_2`, `heading_3`. No h4/h5/h6. Map h4+ to h3 or paragraph. |
| Divider | `{"type":"divider","divider":{}}` — empty object required, not `null`. |
| Page ID format | UUID with hyphens. URL format lacks hyphens, must reformat. |

### Security pattern

| Do | Don't |
|---|---|
| `cat ~/.notion_token` in shell | `--data '{"token":"ntn_..."}' ` on command line |
| `chmod 600` on token file | Leave token in shell history |
| Keep token file outside git | Commit `.notion_token` (add to .gitignore) |
| Re-use `cc` integration across workspaces via "Connections" | Create one integration per push script |

### Fallback hierarchy

If MCP Notion tools are available AND working → prefer them (richer tool surface, built-in search).
If MCP broken → this skill (REST API).
If REST API access denied → user hasn't shared page; re-prompt for Connections step.

## Verification

After push, verify:
1. Script prints `url: https://www.notion.so/...` — open in browser.
2. All sections/tables/code blocks rendered correctly.
3. No truncated rich_text (look for missing ends of long paragraphs).
4. `curl GET /v1/blocks/{child_id}/children?page_size=100` → confirm block count matches expected.

Report URL back to user so they can click through.

## LaTeX Equation Support

`push_notion.py` supports both block-level and inline LaTeX equations using Notion's native `equation` block and `equation` rich_text segment (KaTeX renderer).

### Block equations

Triggered by any of the following patterns in the markdown:

| Markdown syntax | Example |
|---|---|
| `$$` alone on a line (fence) | `$$` ... `$$` |
| Single-line `$$expr$$` | `$$V = mc^2$$` |
| `\begin{align}...\end{align}` | multi-line aligned |
| `\begin{equation}...\end{equation}` | single equation |
| `\begin{gather}...\end{gather}` | gathered equations |
| `\[...\]` | display math |

Output: `{"type": "equation", "equation": {"expression": "<bare latex>"}}` block.

**align → aligned conversion**: Notion KaTeX does not support `\begin{align}` — it only supports `\begin{aligned}`. The converter automatically replaces `\begin{align}` with `\begin{aligned}` (and `\end{align}` → `\end{aligned}`), and likewise for `gather` → `aligned`. The `&` alignment markers and `\\` line breaks inside are preserved as-is.

### Inline equations

`$expr$` (single dollar, not `$$`) within a line is converted to an inline `equation` rich_text segment: `{"type": "equation", "equation": {"expression": "expr"}}`. This renders inline KaTeX inside paragraphs, headings, bullet items, etc.

### KaTeX passthrough

Notion's KaTeX subset natively handles: `\frac`, `\log`, `\overbrace{}^{}`, `\underbrace{}_{}`, `\\`, `&`, `\delta`, `\lambda`, `\nu`, `\mu`, `e^{-x}`, `\begin{aligned}`, etc. No additional escaping is needed.

### Example markdown

```markdown
Block equation (fence):

$$
T^* = \frac{1}{\nu} \log\left[\frac{(\delta+s)/2 + c/\nu}{(\delta-s)/2 + c/\nu}\right]
$$

Block equation (align, auto-converted to aligned):

\begin{align}
V^b_L(T^*) &= V^b_M \\
\left(\frac{\delta + s}{2} + \frac{c}{\nu}\right) e^{-\nu T^*} &= \frac{\delta - s}{2} + \frac{c}{\nu}
\end{align}

Inline: The continuation value is $V^b_M = (\delta - s)/2$.
```

## Related issues / docs

- [Notion API docs](https://developers.notion.com/reference/intro)
- [Block object reference](https://developers.notion.com/reference/block)
- [Notion equation block reference](https://developers.notion.com/reference/block#equation)
- [Claude Code MCP OAuth bug #10250](https://github.com/anthropics/claude-code/issues/10250)
- [Bearer token never sent #46140](https://github.com/anthropics/claude-code/issues/46140)
