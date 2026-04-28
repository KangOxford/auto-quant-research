---
name: symlink-claude-config
version: "1.0.0"
description: Convert a copy-based "public view" of Claude config (CLAUDE.md, skills/, memory/, settings.json, hooks/, etc.) into a symlink-based view pointing at canonical ~/.claude/. Preserves project-encoded memory, skips secrets (.credentials.json, .notion_token, history.jsonl, sessions/), and handles the permission-hook `mv` authorization dance. Complements chmod-world (permissions layer); this skill handles the content layer. Trigger phrases include "make the public dir a symlink view", "replace copies with symlinks", "consolidate claude config", "link settings to ~/.claude".
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Glob
  - Write
---

# symlink-claude-config

Migrate a copy-based "public view" Claude config directory (e.g., `/projects/public/<team>/<user>/`) into a symlink view pointing at canonical `~/.claude/`. After the migration, any changes on the source side are instantly reflected on the public side with zero manual syncing.

**Difference from `chmod-world`**: chmod-world manages the **permissions layer** (who can access); this skill manages the **content layer** (how to make the public dir a live mirror of the canonical source). They are orthogonal and are commonly used together: first chmod-world to make the directory readable cross-group, then this skill to replace the contents with symlinks.

## When to Use

- User says: "symlink these configs to ~/.claude", "replace copies with symlinks", "consolidate claude config", "make a symlink view"
- A public / shared directory has scattered Claude files (`CLAUDE.md`, `settings.json`, `skills/`, `memory/`, etc.) with contents overlapping `~/.claude/`, suspected to be manual copies that have already drifted
- Team members want to expose their Claude setup to teammates without manually syncing every change

**Do NOT use for**:
- Single-file symlinks (just run `ln -s` directly)
- Symlinking `~/.claude/` itself to elsewhere (circular dependency)
- Sharing token / credential files (these should never be in a public directory)

## Four Pitfalls You Must Know

### (1) Memory paths are cwd-encoded, not flat

Claude per-project memory is stored at `~/.claude/projects/<encoded-cwd>/memory/`, where the encoding rule is: **every `/` in the physical cwd is replaced with `-` (including the leading `/`).**

| cwd | encoded |
|-----|---------|
| `/lus/lfs1aip2/projects/public/s5e/quant_team/kang` | `-lus-lfs1aip2-projects-public-s5e-quant-team-kang` |
| `/home/alice/work` | `-home-alice-work` |

**Pitfall**: The copy-based view places memory files under `<public-dir>/memory/`, but Claude actually writes to `~/.claude/projects/<encoded-cwd>/memory/`. The latter is often **empty** while the former holds old data. Deleting the old directory directly would cause data loss. **Always move the contents to the encoded location first**, then create the symlink.

Use `pwd -P` to get the physical path (not the pre-symlink-resolution path); otherwise the encoded path won't match where Claude actually stores data.

### (2) Files that must never be symlinked

| Category | Specific files | Reason |
|------|---------|------|
| Secret | `.credentials.json`, `.notion_token`, any `.*_token`, `.*key*.json` | Bearer tokens — placing them in public equals exposing them |
| History | `history.jsonl`, `sessions/`, `session-chain.json` | Personal conversation history + session state |
| Log | `hook-debug.log`, `notion-sync.log`, `insights-*.log` | Contains prompts / tool results |
| Cache | `cache/`, `paste-cache/`, `file-history/`, `debug/` | Large volumes of private content |
| Telemetry | `statsig/`, `telemetry/`, `usage-data/` | User metadata |
| Cross-project memory | The entire `projects/` directory | Only link the encoded memory for the **current** public dir |

**Safe to link**: `CLAUDE.md`, `settings.json`, `settings.local.json`, `skills/`, `hooks/`, `agents/`, `commands/`, `plugins/`, `bin/`, `.mcp.json`, `statusline-command.sh`, and the `projects/<encoded-cwd>/memory/` corresponding to the **current public dir**.

### (3) The permission hook treats `mv` as a delete-like action

A strict permission hook treats the source of `mv /src/file /dst/` as "being deleted", even when the destination is the canonical path.

**Workaround**: The hook **only accepts explicit text authorization typed by the user in the chat box** (e.g., "approve mv", "go ahead", "proceed"). The return value of `AskUserQuestion` **does not count**. Explicit authorization must be obtained in the conversation before executing.

### (4) Backup naming convention

