#!/usr/bin/env bash
# Claudeception activator hook
# Runs after every UserPromptSubmit to remind Claude to evaluate
# whether the current work session produced extractable knowledge.

cat << 'HEREDOC'
[Claudeception Reminder] After completing the current task, briefly evaluate:
- Did this work involve a non-obvious pattern, debugging insight, or reusable technique?
- Would a skill file help in future similar situations?
- Does this knowledge already exist in CLAUDE.md, learned_lessons.md, or existing skills?
If YES to first two and NO to third → invoke Skill(claudeception) to extract.
If unsure → skip. Under-extraction is better than over-extraction.
HEREDOC
