---
name: claudeception
description: Automatically extract reusable skills from work sessions. Evaluates current work for extractable patterns, checks for duplicates, and creates new SKILL.md files.
version: 3.0.0-adapted
allowed-tools: Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Skill
alwaysApply: false
---

# Claudeception: Continuous Learning Skill

You are an AI assistant with the ability to learn from your work by creating reusable skills. After completing meaningful work, evaluate whether the experience contains extractable knowledge worth preserving as a skill.

## When to Extract

After completing a task, evaluate against these **4 quality gates** — ALL must pass:

| Gate | Question | Fail Example |
|------|----------|--------------|
| **Reusable** | Will this help in future, different contexts? | One-off data migration script |
| **Non-trivial** | Does it encode insight beyond "read the docs"? | "Use `git commit -m`" |
| **Specific** | Is it concrete enough to act on? | "Write good code" |
| **Verified** | Was the solution confirmed working? | Untested hypothesis |

## Anti-Patterns (Do NOT Extract)

- **Over-extraction**: Not every task deserves a skill. Most don't.
- **Documentation duplication**: If it's already in CLAUDE.md, learned_lessons.md, or official docs, skip it.
- **Vague descriptions**: "Handle errors properly" is useless.
- **Unverified solutions**: Only extract patterns that actually worked.
- **Stale knowledge**: Don't extract version-specific workarounds that will rot.

## Extraction Process

### Step 1: Check for Existing Skills

Before creating, search for duplicates:

```
Glob: ~/.claude/skills/*/SKILL.md
Grep: <key-concept> in ~/.claude/skills/
```

If a similar skill exists → **update it** instead of creating a new one.

### Step 2: Evaluate Quality Gates

Run through the 4 gates above. If ANY gate fails, **stop**. Do not extract.

### Step 3: Research (Optional)

If the skill involves external tools/APIs, verify current best practices:
- Check official documentation
- Confirm the approach is not deprecated

### Step 4: Create Skill File

Write to `~/.claude/skills/<skill-name>/SKILL.md`:

```markdown
---
name: <kebab-case-name>
description: <one-line description — specific enough to match against future contexts>
version: 1.0.0
allowed-tools: <comma-separated list of tools this skill needs>
alwaysApply: false
---

# <Skill Title>

## When to Use
<Specific trigger conditions>

## Process
<Step-by-step instructions>

## Key Insights
<The non-obvious knowledge this skill encodes>

## Verification
<How to confirm the skill worked>
```

### Step 5: Report

After creating/updating a skill, report:
- Skill name and path
- What triggered the extraction
- Which quality gates it passed and why

## Skill Lifecycle

```
Creation → Refinement (update on new insights) → Deprecation (mark outdated) → Archival (delete)
```

## Integration with Existing Systems

This skill complements (does NOT replace):
- **CLAUDE.md**: Hard rules and project config (Level 1)
- **Memory system**: Cross-session context (Level 2)
- **learned_lessons.md**: Chronological experience log

Claudeception is **Level 3**: abstracted, reusable, auto-triggered patterns.

## Language

Skill files should be written in English (for tool matching), but key insights and comments can include Chinese annotations where helpful for the user.
