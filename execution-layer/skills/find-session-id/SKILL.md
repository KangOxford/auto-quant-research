---
name: find-session-id
user-invocable: true
description: Find a historical Claude Code session by user-quoted text. Trigger on "find session", "find session id", "which session", "findSessionId".
arguments: "<quoted text> — the text snippet from the session to find"
version: 3.6.0
---

# /find-session-id — Find Historical Session by Quoted Text

Locate the JSONL session file that produced user-quoted output.

## Token Budget: 1 Bash Call, ~6 Line Output

This skill MUST complete in 1 Bash call for the happy path. If you're about to make a 3rd call, STOP and output what you have.

**Output discipline**: print exactly 6 labeled lines — Session ID, Size, Modified, Matches, Path, Resume. Do NOT print the full `ls -l` row (perms, owner, group, ~200 chars of noise); the 6 structured fields carry everything the user needs to identify, inspect, and trust the answer (Matches = why this session won over others).

## The Two Rules (applied in order)

1. **EXCLUDE active sessions.** Any JSONL modified within the last 30 seconds is almost certainly being written to *right now* — either the session running this skill, or a sibling session the user has open. The user asked you to find the *origin* of a quote, not to return a session that's actively echoing it.
2. **HIGHEST count-per-file wins = origin session.** Among non-active matches, pick the file where the key appears the MOST TIMES. Size is a weak tiebreaker only.

**Why count, not size (superseded the old LARGEST rule on 2026-04-13):** when a user pastes an assistant transcript into another session (e.g., a prior long conversation they had open) and asks "find this session," the quoted text is present in THREE places:
- **Origin** (medium-sized, generated the key 20+ times via tool output / assistant messages that referenced the URL / checkpoint path / etc.)
- **Paste-into** session (possibly HUGE, but the key appears only 1–4 times because user pasted once)
- **Current** session (mtime < 30s — filtered by rule 1)

Size-based ranking picks the paste-into session (wrong). Count-based ranking picks the origin, which naturally has the highest density of the key because the tools/assistant repeated it throughout their original workflow. Observed case: origin=23 hits, paste-into=4 hits, current=21 hits filtered.

**Why count can still fail — the provenance trap (2026-04-14):** count beats size, but count can be gamed by a *follow-up find-session* that repeatedly greps the original key. Case study: user pasted a snippet where the assistant was creating a `multi-node-jax-ffi-debug` skill; picking that skill name as KEY gave a wrong session (a later "help me find the session that created this skill" session) with count=10, because that session's tool calls echoed the skill name many times during its own grep workflow. The real origin had count=1 when queried with a key that only the origin session would have emitted: a bash command regex `local_device_ids|slurm.*gpu` that was literally typed in the origin's tool_input. Rule: prefer **behavior-trace keys** (bash command substrings, unique CLI flags, one-off file paths) over **topic-name keys** (skill names, module names, concept labels). The former can only appear in sessions that ran the trace, the latter can appear in any session that searched for the topic.

**Fallback if exclusion empties the result:** some tasks *do* want the current session (e.g., the user asks "what session am I in?"). If mtime-exclusion leaves zero matches, drop the filter and return the highest-count overall match, and flag the answer with "active session" so the user sees why.

## Algorithm (Single Pipeline)

```
Step 1: Extract ONE high-selectivity key from quote
        Priority: W&B run ID > Job ID > commit hash > UUID > unique error string
        ONLY ONE KEY. Never search for two.
Step 2: Run the single pipeline (see below)
Step 3: Output 5 labeled lines (ID / Size / Modified / Path / Resume). Done.
```

## The Single Pipeline (1 Bash Call)

```bash
KEY="<KEY>"
NOW=$(date +%s)
# For each match: count occurrences, plus size/mtime/path
DATA=$(grep -lF "$KEY" ~/.claude/projects/*/*.jsonl 2>/dev/null | while read F; do
    CNT=$(grep -cF "$KEY" "$F")
    stat -c "$CNT %s %Y %n" "$F"
done)
# Exclude active sessions (mtime within last 30s)
FILTERED=$(echo "$DATA" | awk -v c=$((NOW - 30)) '$3 < c')
NOTE=""
if [ -z "$FILTERED" ]; then
    FILTERED="$DATA"
    NOTE="  (active session — no quiescent match)"
fi
# Sort by count DESC (primary), size DESC (tiebreak)
F=$(echo "$FILTERED" | sort -k1,1rn -k2,2rn | head -1)
if [ -n "$F" ]; then
    CNT=$(echo "$F" | awk '{print $1}')
    SIZE=$(echo "$F" | awk '{print $2}')
    MTIME=$(echo "$F" | awk '{print $3}')
    FPATH=$(echo "$F" | awk '{print $4}')
    ID=$(basename "$FPATH" .jsonl)
    SIZE_MB=$(awk "BEGIN {printf \"%.2f\", $SIZE/1024/1024}")
    MTIME_STR=$(date -d @$MTIME '+%Y-%m-%d %H:%M:%S')
    printf "Session ID: %s%s\nSize:       %s MB (%s bytes)\nModified:   %s\nMatches:    %s occurrences of key\nPath:       %s\nResume:     claude --resume %s\n" \
           "$ID" "$NOTE" "$SIZE_MB" "$SIZE" "$MTIME_STR" "$CNT" "$FPATH" "$ID"
else
    echo "NOT FOUND - try a different key from the quote"
fi
```

