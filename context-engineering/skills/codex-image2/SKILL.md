---
name: codex-image2
description: >-
  Generate publication-quality raster figures (PNG) by delegating to codex CLI's
  built-in image_gen tool (gpt-image-2 / image2). Use when the user wants to
  draw figures via codex's image-gen path, especially when sourcing content
  from a Notion page, markdown spec, or research wiki. Trigger phrases: "image-gen
  by codex", "use codex to draw figures for this page", "draw figures for this notion page using
  codex image-gen", "codex image2", "codex-image2". DO NOT use for matplotlib /
  SVG / vector deterministic diagrams — those go to fireworks-tech-graph or the
  matplotlib code-render path.
version: 1.0.0
allowed-tools: Bash, Read, Write, Edit, TaskCreate, TaskUpdate, advisor
alwaysApply: false
---

# codex-image2

Delegate figure generation to codex CLI's built-in `image_gen` tool, which calls
gpt-image-2 (a.k.a. "image2") under the user's ChatGPT login. No OpenAI API key
needed. Output lands at `~/.codex/generated_images/<session-uuid>/ig_<hash>.png`
and must be `cp`-ed to the workspace.

## When to Use

| Match | Skip |
|---|---|
| "image-gen by codex" / "codex image2" | "draw with matplotlib" |
| "draw figures for this notion/wiki/page" | "give me an SVG diagram" |
| Diffusion-style infographics, hero images, concept art | Vector / editable / programmatic figures |
| User explicitly names `codex` and/or `image2`/`gpt-image-2` | Anything where label-precision matters more than visual polish (use `fireworks-tech-graph` or matplotlib) |

**Hard rule (CLAUDE.md 2026-04-26):** if the user names `codex` and/or `image2`,
those are tool/model hard constraints. Never substitute Grok-Imagine, SD,
Midjourney, or matplotlib. First failure → search for other ways to invoke the
*same* tool, not a different tool.

## Process

### 1. Verify environment (one-shot)

```bash
which codex                         # /projects/.../miniforge3/bin/codex
codex --version                     # codex-cli 0.124.0+
codex login status                  # Logged in using ChatGPT  ← required for image_gen
ls ~/.codex/generated_images/       # exists (created on first image gen)
```

If `codex login status` says not logged in, stop and tell the user to `codex login`.

### 2. Source the content (if from a Notion page)

```python
# Recursively walk the page tree via REST API
PAGE_ID = "<from notion URL last 32 chars, dash-formatted>"
TOKEN = open("~/.notion_token").read().strip()  # required env at user
# GET /v1/pages/{id}                  → page meta
# GET /v1/blocks/{id}/children?page_size=100  + cursor pagination
# Recurse for any block where has_children: true
```

Render to a flat markdown file (`/tmp/<task>/content.md`) — codex will read it.
**Not all `child_page` blocks need to be recursed** — depth-1 traversal is usually enough.

### 3. Write structured English prompts

Create `image_gen_prompts.md` in the target dir with one section per figure:

```markdown
## fig{N}_{slug}

Prompt:
> A clean modern infographic of <subject>. <Specific layout: hub-and-spoke / vertical pipeline / horizontal timeline / 2D scatter / tiered architecture>. <List elements with EXACT text>. <Color palette spec>. White background, sans-serif, no AI-art tropes (no glowing orbs, no stock-photo people). 16:9 landscape.
```

**Critical: English only.** gpt-image-2 renders English text reliably; CJK
text often becomes garbled or tofu. Translate any Chinese labels in the source
to concise English equivalents and note this in the delivery report.

### 4. Invoke codex exec

