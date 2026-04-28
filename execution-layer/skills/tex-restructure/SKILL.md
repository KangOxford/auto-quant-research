---
name: tex-restructure
description: Task-list-driven LaTeX paper restructuring with dependency graph, fragment-then-assemble strategy, and auto commit+push to Overleaf. Trigger on "restructure paper", "reorder sections", "reorganize tex", "move sections".
version: 1.0.0
allowed-tools: Agent, Bash, Read, Edit, Write, Glob, Grep, TaskCreate, TaskUpdate, TaskList, TaskGet
alwaysApply: false
---

# LaTeX Paper Restructuring (Task-List Driven)

## When to Use

Trigger when user asks to:
- Restructure/reorganize a LaTeX paper
- Reorder sections (e.g., "put new content first")
- Move content to appendix
- Merge or split sections
- Any large-scale structural change to a multi-section .tex file

## Process

### Phase 0: Map Current Structure

1. Read the .tex file and extract ALL `\section`, `\subsection`, `\subsubsection` with exact line numbers
2. Use **Opus** model for this (not Sonnet; structure analysis requires deep understanding)
3. Create a section map table:

```
| Line | Type | Command | Label | Lines to Next |
```

4. Create `task_plan.md` with old structure -> new structure mapping
5. `git branch backup-before-restructure` (safety net)

### Phase 1: Design Task List with Dependencies

Create tasks using TaskCreate with explicit blockedBy dependencies. Key principles:

**Dependency Rules:**
- Moving content to Appendix has NO dependencies (do first)
- Promoting sections depends on Appendix moves (line numbers change)
- Section reordering is SERIAL (each move shifts line numbers)
- New content insertion depends on target section being in place
- Introduction rewrite depends on ALL section moves (needs final numbering)
- Cross-reference fix depends on everything
- Final review depends on everything

**Parallelization Strategy:**
- Appendix moves can be parallel (different regions)
- New content can be written to fragment files in parallel
- Section moves must be serial (same file, line numbers shift)

### Phase 2: Execute with Fragment-then-Assemble

For NEW content (not moves), use the Fragment strategy:

```
Fragment Writers (parallel agents) → Write to fragments/*.tex
                                           ↓
Assembler (single agent) → Insert fragments into main.tex
                                           ↓
Cross-reference fixer → Fix all \ref, \cite
```

For MOVES (existing content), work from END to BEGINNING of file:
- Moving content at L3000 before content at L500 avoids line number invalidation
- Always CUT first, then PASTE, then add cross-reference paragraph

### Phase 3: Commit Strategy

**Overleaf repos (git.overleaf.com):**
- Commit + push after EVERY phase (not just at the end)
- Other sessions/agents may be editing simultaneously
- `git pull --rebase` before each phase
- Auto commit+push every 3 minutes during long agent runs

**Non-Overleaf repos:**
- Commit after each phase
- Push only when user confirms

### Phase 4: Cross-Reference Repair

After all moves, systematically fix:
1. `\ref{sec:*}` pointing to moved sections
2. Hardcoded "Section X" text references
3. Introduction roadmap (section numbers)
4. Abstract (if it references structure)
5. Conclusion cross-references
6. Label consistency (old labels still work via `\label` in new location)

## Key Insights

1. **Work from END to BEGINNING** when moving content within a single file. This prevents line number invalidation.

2. **Fragment-then-Assemble** for new content: parallel agents write to separate files, one assembler merges. This avoids file contention.

3. **Serial section moves, parallel content creation**: Section reordering must be serial (same file), but writing new subsections can be fully parallel.

4. **Every phase = commit + push**: Especially for Overleaf repos where multiple agents compete.

5. **Backup branch before restructuring**: Always `git branch backup-before-restructure` so you can recover.

6. **Opus for structure analysis, Sonnet for grep/search**: Understanding paper structure requires the stronger model.

7. **Add cross-reference paragraphs** when moving content to Appendix: "For X, see Appendix~\ref{app:X}." Don't just delete; redirect.

## Verification

After restructuring:
1. `grep -c '\\begin{' main.tex` == `grep -c '\\end{' main.tex` (balanced environments)
2. All `\ref{}` resolve (no "??" in compiled PDF)
3. All `\cite{}` resolve
4. Section numbers are consecutive
5. No duplicate content (moved, not copied)
6. Introduction roadmap matches actual sections
7. Paragraph transitions at section boundaries are smooth

## Example Dependency Graph

```
T0: Pull + backup ──────────────────────────────────┐
  ├──→ T1: Move X → Appendix  ─┐                   │
  └──→ T2: Move Y → Appendix  ─┤                   │
                                ▼                   │
                     T3: Promote Sec N → Sec 2      │
                                │       │           │
                                │       └──→ T7: New content
                                ▼               │
                     T4: Promote Sec M → Sec 3  │
                                │               │
                                ▼               │
                     T5: Demote old → Sec 4     │
                                │               │
                                ▼               │
                     T6: Rewrite Intro          │
                                │               ▼
                     T8: Fix cross-refs ←───────┘
                                │
                     T9: Final review + push
```