Wide search across ALL project dirs → for each matching file, count `grep -c` occurrences and capture size/mtime/path → **filter out files modified within the last 30s** (the currently-active session writing as we run this) → sort by count desc (size desc as tiebreak) → take top → format and print 6 lines. If the filter empties the set, fall back to all matches and tag the answer as "active session." The `Matches:` field now makes the choice auditable: the user sees why this particular session won (e.g., 23 hits vs 4 in the runner-up).

**Why `grep -lF` (not `-rl`)?** `-F` = fixed string (literal match). Faster than regex, and safe for keys containing `.`, `[`, `*`, `(` that would otherwise need escaping. `-l` = filenames only. The shell glob `*/*.jsonl` already enumerates files, so recursion is unnecessary.

**Why `stat -c '%s %Y %n'` instead of `ls -lhS`?** `ls -l` outputs 7 columns (~250 chars/line). `stat -c '%s %Y %n'` outputs 3 columns (size + epoch-mtime + path, ~80 chars/line). Identical sort behavior on size (epoch int in col 2 doesn't destabilize `sort -rn`'s leading-key behavior), ~3x less context cost, and the epoch mtime lets us format a human-readable timestamp in one `date -d @N` without a second `stat` call.

**Why the `FPATH` variable, not `PATH`?** `PATH` is the shell's executable search variable — overwriting it inside a script breaks every subsequent command (`awk`, `basename`, `date` all become "not found"). Rename to `FPATH` to avoid shadowing.

**Why no project-key narrowing?** Inferring `~/.claude/projects/<KEY>` requires flattening cwd correctly (e.g., `tasks/` subdir adds `-tasks` suffix — easy to miss). High-selectivity keys (W&B IDs, commit hashes) are globally unique anyway, so wide search costs ~nothing extra and removes a whole class of bugs.

**Why `2>/dev/null` everywhere?** Stale dir cache can list deleted JSONLs. Without suppression, `grep`/`xargs` errors pollute stdout and break downstream parsing (`head -1` may return error text instead of a filename).

**Why `xargs -r` + `[ -n "$F" ]` guard (CRITICAL, observed 2026-04-13)?** Without `-r`, an empty grep result still triggers `xargs` to run its command (with `-I{}` it runs once with `{}` literal as arg → silent stat error → empty output). Then `basename "" .jsonl` returns `.` → corrupts output to `Session ID: .` and `Resume: claude --resume .`. The `-r` (GNU extension) skips invocation when stdin is empty, and the `[ -n "$F" ]` guard handles the empty case explicitly with a NOT FOUND message instead of garbage.

**Why a 30-second cutoff (not 5s or 5min)?** The current session's JSONL is appended on every tool call / user turn / assistant token stream — between the grep and the following awk, mtime is typically 0–5 seconds old, but can stretch if the harness queued writes. 30 seconds is long enough to catch any reasonable flush jitter yet short enough that a "quiet" origin session from even 1 minute ago still wins. If two Claude sessions are running in parallel, both get filtered and the fallback kicks in — which is the correct behavior (the user's search is ambiguous and the flag tells them so).

## Fallback (Only If Pipeline Returns Empty)