```bash
cd <task_dir>
codex exec --full-auto --skip-git-repo-check \
  -C <task_dir> \
  --add-dir <content_dir> \
  "Use your built-in image_gen tool to produce N figures.

INPUT: ./image_gen_prompts.md (in cwd) — sections '## figN_<slug>' each contain a '> Prompt:' block.

WORKFLOW:
1. Read image_gen_prompts.md and extract the N prompts.
2. For EACH prompt sequentially (NOT parallel — preserves style consistency):
   a. Call image_gen with the exact prompt text from the '> Prompt:' block.
   b. The image saves to ~/.codex/generated_images/<session>/ig_<hash>.png.
   c. Find newest ig_*.png and cp to cwd as figN_<slug>.png.
   d. Print path + size + dimensions.
3. After all N done, run 'ls -la *.png' and verify each >50KB and is valid PNG.
4. If any figure fails, retry once. If still fails, print which one and continue.

CONSTRAINT: ONLY image_gen tool. NO matplotlib, NO code-rendering.

Work autonomously, no clarifying questions." \
  2>&1 | tee codex_run.log
```

Run with `run_in_background=true` and `timeout=1500000` (25 min). 5 figures
typically complete in ~5 min sequentially.

### 4b. Speed mode: parallel codex exec (optional, ~6× faster)

If style consistency across figures isn't critical (each figure standalone), run
N parallel codex exec processes. Wall-clock drops from ~5 min to ~60-90 s for
5 figures.

**Source-race trap**: naive parallel runs all share `~/.codex/generated_images/`
and "find newest ig_*.png" picks the global newest — 5 parallel writers race,
multiple cp can target the same file. Fix: **CODEX_HOME isolation per process**.

```bash
DIR=<task_dir>
for i in 1 2 3 4 5; do
  (
    export CODEX_HOME=$(mktemp -d -t codex-fig${i}-XXX)
    cp ~/.codex/auth.json    $CODEX_HOME/
    cp ~/.codex/config.toml  $CODEX_HOME/

    codex exec --full-auto --skip-git-repo-check \
      -c model_reasoning_effort="low" \
      -C $DIR \
      "Read image_gen_prompts.md, find section '## fig${i}_', call image_gen with that prompt's text. Then exit. Do NOT cp anything."

    SRC=$(find $CODEX_HOME/generated_images -name 'ig_*.png' | head -1)
    SLUG=$(awk -v i=$i '/^## fig/&&match($0,"fig"i"_") { sub(/^## fig[0-9]+_/,""); print; exit }' $DIR/image_gen_prompts.md)
    cp "$SRC" "$DIR/fig${i}_${SLUG}.png"
    rm -rf $CODEX_HOME
  ) &
done
wait
```

Three required pieces for parallel safety:
1. `CODEX_HOME=$(mktemp -d)` — independent codex root per process; `generated_images/` lives under it
2. **Copy auth.json + config.toml** into the temp CODEX_HOME — codex reads them on startup; missing them → "not logged in" error
3. cp source from `$CODEX_HOME/generated_images/` only — that dir holds exactly one ig_*.png (the one this process generated)

Tradeoff: parallel sessions don't share style context, so 5 figures may use
different icon sets / palettes / typography. For paper figure series where
visual consistency matters, stick with sequential (single exec).

### 5. Verify the output (do not trust agent's word)

After codex completes, **Read** at least 2-3 of the produced PNGs in Claude
Code (Read tool returns the image inline). Check:
- Subject matches prompt
- Text labels are correct (no typos / no CJK garbage)
- 2D scatters have correct point positions
- Trade-off / architecture diagrams have correct structural relationships

If a figure looks wrong, edit only that prompt section and re-run codex with
a single-figure prompt.

### 6. Deliverables

```
<task_dir>/
├── image_gen_prompts.md       # the spec (preserved for re-runs)
├── codex_run.log              # full codex stdout (debug)
├── fig1_*.png ... figN_*.png  # the figures
```

Do NOT auto-push to Notion unless user explicitly asks.

## Key Insights

1. **`~/.codex/generated_images/<session-uuid>/ig_<hex>.png`** is the codex
   image-gen save path. Invisible from `codex --help`. Each session has its own
   uuid dir. The newest `ig_*.png` is the latest output.

2. **`--full-auto --skip-git-repo-check -C <dir>`** trio: full-auto enables
   workspace-write sandbox without approvals; skip-git-repo-check allows running
   in non-git dirs; -C sets working root.

