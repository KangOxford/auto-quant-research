---
name: list-recent-sessions
user-invocable: true
description: List N most recent Claude Code sessions with rich metadata — topic, timestamps, size, resume commands. Trigger on "recent sessions", "list sessions", "find recent", "what was I working on", "resume sessions".
arguments: "[timeframe] — e.g. '5h', '24h', '3d' (default 24h). Optional: [N] max sessions to show."
version: 2.0.0
---

# /list-recent-sessions — List Recent Sessions

Find recent Claude Code sessions across ALL project directories, extract metadata, and present in standardized table format.

## Output Format (MANDATORY)

The output MUST be a box-drawing ASCII table with exactly these columns:

```
| # | Session ID | Size | Started | Last Active | CWD | Topic | Resume |
```

- **Session ID**: first 8 chars of UUID (display only; full UUID in Resume column)
- **Size**: human-readable (e.g. 9.7M, 340K)
- **Started / Last Active**: from JSONL internal timestamps (NOT file mtime)
- **CWD**: abbreviated path (e.g. `.../LOBS5/tasks`, `/projects/s5e/quant`)
- **Topic**: extracted from user messages + keyword enrichment
- **Resume**: full `claude --resume <UUID>` command
- **Current session**: mark as "now" in Last Active, "--" in Resume

Sort by Size descending (largest = most substantive session first).

## Algorithm

### Step 1: Discovery

Search ALL project directories, not just current one. This is critical because users work across multiple cwds.

```bash
find /projects/s5e/quant/.claude/projects/ -name "*.jsonl" \
  -mmin -MINUTES -not -path "*/subagents/*" -type f \
  -exec ls -lhS {} + 2>/dev/null
```

Where MINUTES = timeframe converted to minutes (24h = 1440, 5h = 300, 3d = 4320).

### Step 2: Metadata Extraction

Run ONE Python script that processes all discovered files. Extract per session:

```python
# For each JSONL file, stream line-by-line (never load entire file):
# 1. custom-title → title
# 2. system with cwd → working directory  
# 3. First/last timestamp → Started/Last Active
# 4. type=="user" messages → first 5-10 for topic identification
#    IMPORTANT: message type is "user" NOT "human"
```

Key gotchas:
- Message type field is `"user"`, not `"human"`
- Content can be `str` or `list` of content blocks
- Filter out messages starting with `<` (system reminders) and skill invocations
- Timestamps use ISO format with `Z` suffix, parse with `.replace('Z', '+00:00')`

### Step 3: Topic Identification

Two-pass approach:
1. **First pass**: First 2-3 user messages (truncated to 150 chars each)
2. **Second pass** (if first pass is ambiguous): keyword grep for high-signal terms:
   - Post-training: `grpo|eggroll|evolution.strategy|reward`
   - Kernel dev: `cuda.ffi|tilelang|triton.*kernel|mamba|fla_kda`
   - Infrastructure: `tmux|quota|sbatch|slurm|nccl`
   - Paper writing: `overleaf|quant2026|latex|tex|Leandro`
   - Scaling: `scaling.law|benchmark|IC|DA`
   - Inference: `inference|lobench|eval`

### Step 4: Present Table

Print the table using markdown pipe syntax. Example output:

```
| # | Session ID | Size | Started | Last Active | CWD | Topic | Resume |
|---|-----------|------|---------|-------------|-----|-------|--------|
| 1 | 914d7d25 | 9.7M | Mar 31 04:27 | Apr 02 19:10 | .../LOBS5/tasks | Post-training scaling, IC/DA249, job monitoring | claude --resume 914d7d25-2ca6-4ffc-a2e2-bf408f8dd367 |
| 2 | 41763d09 | 9.3M | Mar 31 17:13 | Apr 02 19:05 | .../LOBS5/tasks | Paper writing, brainstorming, Codex review | claude --resume 41763d09-7dab-45b5-944a-cac20b9ac2c9 |
```

## CWD Abbreviation Rules

| Full Path | Abbreviated |
|-----------|-------------|
| `.../AlphaTrade/LOBS5/tasks` | `.../LOBS5/tasks` |
| `.../AlphaTrade/LOBS5` | `.../LOBS5` |
| `/lus/lfs1aip2/projects/s5e/quant` | `/projects/s5e/quant` |
| `/lus/lfs1aip2/projects/s5e` | `/projects/s5e` |
| Other | last 2 path components |

## Critical Rules

1. **Search ALL project dirs**: `find /projects/s5e/quant/.claude/projects/ ...` (not just current project)
2. **Exclude subagents**: `-not -path "*/subagents/*"`
3. **Full UUIDs in Resume**: Never truncate Session IDs in the resume command
4. **Identify current session**: Compare with current session's JSONL (newest + being written to). Mark it, don't provide resume command.
5. **Stream, don't load**: Never `json.load()` entire multi-MB files. Line-by-line only.
6. **Timestamps from JSONL content**: Use internal `timestamp` fields, NOT file `mtime` (mtime updates on system writes, not user activity)

## Anti-Patterns

| Pattern | Why Wrong | Correct |
|---------|-----------|---------|
| `type == "human"` | Wrong field value | `type == "user"` |
| Only searching current project dir | Misses sessions in parent/sibling dirs | Search all dirs under `~/.claude/projects/` |
| Using file mtime for "Last Active" | System writes update mtime independently | Parse last timestamp from JSONL content |
| `json.load(open(file))` | OOM on 10MB files | Line-by-line streaming |
| Truncating UUID in resume cmd | Cannot resume with partial ID | Always use full UUID |