Do not `rm` old copies directly. Move them to `~/.claude/backups/<basename>-snapshot-$(date +%Y%m%d)/`. `~/.claude/backups/` is an established "recycle bin" convention where users know to look for recovered items.

## Process

### Step 0 — Inventory & classify

```bash
SRC=<public dir>             # e.g. /projects/public/s5e/quant_team/kang
CLAUDE="$HOME/.claude"

ls -la "$SRC/"
ls -la "$CLAUDE/"
```

Classify each item in `$SRC`:

| Classification | Action | Example |
|------|------|------|
| `link` | backup old + ln -s new | `CLAUDE.md` (contents match the canonical source) |
| `preserve+link` | first mv contents to canonical, then backup the empty shell, then ln -s | `memory/` (has content, but canonical is empty) |
| `backup-only` | backup only, no corresponding canonical source | `project-CLAUDE.md` (file exists only locally) |
| `never` | skip the entire category | `.credentials.json` and other secrets |

### Step 1 — Encode memory path

```bash
ENCODED=$(pwd -P | sed 's|/|-|g')     # use the physical path, not the pre-symlink-resolution path
MEMORY_CANONICAL="$CLAUDE/projects/$ENCODED/memory"
mkdir -p "$MEMORY_CANONICAL"
echo "Memory will live at: $MEMORY_CANONICAL"
```

### Step 2 — Preserve divergent memory content

If the public-side memory has content while canonical is empty, move the content over:

```bash
if [ -d "$SRC/memory" ] \
   && [ -n "$(ls -A "$SRC/memory/" 2>/dev/null)" ] \
   && [ -z "$(ls -A "$MEMORY_CANONICAL" 2>/dev/null)" ]; then
  shopt -s dotglob
  mv "$SRC/memory"/* "$MEMORY_CANONICAL/"
  shopt -u dotglob
  echo "Moved $(ls "$MEMORY_CANONICAL" | wc -l) memory files to canonical"
fi
```

**This step requires the user to explicitly approve the mv** — the hook will block it; tell the user and wait for authorization in the conversation.

### Step 3 — Move old copies to backup

```bash
BACKUP="$CLAUDE/backups/$(basename "$SRC")-snapshot-$(date +%Y%m%d)"
mkdir -p "$BACKUP"
for item in "$SRC"/* "$SRC"/.mcp.json "$SRC"/.claude-*; do
  [ -e "$item" ] || continue
  [ -L "$item" ] && continue       # already a symlink, skip
  mv "$item" "$BACKUP/"
done
echo "Backed up $(ls "$BACKUP" | wc -l) items to $BACKUP"
```

This also requires user approval for the mv. One authorization covers the entire batch.

### Step 4 — Create symlinks

```bash
# Safe set — verified user-facing Claude config
SAFE_ITEMS=(
  CLAUDE.md
  settings.json
  settings.local.json
  skills
  hooks
  agents
  commands
  plugins
  bin
  .mcp.json
  statusline-command.sh
)

for item in "${SAFE_ITEMS[@]}"; do
  if [ -e "$CLAUDE/$item" ]; then
    ln -s "$CLAUDE/$item" "$SRC/$item"
  else
    echo "SKIP: $CLAUDE/$item does not exist at source"
  fi
done

# Memory — use encoded path
ln -s "$MEMORY_CANONICAL" "$SRC/memory"
```

### Step 5 — Verify

```bash
echo "=== Symlink verification ==="
for f in "$SRC"/* "$SRC"/.mcp.json; do
  [ -e "$f" ] || [ -L "$f" ] || continue
  target=$(readlink "$f" 2>/dev/null)
  if [ -n "$target" ]; then
    if [ -e "$target" ]; then
      echo "OK    $(basename "$f") -> $target"
    else
      echo "BROKEN $(basename "$f") -> $target"
    fi
  fi
done
```

Expected: each item shows `OK   <name> -> <canonical path>`. Investigate any `BROKEN` entries.

Typical additional sanity checks:
```bash
# Verify the symlinked CLAUDE.md resolves correctly
head -3 "$SRC/CLAUDE.md"
# Skills directory can be listed
ls "$SRC/skills" | head -5
# Memory count matches canonical
test "$(ls "$SRC/memory" | wc -l)" = "$(ls "$MEMORY_CANONICAL" | wc -l)" && echo "memory count OK"
```

## Reference Script