If the single pipeline returns 0 results, THEN (and only then) try ONE of:
- A different key from the quote (likely the first key wasn't actually in the JSONL — e.g., it was generated post-message)
- Loosen the pattern (e.g., partial UUID instead of full)

This is your 2nd (and final) Bash call.

## Decision Tree

```
grep -lF <KEY> across all projects → stat (size, mtime, path)
  → filter mtime >= now-30s (drop the active session)
  → sort -rn by size → head -1
     ├─ 0 matches overall                → "NOT FOUND" → Fallback: different key (Call 2, final)
     ├─ 0 after filter, >0 overall       → fallback to full set, flag "active session"
     ├─ 1 after filter                   → print 5 lines. Done.
     └─ 2+ after filter                  → head -1 took the largest quiescent. Done.
```

## Output Format

Exactly 6 labeled lines, aligned with a single space of padding after the longest label:

```
Session ID: <UUID>
Size:       <X.XX> MB (<N> bytes)
Modified:   <YYYY-MM-DD HH:MM:SS>
Matches:    <N> occurrences of key
Path:       <absolute path to .jsonl>
Resume:     claude --resume <UUID>
```

Rationale for each field:
- **Session ID** — the discriminator, what the user actually asked for.
- **Size** — size as a sanity check (too small → subagent fragment; unexpectedly large → pasted-into session).
- **Modified** — absolute timestamp; useful when the user has multiple sessions from the same day and wants to cross-reference with their own memory / calendar.
- **Matches** — why *this* session won. High count = origin-like density; low count (1–5) = either a minor mention or a paste artifact. The user can audit the ranking decision.
- **Path** — direct handle for `Read` / `grep` on the JSONL without re-deriving the project-key flatten rules.
- **Resume** — paste-and-go command; closes the loop from "found it" to "using it".

Do NOT expand beyond these 6 fields (owner, perms, project-key, etc. are all derivable and add noise).

## Anti-Patterns (NEVER DO)

| Waste Pattern | Why It's Wrong | Token Cost |
|--------------|----------------|------------|
| Search for 2+ keys in parallel | One high-selectivity key is enough | 2x calls |
| Cross-reference analysis (child refs parent?) | Size rule already handles this | 3-5x calls |
| Role/type JSON structure analysis | Zero discriminative value | 2x calls |
| Narrowing to inferred `~/.claude/projects/<KEY>` first | Cwd-flatten rules (`tasks/` → `-tasks` suffix) easy to get wrong; high-sel key already unique globally | 2x calls (then fallback) |
| `ls -t \| head -1` for current-session exclusion | Stale dir cache lists deleted files → grep errors corrupt pipeline | Whole pipeline misfires |
| `grep` without `2>/dev/null` | Error lines pollute stdout, get piped into `xargs ls`, break `head -1` | Misparse the answer |
| `xargs` without `-r` | Empty grep result still triggers stat → empty `$F` → `basename ""` returns `.` → garbage output `Session ID: .` | Wrong answer with no error |
| Print full `ls -l` row (perms/owner/date/name in one line) | ~200 chars of irrelevant columns; the 5 labeled fields already carry size/mtime/path structured | Output bloat |
| Use `PATH` as a local var name (shadows `$PATH`) | After `PATH=$(...)`, the shell loses its executable search path; `awk`/`date`/`basename` become "command not found" | Whole pipeline silently produces blank fields |
| "Verify" the result with content checks | Trust the size rule | 2-3x calls |
| Test the NOT FOUND path by echo-ing a unique string in the test command | The string itself gets logged into the live JSONL → grep finds it → false positive. Use a string read from a file (never echo) instead. | Wastes a debug cycle chasing a phantom bug |
| Pick topic names (skill / module / package / concept) as KEY when a bash-command-substring or SLURM ID is available in the quote | Topic names appear in **any** session that grep'd for them, including later find-session sessions. Count-based ranking then picks the polluting session, not origin. 2026-04-14 case: `multi-node-jax-ffi-debug` → wrong session (count=10, polluted by a follow-up find-session); `local_device_ids\|slurm.*gpu` → correct origin (count=1, only the session that ran that bash command had it). | Wrong answer returned with high confidence |

**Root cause of waste: not trusting the size rule + over-engineering the search scope.** If you wrote "largest = main session, always" then ACT on it. Don't spend 5 calls verifying what 1 call already told you, and don't pre-narrow the search scope when a wide grep on a unique key costs the same.

## Key Selection Priority

Two dimensions matter: **selectivity** (how globally unique) and **provenance** (origin-only trace vs discussable topic). Both must be high. A skill name is high-selectivity but low-provenance: any session that grep'd for it also matches. Prefer keys that only the origin's tools/commands would have emitted.

### Behavior traces (preferred — origin-only)

| Key Type | Selectivity | Example |
|----------|------------|---------|
| SLURM Job ID | Very high | `j3500502` |
| Commit hash (7+ chars) | Very high | `8a14f6a2` |
| W&B run ID | Very high | `u4bo1r13` |
| Bash command substring (regex literals, unique flags, one-off paths) | Very high | `local_device_ids\|slurm.*gpu`, `CURTAIL_EPOCHS=300 sbatch` |
| UUID fragment | High | `d3a2335a` |
| Specific runtime error message | Medium-High | `BatchTracer no __dlpack_device__` |

### Topic names (avoid unless no trace available — pollution risk)

| Key Type | Why risky | Example |
|----------|-----------|---------|
| Skill / module / package name | Later find-session sessions echo it during their own greps, inflating count | `multi-node-jax-ffi-debug`, `flash-attention` |
| Generic concept | Matches too many unrelated sessions | `smoke test`, `KDA`, `debug` |
| Project-level jargon | Shared across many sessions within the same project dir | `GDN`, `scaling law` |

Pick the FIRST behavior-trace key you see. Only fall back to a topic-name key if no behavior trace is available, and expect to verify the result by size/mtime. Do not collect multiple keys.
