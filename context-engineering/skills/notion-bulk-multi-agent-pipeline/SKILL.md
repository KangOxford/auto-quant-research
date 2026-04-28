---
name: notion-bulk-multi-agent-pipeline
description: Race-safe pattern for creating N>10 Notion pages in parallel via subagents. Use when bulk-creating Notion subpages (wikis, dashboards, indices) where multiple agents POST/PATCH concurrently. Covers pre-allocation strategy, state-file race avoidance, and Notion-as-source-of-truth recovery. Trigger on "create 50 notion pages", "bulk notion pipeline", "parallel notion agents", "notion subpage hierarchy".
version: 1.0.0
allowed-tools: Read, Write, Bash, Edit, Agent
alwaysApply: false
default-language: zh-CN
---

# Notion Bulk Multi-Agent Pipeline

## When to Use

When the user wants to create more than ~10 Notion subpages, especially via parallel subagents. Common scenarios:
- "Build a wiki with 50+ pages"
- "Create one Notion subpage per git worktree / experiment / artifact"
- "Push N markdown files as separate Notion subpages"
- Hierarchical structures: parent pages with N child pages each

If single-page push: use `notion-push-via-rest` skill instead. This skill is for **N-way parallel** creation.

## The Race Condition Problem

```
Agent A: read state.json → modify A's entry → write back
                                    ↑
Agent B: read state.json (old) → modify B's entry → write back (overwrites A's entry)
```

If multiple agents share a single state file via read-modify-write, **the last writer wins** and earlier agents' entries are lost. The Notion pages still exist (the POST succeeded), but the local index loses page_ids.

This silently breaks anything that builds on the state file (e.g., navigation builders).

## Process — 3 Strategies (pick by scenario)

### Strategy 1: Pre-allocate (preferred)

```
[Main session, sequential]
1. Build full schema with N page entries (id, title, icon, parent)
2. POST /v1/pages × N (with empty children=[]) → collect all page_ids
3. Persist {schema_id → page_id} mapping ONCE
4. Dispatch agents to PATCH content into KNOWN page_ids
   → no shared write, fully parallel-safe
```

POST is fast (~300-500ms). 50 pages ≈ 25 seconds in main session. Agents do the heavy content work in parallel.

### Strategy 2: Per-agent state shard

If pre-allocation isn't possible (e.g., agents discover new pages dynamically):

```
agent-K writes:  state-K.json     {pages: {K1: ..., K2: ...}}
agent-O writes:  state-O.json     {pages: {O1: ..., O2: ...}}
... no overlap ...
[Main session aggregates after all agents complete]
```

Don't dispatch agents that all write to `state.json`. Each agent has its own JSON.

### Strategy 3: Recovery via Notion GET

If Strategy 1/2 failed and state file is incomplete:

```python
# Notion is the source of truth. State file is just cache.
GET /v1/blocks/{top_page_id}/children?page_size=100
for child in results:
    if child['type'] == 'child_page':
        page_id = child['id']
        title = child['child_page']['title']
        # parse title prefix to identify which schema entry this is
        # rebuild state file
```

This worked in the 2026-04-27 LOBS5 wiki rebuild: 2 letter parents (Q, S) lost from state.json after race; recovered by GET children + title-prefix matching.

## Key Insights

1. **Notion is single source of truth, not local state**: design recovery paths that re-read Notion when local cache is suspect.

2. **Idempotent state-save after each step**: each `POST /v1/pages` writes back to state immediately, so partial failures don't lose data.
   ```python
   for entry in schema:
       new_id = api("POST", "/pages", body)
       state[entry["num"]] = {"page_id": new_id, ...}
       save_state(state)  # ← persist after EACH page, not at end
   ```

3. **Pre-create lets agents become PATCH-only**: PATCH /v1/blocks/{known_id}/children is race-free because each agent works on its own page_id. Creation is the dangerous step.

4. **Title prefix as recovery key**: Use `<num> <icon> <topic>` as page title so you can reverse-lookup from Notion children. Don't rely on order.

5. **Light throttle helps**: `time.sleep(0.35)` between POSTs avoids hitting Notion's 3 RPS limit. With exponential backoff in api(), 429 retries work but slow you down.

6. **Pages created with empty children=[] are valid**: Notion accepts this. You can create empty pages, then PATCH content later. Don't try to create page+content in single POST for bulk.

## Push Protocol Recap

For each agent's PATCH content workflow:
1. First block: resume callout (claude --resume + cwd) at top of agent's contribution
2. Divider + ingest header (timestamp)
3. md_to_blocks(content) — see notion-push-via-rest for converter
4. Footer divider + footer paragraph
5. Batches of ≤100 blocks per PATCH

For `after=<existing_first_block_id>` to position callout near top of an existing page (multi-machine append-only): see notion-push-via-rest skill.

## Verification

After bulk pipeline completes:

```bash
# 1. Count children of top page = expected total
PID=<top_page_id>; TOKEN=$(cat ~/.notion_token)
curl -s "https://api.notion.com/v1/blocks/${PID}/children?page_size=100" \
  -H "Authorization: Bearer $TOKEN" -H "Notion-Version: 2022-06-28" \
  | jq '[.results[] | select(.type=="child_page")] | length'

# 2. Diff schema vs state file
jq -r '.pages[].num' schema.json | sort > /tmp/schema_nums
jq -r '.pages | keys[]' state.json | sort > /tmp/state_nums
diff /tmp/schema_nums /tmp/state_nums  # should be empty

# 3. If diff non-empty, GET children + reconcile (Strategy 3)
```

## Anti-patterns

- ❌ One mega-agent doing all 50 creates sequentially (slow + single point of failure)
- ❌ N agents all reading and writing the same `state.json` (race condition)
- ❌ Trusting state.json over Notion when they disagree (Notion wins)
- ❌ Hardcoding page_ids in code (use schema + state file abstraction)
- ❌ Skipping `save_state` between iterations (one crash = lose all progress)

## Real-world Reference

This skill encodes the design from the 2026-04-27 LOBS5 auto-wiki rebuild:
- 50 categories pages (pre-allocated in main session, agents PATCH content) — 0 races
- 91 letter-hierarchy pages (agents created own subpages, shared state file) — Q/S parent_ids lost, recovered via GET children + title prefix match

The pre-allocate strategy was the clean win.
