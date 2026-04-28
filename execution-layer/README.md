# Claude Code Context Engineering

This folder contains the Claude Code (the AI coding-assistant CLI from Anthropic) configuration that powers AlphaZero's Execution Layer. It is published here as a complete, reproducible reference: anyone wanting to stand up a similar autonomous-research system can clone this folder, drop it into their `~/.claude/`, adapt the paths and project-specific rules, and have a working starting point.

The unifying theme across all of these files is **context engineering**: the deliberate practice of shaping what the LLM sees on every turn so that it acts predictably, safely, and effectively across a long-horizon multi-step task. Where a single chat with Claude is a one-shot, autonomous research replication is a marathon, and the marathon needs scaffolding.

## What is in this folder

```
context-engineering/
├── CLAUDE.md                     Global instructions loaded into every session
├── CRITICAL_LESSONS.md           Permanent lessons learned the hard way
├── settings.json                 Runtime config: permissions, hooks, env, status line
├── notion-sync-manifest.json     Which markdown files auto-sync to which Notion page
├── statusline-command.sh         Custom status line renderer
├── statusline-session.sh         Per-session metadata for the status line
├── skills/                       Reusable, on-demand procedures (one folder per skill)
├── hooks/                        Event-driven shell scripts (PostToolUse, Stop, etc.)
├── agents/                       Subagent definitions
└── commands/                     Slash commands
```

Forty-plus skills cover everything from job submission and benchmarking to documentation push, image generation, file-system safety, and translation. Hooks intercept events such as a tool call finishing, a session ending, or a markdown file being written, and translate them into side effects (auto-sync to Notion, archive previous version, run a linter, etc.).

## What is intentionally **not** in this folder

The published copy filters out everything that is either a secret, transient, or scoped to one user's local state:

- `~/.claude/.credentials.json` and any other credential files (Claude Code authentication, API keys)
- `~/.notion_token`, `~/.git-credentials`, HuggingFace tokens, and any other API tokens
- `~/.claude/projects/` (full chat transcripts, contains every conversation ever held)
- `~/.claude/history.jsonl`, `*.log`, `paste-cache/`, `cache/`, `debug/`, `file-history/` (session metadata, logs, ephemeral state)
- `~/.claude/session-*` (per-session data)
- `~/.claude/plugins/` (third-party plugins with their own licensing)
- `~/.claude/backups/`, `~/.claude/bin/`, `~/.claude/chrome/`, `~/.claude/ide/`, etc. (local-machine setup)
- `~/.claude/.mcp.json` and `mcp-needs-auth-cache.json` (may contain server URLs and auth state)

A grep across the published files for common token formats (GitHub PATs, HuggingFace tokens, Anthropic keys, OpenAI keys, AWS / GCP keys, Notion tokens) confirms that no secrets remain.

## How to read this folder

Three suggested entry points:

1. **Start with `CLAUDE.md`**. This is the single largest artifact in the folder and the most important. It encodes the design principles, hard rules, communication conventions, and many specific lessons-learned that every Claude Code session inherits when it opens. The patterns to look for: question-mode versus task-mode, decision layer versus execution layer, the rules for using subagents, and the conventions for writing code.

2. **Browse a few skills**. Each `skills/<name>/SKILL.md` is a focused, declarative description of one reusable procedure. Pick one that sounds familiar (for example `find-wandb`, `submit-job`, `bench`, `notion-push-via-rest`) and read it end to end. The skills are designed so that an LLM can read the SKILL.md once and immediately know how to perform the task; humans benefit from the same clarity.

3. **Skim `hooks/`**. Hooks are how Claude Code is wired into the rest of the user's environment. Each hook is a short shell or Python script that runs automatically on a particular event. The interesting ones here include the markdown-to-Notion sync hook, the prompt-translation hook, and the auto-approve hook for editing the user's own configuration.

## Why publish this

Context engineering is a young craft. Most of the published material is either single tweets ("here is the one prompt that fixed my agent") or extremely abstract ("you should align your AI"). What is missing in the middle is concrete: a complete, working configuration that solves a real problem from end to end, with all of its rules, edge cases, and embarrassing scars.

The configuration in this folder is the result of approximately 5 months of running Claude Code daily on real research code, accumulating rules every time something went wrong. It is far from polished. Many of the rules will not apply outside of HPC, or outside of finance microstructure research, or outside of one specific user's preferences. But the *shape* of it, the way rules and skills and hooks compose, is general; that is the part worth copying.

## License

MIT, same as the rest of the auto-quant-research repository.

## Contact

Found a leaked secret in here despite the filtering? Open an issue immediately so it can be redacted.