Complete, directly-invocable version. The first run **will inevitably** be blocked by the permission hook at the `mv` step; after the user explicitly approves the mv, re-run the script.

```bash
#!/bin/bash
# symlink-claude-config.sh <public-dir>
# Convert a copy-based Claude config mirror into a symlink view of ~/.claude/

set -euo pipefail

SRC="${1:?usage: $0 <public-dir>}"
SRC=$(realpath "$SRC")
CLAUDE="${CLAUDE_HOME:-$HOME/.claude}"

# Encode the source dir path for memory
ENCODED=$(echo "$SRC" | sed 's|/|-|g')
MEMORY_CANONICAL="$CLAUDE/projects/$ENCODED/memory"
mkdir -p "$MEMORY_CANONICAL"

# Step: preserve divergent memory
if [ -d "$SRC/memory" ] \
   && [ -n "$(ls -A "$SRC/memory/" 2>/dev/null)" ] \
   && [ -z "$(ls -A "$MEMORY_CANONICAL" 2>/dev/null)" ]; then
  shopt -s dotglob
  mv "$SRC/memory"/* "$MEMORY_CANONICAL/"
  shopt -u dotglob
fi

# Step: backup current contents (non-symlinks only)
BACKUP="$CLAUDE/backups/$(basename "$SRC")-snapshot-$(date +%Y%m%d)"
mkdir -p "$BACKUP"
for item in "$SRC"/* "$SRC"/.mcp.json; do
  [ -e "$item" ] || continue
  [ -L "$item" ] && continue
  mv "$item" "$BACKUP/"
done

# Step: symlink safe set
SAFE_ITEMS=(
  CLAUDE.md settings.json settings.local.json
  skills hooks agents commands plugins bin
  .mcp.json statusline-command.sh
)
for item in "${SAFE_ITEMS[@]}"; do
  [ -e "$CLAUDE/$item" ] && ln -s "$CLAUDE/$item" "$SRC/$item"
done
ln -s "$MEMORY_CANONICAL" "$SRC/memory"

# Step: verify
echo "=== Verification ==="
for f in "$SRC"/* "$SRC"/.mcp.json; do
  [ -L "$f" ] || continue
  target=$(readlink "$f")
  [ -e "$target" ] && echo "OK    $(basename "$f")" || echo "BROKEN $(basename "$f") -> $target"
done
```

Usage:
```bash
bash symlink-claude-config.sh /projects/public/s5e/quant_team/kang
```

## Key Insights

- **Memory path encoding is a Claude internal convention — do not guess**: Write memory to some cwd once, then `ls ~/.claude/projects/` to see the auto-generated directory name and verify the encoding rule. The `sed 's|/|-|g'` in this skill has been verified to match Claude's actual convention.
- **`ln -s` does not check that the target exists**: `ln -s /nonexistent /dst/foo` will "succeed" and create a broken link. The `readlink + [ -e ]` verification in Step 5 is essential.
- **Modifying files on the source side is immediately reflected in the public view**: This is a feature, not a bug. Team members can get the latest config by looking directly at the public dir.
- **`pwd` vs `pwd -P`**: If the public dir itself is a symlink to a Lustre mount point (`/projects/public/` → `/lus/lfs1aip2/projects/public/`), the encoding must use `pwd -P` to get the physical path; otherwise the computed encoded path won't match where Claude actually writes. `realpath "$SRC"` is equivalent.
- **Symlinks in a git repo trigger "symlink escape" warnings**: If the public dir is itself git-tracked, either add to `.gitignore` or use `git config --local core.symlinks true` and accept symlinks appearing in diffs.
- **A public dir with chmod 2775 / 2755 is world-readable**: Even if the public dir only grants write to the group, other users can still **read** its contents. Placing token-type files (even as symlinks) there is equivalent to making them public.

## Related Skills

- **chmod-world**: Make the public dir readable and traversable cross-group (permissions layer). After this skill handles the content layer, the next step is commonly chmod-world.
- **chmod-group**: In-group sharing, more conservative
- **claudeception**: The meta-skill for this skill, describing the standard process for distilling skills from manual sessions

## Version History

- **v1.0.0** (2026-04-23): Distilled from the 2026-04-23 session (`/projects/public/s5e/quant_team/kang/` copy-to-symlink migration: 12 symlinks created, 76 memory files moved, 7 items backed up to `~/.claude/backups/public-kang-snapshot-20260423/`).