3. **`--add-dir <path>`** grants codex sandbox read access to a path outside
   `-C`. Use it to give codex the source content (e.g., `/tmp/<task>/content.md`).

4. **English-only prompts**: gpt-image-2 renders Latin alphabet cleanly but
   Chinese / Japanese / Korean text often becomes tofu boxes or corrupted
   glyphs. Always translate CJK labels in spec to English. Note this caveat
   to the user in delivery report.

5. **Sequential vs parallel — pick by style requirement**:
   - **Sequential** (single codex exec, N figures in one session): 5 figures ≈ 5
     min wall-clock. Style is consistent across figures (same icon set, palette,
     typography) because the agent shares context across calls.
   - **Parallel** (N codex exec processes via bash `&`): 5 figures ≈ 60-90 s
     wall-clock (~6× speedup). Style drift across figures — different sessions
     don't share context. **Requires CODEX_HOME isolation per process**, see
     "Speed mode" in Process step 4b. Naive parallel without isolation hits a
     source-race: all processes' "find newest ig_*.png" can pick the same
     globally-newest file across 5 racing writers.
   - Use sequential for paper figure series; use parallel for independent figures.

6. **Verify by Read**: codex agent will report "saved 5 files" — but a silent
   tool-call failure can produce a 0-byte file or skip one figure. Always
   `Read` the first 2-3 produced PNGs (`Read` tool returns image inline) before
   declaring done. Advisor lesson 2026-04-27.

7. **Two-file split (spec.md → prompts.md)**: Split the design spec from the
   actual prompts. The spec captures "what figures we want" (often Chinese,
   for the user); the prompts.md is what codex reads (English only). This
   round-trip makes future tweaks easy.

## Anti-Patterns

| Don't | Why |
|---|---|
| Substitute Grok-Imagine / SD / matplotlib when user said "codex" or "image2" | CLAUDE.md hard constraint 2026-04-26 |
| Use this skill for vector / editable diagrams | Use `fireworks-tech-graph` (SVG) or matplotlib code-render |
| Pass prompts inline as codex CLI arg | Long prompts get truncated / quoted incorrectly. Use a `prompts.md` file |
| Trust codex's "saved 5 files" report blindly | One silent failure ≠ caller knows. Always verify via Read |
| Run 5 parallel codex calls **without CODEX_HOME isolation** | Source-race: all 5 cp pick the global newest `ig_*.png`, so each process copies a figure that does not belong to it. Always isolate via `CODEX_HOME=$(mktemp -d)` per process |
| Default to parallel for paper figure series | Style drift across sessions; same font/icon/color contract is hard to enforce. Use sequential when visual consistency matters |
| Use Chinese labels in prompts | gpt-image-2 CJK rendering is unreliable; translate to English first |

## Verification

The skill worked when:
- All N expected `figN_*.png` files exist in target dir
- Each is a valid PNG (>50KB, openable by `file` or PIL)
- Read tool on first 2-3 figures shows the requested subject + correct labels
- No CJK tofu boxes in any rendered text

## Related Skills

- `fireworks-tech-graph`: deterministic SVG diagrams via rsvg-convert. Use when
  vector / editability matters more than visual polish.
- `notion-push-via-rest`: push the generated PNGs to a Notion page via REST API
  (use as follow-up if user asks).
- `notion-auto-sync-md`: hook-based markdown→Notion sync. Different layer.
- `frontend-design`: production-grade frontend visuals. Different stack.

## Provenance

Extracted 2026-04-27 from a session where the workflow was:
- Read Notion `auto wiki` page (id `34f12c45...8ca8`, 428 blocks, 10 child pages)
- Wrote 5 detailed English image-gen prompts
- Single codex exec call → 5 PNGs (~1MB each, 1672×941, 16:9)
- Verified all 5 via Read; no retries needed; total wall-clock ~5 min

codex CLI version verified: 0.124.0 with `model = "gpt-5.5"`, `xhigh` reasoning.
