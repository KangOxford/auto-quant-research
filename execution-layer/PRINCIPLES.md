# Context Engineering — Common Principles

A living document. The goal is to capture the small set of operational rules that, in our experience, separate a chaotic AI-assisted workflow from a productive one. Anyone is welcome to add a principle, refine an existing one, or leave a comment in the Notion mirror of this page.

## Principle 1 — Multi-agent dispatch: parallelize within a problem, never across problems

**(a) When researching a single problem, dispatch parallel subagents to handle the multiple tasks inside that problem at the same time.** A research replication has many independent sub-questions: data ingestion, world-model interface, regression specification, figure generation, robustness checks. Each is a self-contained piece of work that does not depend on the others' final output. Running them concurrently is a near-free speedup, because the wall-clock cost of N parallel subagents is bounded by the slowest one, not by their sum.

**(b) Avoid running multiple parallel agents on unrelated topics simultaneously.** This is the more important half of the principle, because the failure mode is non-obvious. When two or three unrelated investigations run at once, the human in the loop cannot keep all of them in working memory at the same depth. The result is a degraded version of harness engineering: you start approving things you do not really understand, or you context-switch between topics every 30 seconds and lose the thread on every one of them. The real bottleneck is human comprehension, not compute. One topic at a time, parallelized inside; many topics at once, never.

A short way to state the rule: **fan out within a problem, queue up across problems**.

## Principle 2 — Session management: depth over breadth, with explicit sub-sessions

**(a) When investigating one problem, go deeper inside that problem's session rather than starting a fresh session.** Continuing the same thread keeps the accumulated context, the prior tool outputs, and the partial conclusions all in one place. Starting fresh forces you to re-bootstrap the context, often missing nuance that the agent had already discovered.

**(b) When the investigation legitimately needs to branch, use `claude --resume <session-id>` and `claude --resume <session-id> --fork-session` to spawn explicit sub-sessions.** A fork creates an independent timeline that inherits the parent's context but does not pollute it. This gives you a multi-agent style of sub-session management for a single problem: one parent thread holds the high-level plan, several forks explore alternative paths in parallel, and the survivors merge their findings back into the parent.

Concretely:

```bash
# Parent session: top-level investigation
claude --resume <parent-session-id>

# Sub-session A: try design A
claude --resume <parent-session-id> --fork-session
# Sub-session B: try design B
claude --resume <parent-session-id> --fork-session
# Sub-session C: try design C
claude --resume <parent-session-id> --fork-session
```

Each fork can be killed without losing the parent. The pattern is most valuable when the investigation has a real branching choice: which architecture, which estimator, which dataset to validate first. It is overkill for a strictly linear task.

## Why these two principles ride together

Principle 1 is about **breadth control** (do not spread agents across unrelated topics). Principle 2 is about **depth navigation** (when a single topic legitimately branches, fork rather than restart). Together they describe a discipline of focus: at any given moment one topic is active; inside that topic, work may fan out across subagents; if the topic itself splits, fork the session rather than open a parallel browser tab on a different problem.

## How to add a principle

This file is the source of truth. The Notion mirror has the same content with comments enabled for collaborative discussion. To propose a new principle:

1. Write a one-sentence rule (the part everyone should remember).
2. Two-to-four sentences of motivation: when does this matter, what fails when you ignore it.
3. (Optional) A concrete example or command snippet.
4. Open a pull request against `auto-quant-research/context-engineering/PRINCIPLES.md`, or leave a comment on the Notion mirror.

Keep the list short. A long list of principles is just noise; a short list that everyone has internalized is real culture.

---

*Maintainers: Kang Li · Aramis Fereydoun · contributors welcome.*
