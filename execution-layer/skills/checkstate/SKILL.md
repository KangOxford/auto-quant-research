---
name: checkstate
description: Generate a comprehensive experiment status report — goal, timeline, progress, blockers, lessons, and next steps. Trigger on "checkstate", "experiment status", "what's going on", "what happened".
version: 1.0.0
allowed-tools: Bash, Read, Glob, Grep, Agent
alwaysApply: false
---

# /checkstate — Experiment State Report

Generate a structured, comprehensive status report for the current experiment or task. Reconstructs the full narrative from git history, worktrees, checkpoints, job logs, and memory.

## When to Use

- User asks "checkstate", "what's going on", "experiment status", "what happened"
- Starting a new session and need to understand current state
- After a long break, to rebuild context
- When the user asks for a summary of an experiment's progress

## Output Structure

The report MUST follow this exact 3-section structure with subsections:

```
## 1. Overall Situation
   (a) Experiment Goal — what we're trying to achieve
   (b) History — what happened before this session
   (c) Timeline — chronological phases with key events

## 2. Progress Details
   (a) Completed Steps — table of done items
   (b) Current Step — what's actively happening
   (c) Blockers — what's stuck and why

## 3. Summary & Planning
   (a) Learned Lessons — table of insights from debugging/experiments
   (b) Next Steps — prioritized action items
   (c) Future Goals — what success looks like
   (d) Git Worktrees — table of all related worktrees with branches and status
```

## Data Collection Process

Gather information from these sources (use subagents for parallel collection):

### Source 1: Git History
```bash
# In the relevant worktree(s)
git log --oneline -30                    # Recent commits
git branch --show-current                # Current branch
```

### Source 2: Worktrees
```bash
# From main repo
git worktree list 2>/dev/null | grep -i "<experiment_prefix>"
```

### Source 3: Checkpoints
```bash
# List checkpoint directories and their steps
ls <worktree>/checkpoints/              # Available checkpoints
ls <worktree>/checkpoints/<latest>/     # Steps within latest
```

### Source 4: Job History
```bash
# Recent jobs and their status
ls -lt <worktree>/logs_lobs5/training_*_node0.log 2>/dev/null | head -10
# Check for errors in recent jobs
grep "FATAL\|Error\|watchdog" <latest_log> | tail -5
```

### Source 5: Current Jobs
```bash
squeue --me -o "%.10i %.25j %.8T %.10M %.10l %.6D" 2>/dev/null
```

### Source 6: Memory System
Check `MEMORY.md` and relevant memory files for experiment context.

### Source 7: Benchmark Results
```bash
# Check for LOBbench/return-bench results
ls <pipeline>/results_<experiment_name>*/scores/ 2>/dev/null
```

## Formatting Rules

1. **Timeline**: Use ASCII art timeline with `━`, `├─`, `└─` for visual clarity
2. **Tables**: Use markdown tables for structured data (steps, lessons, worktrees)
3. **Blockers**: Mark with severity (P0 = critical, P1 = important, P2 = nice-to-have)
4. **Numbers**: Include exact values (step counts, loss values, job IDs, percentages)
5. **Code blocks**: Use for commands, file paths, and configuration snippets
6. **Language**: Main text in Chinese, tables and technical terms in English

## Example Output Skeleton

```markdown
## 1. Overall Situation

### (a) Goal
<1-2 sentences describing the experiment's purpose>

### (b) History
<Table or diagram showing the evolution of the experiment>

### (c) Timeline
<ASCII timeline with phases, key events, and dates>

## 2. Progress Details

### (a) Completed Steps
| Step | Status | Description |
|------|--------|-------------|
| ...  | Done   | ...         |

### (b) Current Step
<What's actively running or just completed, with metrics>

### (c) Blockers
| ID | Severity | Description | Suspected Root Cause |
|----|----------|-------------|---------------------|
| 1  | P0       | ...         | ...                 |

## 3. Summary & Planning

### (a) Learned Lessons
| # | Lesson | Context |
|---|--------|---------|
| 1 | ...    | ...     |

### (b) Next Steps
1. **[P0]** ...
2. **[P1]** ...

### (c) Future Goals
<What success looks like, target metrics, comparison table to fill>

### (d) Git Worktrees
| Path | Branch | Status |
|------|--------|--------|
| ...  | ...    | ...    |
```

## Key Insight

The value of checkstate is **narrative reconstruction**: turning scattered artifacts (commits, logs, checkpoints, jobs) into a coherent story. The user should be able to read the report and immediately understand:
1. WHERE we are (progress %)
2. WHY we're here (decisions that led to current state)
3. WHAT's blocking us
4. WHAT to do next

## Tips

- Use subagents (Explore type) to gather data in parallel from multiple sources
- For log analysis, always use subagents to avoid polluting main context
- Filter logs with `grep -v "sol_gpu_cost_model"` on this HPC system
- Cross-reference git commits with job IDs to build the timeline
- Check both the current worktree AND the main repo for relevant history
