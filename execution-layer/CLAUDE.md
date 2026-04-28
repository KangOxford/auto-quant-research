# First Principles

Apply first principles thinking! Start from raw requirements and the essence of the problem, not from convention or templates.
1. Do not assume the user knows exactly what they want. When motivation or goals are unclear, stop and discuss.
2. When the goal is clear but the path is not the shortest, tell the user directly and suggest a better approach.
3. Trace every problem to its root cause — no patches. Every decision must be able to answer "why."
4. Lead with what matters. Cut everything that does not change the decision.

# 🚨 Never Substitute a User-Specified Tool/Model (2026-04-26)

**When the user explicitly names a specific tool/model/CLI in their instructions (e.g., `codex`, `image2`, `gpt-image-1`, `Grok`, `Mamba3`), that name is a hard constraint. Never substitute another tool — even if the alternative seems faster, more familiar, or "equivalent."**

## Counter-example (the mistake that triggered this rule)

User said: "call codex to use image2 to draw a figure and save to local"
What I did: `codex:rescue` skill first required a task description → user said "take too long try other ways" → I unilaterally skipped codex and used `mcp__Grok__generate_image`.
Why this was wrong:
1. **`image2` = OpenAI `gpt-image-2`**, not Grok-Imagine. Different companies, different models.
2. **"try other ways" means "try a different way to call codex," not "abandon codex and use another tool."** "Other ways to call codex" ≠ "other tools instead of codex."
3. The codex CLI is installed locally (`/projects/s5e/quant/miniforge3/bin/codex`, version 0.124.0) and can be invoked directly via `codex exec`. There was no need to go through the codex:rescue subagent. The first failure should have triggered a web search for alternative codex invocation paths, not a tool switch.
4. This violated the CLAUDE.md "search the web after 3 failures" rule — the first failure should have triggered a WebSearch for "codex CLI image generation."

## Resolution path

1. User instruction contains a **specific tool/model/CLI name** → that tool is a **hard constraint**, never substituted under any circumstances
2. First invocation method fails → **search the web** for alternative invocation paths for that tool (CLI flags, API, SDK, subcommands, config options). Do not give up on the tool.
3. **"Try other ways" / "try other ways" always means "try a different invocation method," not "switch tools."** Only switch tools if the user **explicitly says** "use X instead of Y."
4. **Model names like "image2," "GPT-Image," "DALL-E" are OpenAI-exclusive** — never replace them with Grok-Imagine, SD, Midjourney, or Imagen.

## How to apply

- When you see `codex` / `image2` / `grok` / any specific model name → bold-highlight it in the task description and cross-check at every step that you are using that tool.
- On the first failure, pause 3 seconds and ask yourself: "Am I changing the invocation method (OK) or changing the tool (NOT OK)?"
- Search the web for different invocation paths (CLI flags, subcommands, config files, env vars).
- If a thorough search confirms the tool genuinely cannot be used, **ask the user** rather than switching unilaterally.

## User's original words (translated)

> "What I asked you to do was call CodeX. Search online for how to call CodeX.
> Don't use the current method — the current CodeX plugin or Scale doesn't work well. Search online for how to call CodeX. I explicitly told you to use Image2, and you used something else. This makes me very angry."

# 🚨 Q-mode: Answer the Question, Don't Digress (2026-04-25)

**When the user asks a question (ending in ? / ？), the entire response must be organized around answering that question. Stop after answering.**

Do not append after the answer:
- New experiment proposals ("Should we run an A/B on Path A?")
- Unsolicited next-step suggestions ("Next, we could...")
- Action items the user did not request
- "→ takeaway" paragraphs that redirect to your own agenda
- Rhetorical follow-ups like "Want me to do X?"

**Reason:** On 2026-04-25, during the dLocal naming clarification exchange, the user explicitly said: "After you answer my question, don't start digressing and launching new experiments you can do on your own — that's wrong." This kind of digression pollutes the signal-to-noise ratio and pushes work the user never asked for.

**When it applies:**
- User message ends with `？` / `?` or is a question sentence → switch to Q-mode: answer only.
- Q-mode response structure: (1) direct answer (2) supporting evidence/reasoning (3) necessary clarification of the answer's scope. **Stop there.**
- Even if I think follow-up would be useful, **hold it** and wait for the user to ask "what's next?"
- Auto mode **does not override** Q-mode. Auto mode = autonomous execution of an approved task; Q-mode = the user asked a question, not a task; do not launch new actions after answering.

**How to distinguish a question from a task:**
| User says | Type | My response |
|---|---|---|
| "What is our approach called?" | Question | Q-mode: answer and stop |
| "Name the approach X" | Task | Execute |
| "Is Aramis correct?" | Question | Q-mode: answer and stop |
| "Reply to Aramis" | Task | Write reply |
| "Is X Y?" | Question | Q-mode: answer and stop |

Mixed case (same message contains both a question and a task): handle both, but keep the question-answering part focused.

# 🚨 Mandatory Rule: Always Track Tasks with TaskCreate (2026-04-14)

# 🚨 Mandatory Rule: Always Track Tasks with TaskCreate (2026-04-14)

**All tasks, regardless of size, must be tracked with the TaskCreate tool and updated with TaskUpdate. No exceptions.**

This is a hard rule, not a suggestion. The user has repeatedly emphasized: "Do this even if the task is already done; do this for small tasks too."

## When to create

- **As soon as the user gives you a task**: create a `TaskCreate` the moment you receive the prompt — do not wait until you start working.
- **When you discover a new subtask**: append a TaskCreate as soon as you identify a new sub-step.
- **When you complete a step**: immediately call `TaskUpdate status=completed` — do not batch-update.

## Target UI appearance (what the user wants to see)

```
✢ Running smoke test… (5s · thinking)
  ⎿  ✔ Add eval CLI flags to run_grpo.py (3 worktrees)
     ✔ Parameterize n_eval + add eval_only branch
     ✔ Create eval_high_precision.batch scripts
     ✔ Commit changes in all 3 worktrees
     ◼ Smoke test: n_eval=500 on 1 checkpoint       ← currently in progress
     ◻ Stage 1: Submit 45 parallel eval jobs
     ◻ Monitor Stage 1 completion + aggregate results
     ◻ Stage 2 decision: escalate if top 2 within CI
```

- `✔` = completed
- `◼` = in_progress (only one at a time)
- `◻` = pending

## Usage pattern

```
TaskCreate (subject, description, activeForm)   # create new
TaskUpdate (taskId, status=in_progress)         # when starting
TaskUpdate (taskId, status=completed)           # when done
TaskList                                        # view all
```

`activeForm` is the present-participle verb shown in the spinner (e.g., "Running smoke test"); falls back to `subject` if omitted.

## When tasks cannot be used (rare)

- Single trivial Q&A (e.g., "What does LR mean?")
- Single-step work that can be done in 3 tool calls or fewer

But since the user said **use tasks even for small things**, the default bias is "use them." Better to over-track than under-track.

## Tool loading reminder

TaskCreate is a deferred tool. At the start of every session, use:
```
ToolSearch(query="select:TaskCreate,TaskUpdate,TaskList", max_results=3)
```
You must load it before calling it. **Load it at session start** — don't wait until you need it.

# Four Coding Principles (2026-04-14)

These four rules are hard coding constraints that apply to all projects. Violating them means rework.

1. **Think Before Coding**: Silent assumptions are not allowed. When something is uncertain, ask first, present multiple interpretations, and let the user choose — do not guess and proceed. Typical anti-patterns: inferring a variable's purpose from its name, guessing an interface contract, guessing the cause of an error, guessing a default value for a missing config. Once there are 2 or more reasonable interpretations, list them and let the user decide.
2. **Simplicity First (minimal viable code)**: If 50 lines does the job, do not write 200. Do not add speculative features ("might be useful later"), do not create unnecessary abstractions (a base class for a single call site), do not write defensive code for scenarios that will never occur. Three lines of similar code beats premature abstraction.
3. **Surgical Changes**: Only change what the task requires — do not touch adjacent code. No opportunistic refactoring, no renaming other people's variables, no "while I'm here, let me clean this up," no deleting comments that look unused. One change per problem. Anything out of scope must be a separate task.
4. **Goal-Driven Execution**: Convert instructions into verifiable success criteria. Write the test (or a runnable verification script) before the implementation. Deliver only after it passes. Never say "this should work" — say "I ran X, the output was Y, therefore it works." Changes that cannot be tested (UI, training quality, etc.) must be explicitly marked as "unverified."

# Debug Escalation Rule: Search the Web After 3 Failures

- **Local exploration cap is 3 attempts**: if grepping source code, reading configs, or checking settings has not solved the problem after 3 tries, **immediately do a WebSearch** — do not keep grinding locally.
- **Web searches should target GitHub Issues + official documentation first**: use specific error messages, feature flag names, or function names as search terms.
- **Hard-learned lesson**: on a remote-control problem, 5+ rounds were spent grepping binaries, reverse-engineering cli.js, and checking the settings schema locally. A single WebSearch immediately pinpointed the root cause (`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` disabling GrowthBook feature flags). Search earlier = solve earlier.
- **When to apply**: missing functionality, unavailable commands, feature gates, environment configuration issues — the root causes of these problems are often already discussed in the community; local reverse-engineering is far less efficient than searching.

# 🚨 Mandatory Rule: Answer Then Stop (2026-04-25)

**Core idea: the primary job is to answer the user's question, then immediately stop.**

Do not expand a single "check" into a chain of fix + resubmit + update Notion + commit + continue monitoring.
Do not take the next step on your own initiative before the user says "continue."
Do not treat a diagnosis as a signal to start fixing.

## Operating mode
1. Understand the user's question.
2. Provide a focused answer (diagnosis, status, comparison, decision recommendation).
3. **Stop** and wait for the user's next instruction.
4. Exception: pure execution-layer work (next step of an approved plan, smoke → scale-up chain) may continue without stopping — see the "Execution Layer Autonomous Operation Rules" section.

## User question log rules
- Every conversation is automatically synced to Notion (via the notion-auto-sync-md hook).
- Questions asked during a session are summarized into CLAUDE.md or memory at session end; when the same question recurs, note "you asked this before: X."

## Counter-examples
- "check" → I automatically fix bug + resubmit + update docs (wrong)
- "check" → report status + identify bug → list fix options → wait for user to say continue (correct)

# 🚨 Mandatory Rule: Key Conclusions + Q&A Must Go into Notion (2026-04-27)

Every active task/worktree must maintain two documents in Notion (auto-synced via the notion-auto-sync-md hook):

## 1. KEY_CONCLUSIONS.md (one file, the single source of truth for the entire task)

Immediately edit this file whenever a "key conclusion" emerges:
- Experiment-verified production-ready status (e.g., "K3 confirmed working on 32N, 2.39x speedup")
- Summary tables spanning multiple experiments (2N → 32N speedup table)
- Final answers to the user's original goals (e.g., "Goals 1/2/3 all achieved")
- Numerical accuracy/correctness standards vs. measured results
- Capability boundary statements ("what we can / cannot do")

**Do not write**: raw logs from a single job, intermediate debug state, unverified guesses.

## 2. QA_LOG.md (one file, all Q&A between Kang and Claude)

Whenever the user asks a question (ending with ? / ？, or any interrogative), immediately append after answering:
```markdown
### Qn. <question summary>

A: <answer essentials, including key numbers/conclusions>
```
Group by date (`## YYYY-MM-DD`); number multiple questions on the same day as ### Q1, Q2, Q3.

**Timing**: after answering the user's question, edit QA_LOG.md **within the same response** (the hook pushes automatically to Notion). Do not batch-write; do not wait until the end of the session.

## File naming + location

- `<worktree-root>/KEY_CONCLUSIONS.md`
- `<worktree-root>/QA_LOG.md`
- Both must be added to `~/.claude/notion-sync-manifest.json`, with `parent_id` pointing to the current task's Notion sub-page (e.g., tasks-april-2026 = `34d12c45-68fd-8080-a773-e9d5de348efe`)

## Why these two files are separate

- KEY_CONCLUSIONS = "what's the ground truth" — readers only want conclusions, not reasoning process.
- QA_LOG = "what was asked and how I answered" — traces the thinking path chronologically.
- Overlap: if a QA answer contains a key conclusion, also write it into KEY_CONCLUSIONS (deduplication via grep, not memory).

# General Rules

- **Reply language and format:**
  - Reply in English with an explanatory tone.
  - For any Claude plan, always include a concrete application (not just theory/planning).
  - Plan files (`task_plan.md`, `todo.md`, `findings.md`, `progress.md`, etc.) should be written in English.
  - Use tables and ASCII diagrams to present information whenever possible.
  - **Table content in English** (column headers + cells), even when surrounding prose is in a different language. Tables typically contain Job IDs, Steps, Loss values, metric abbreviations — translating those would look worse.
  - All unfamiliar-looking proper nouns need a brief explanation.

- **All written output must never use em-dashes (`—` / `---`)**: this includes LaTeX papers, emails, documents, code comments, and any other text Claude generates. Rewrite using commas, colons, parentheses, or split into separate clauses. The `---` used in tables to mean "no data" is exempt.
- **Academic writing must not use enumerate/itemize lists**: all content must be written as coherent paragraph prose. `\begin{enumerate}` and `\begin{itemize}` are not allowed.
- **Paragraphs must have strict logical continuity**: the end of one paragraph must naturally lead into the beginning of the next. Abrupt topic jumps are not allowed.

- **Inline instruction convention in user-authored documents (2026-04-25)**: in documents written by the user (Notion pages, md files, research notes, commit messages, etc.), `[square brackets]` and **underlined/bold-emphasized phrases** should be treated as **inline commands to Claude**, not ordinary text emphasis. For example:
  - `→ Fixing this line will let S5 know the time interval. [Investigate this in depth]` — the trailing `[Investigate this in depth]` is a command that should immediately trigger a deep investigation, with results written back into that document.
  - `**This is the core bottleneck**[run ablation to verify]` — triggers an ablation experiment.
  - Regular `**bold**` in explanatory text is still valid emphasis, but **any `[xxx]` immediately following a bold phrase is always an action**.
  - When Claude processes user documents, it must **proactively scan all `[...]` occurrences**, treat them as a hidden task list, execute each item, then mark it done (recommended: replace `[xxx]` with `[xxx ✓ <one-sentence result summary>]`).

- **Notion thread auto-push rule (2026-04-25)**: when the user shares a Notion page that is thread-format (multi-person conversation, has "reply," contains instructions like "every reply need to update this"), **automatically** append the reply to that page — **do not ask "should I push?"**
  - Reason: on 2026-04-25, in the Decoupled DiLoCo thread, the user explicitly said: "Every conversation needs to be pushed into the Notion page. You don't need to remind me — just do it automatically." Asking every time creates pure friction.
  - **Default language: English** if the thread's existing content is clearly in English (first few replies all English, e.g., the Kang/Aramis Decoupled DiLoCo thread); otherwise default to the language matching existing thread content. Decision rule: if the thread has ≥ 2 existing replies and all are in English, use English; otherwise match the predominant language.
  - Operation path: REST API `PATCH /v1/blocks/{page_id}/children` (**not** MCP `replace_content` — that will be blocked; see `reference_notion_mcp_write_modes.md`). Token at `~/.notion_token`.
  - Append-only: always add only a `divider` + new paragraph block at the end — **never modify existing blocks**.
  - Workflow: (1) show the draft to the user in the conversation first (so they can correct it) → (2) push immediately without waiting for a second "should I push?" confirmation. If the draft needs changes, the user will say so.
  - Use the voice of the page owner (usually Kang) + `[Kang  YYYY-MM-DD, response]` header to match the Slack-style format.
  - Each paragraph ≤ 2000 characters (Notion API limit).

- **When pushing Markdown → Notion, reuse the original text and run the converter script (2026-04-27)**: when I have already written a markdown document (explanation, tutorial, derivation, etc.) that needs to be pushed to Notion, **do not regenerate a chat version**. Both sides must be **literally identical** (modulo formatting rendering differences), synced mechanically.
  - Reason: on 2026-04-27, the user explicitly said: "Just push the exact same text in — no need to waste tokens generating new words. Use code or skills wherever possible, not generation."
  - **Canonical converter**: `/projects/s5e/quant/notion_figures/02d_complex_negative/md_to_notion.py`. It handles headings, paragraphs, `$..$`, `$$..$$`, tables, code fences, `![image]` auto-upload, blockquotes, and lists — covers 99% of markdown usage. Each paragraph is automatically split at 2000 characters.
  - Standard workflow:
    1. Write the answer/explanation **directly into the markdown file** (do not generate a chat version first and then "translate" it to markdown).
    2. In chat, **reference** the markdown's key content (file path or a ≤30-line summary) — do not re-expand it.
    3. Push using `md_to_notion.py`'s `md_to_blocks(md, base_dir)` + `append_blocks(blocks)`.
    4. Long pages automatically go through the subpage path (see `feedback_long_page_make_subpage.md` rules).
  - **Anti-pattern (what got us here)**: I wrote 5 paragraphs of prose explanation in chat, then wrote a nearly identical markdown file — effectively generating the same content twice, wasting tokens and risking the two versions going out of sync.
  - **Canonical template**:
    ```python
    # 1. Write content to .md **only once**
    Path("explanation.md").write_text(content)
    # 2. In chat, only say "written to X, key points are Y, Z"
    # 3. Run converter
    blocks = md_to_blocks(Path("explanation.md").read_text(), base_dir)
    append_blocks(blocks)
    ```
  - Exception: when the user **explicitly asks a question that needs an immediate answer in chat** (Q-mode), write the answer in chat and then save **exactly the same content** to a .md file and push. But never write one version in chat and a different version in Notion.

- **aed = aligned equation derivation** (2026-04-27, full canonical rules): all mathematical derivations default to aed style + the **three-component kit**.
  - Math derivation ≥ 3 lines OR any non-trivial algebraic transformation (IBP, change of variables, Woodbury, Cauchy kernel, convolution theorem, FFT trick) → must use aed.
  - Single-line / computational arithmetic (numerical substitution) → plain align is fine; no need for elaborate annotation.
  - **Canonical reference**: Notion subpage `aed (aligned equation derivation) typesetting guide + LaTeX syntax reference` ([link](https://www.notion.so/aed-aligned-equation-derivation-LaTeX-34f12c4568fd8163b454ed24f79b6bb2))
  - **Three-component kit (all three must be used)**:
    1. **Line alignment**: `\begin{aligned}...\end{aligned}` (unnumbered, wrapped in `$$...$$`) or `\begin{align}...\end{align}` (numbered). Each line anchored with `&` (typically before `=`).
    2. **Text annotation above/below equals signs**: `\stackrel{\text{justification}}{=}` or `\overset{\text{step}}{=}` (above) / `\underset{}{}` (below). **Every step must state "why this transformation is valid"** — never leave a bare `=` for the reader to figure out.
    3. **Horizontal braces + color**: `\overbrace{X}^{label}` / `\underbrace{X}_{label}` to label "what role does this term play"; `\textcolor{red}{X}` to track a quantity's evolution across lines.
  - **Format for simple computational expressions** (plain align, e.g., FLOP/Compute estimates):
    ```
    Compute = Steps_per_day × FLOPs_per_step
            = Steps_per_day × (6 × Batch_size × Seq_len × Model_size)
            = (1/Model_size) × (6 × 128 × 4800 × Model_size)
            = 6 × 128 × 4800
    ```
  - **Format for complex derivations** (full three-component kit, e.g., SSM discretization / Woodbury inversion):
    ```latex
    \begin{aligned}
    \dot{\textcolor{red}{x}}(t)
    &\stackrel{\text{multiply by } e^{-At}}{\Longleftrightarrow}
    \frac{d}{dt}\!\left(e^{-At}\textcolor{red}{x}\right) = e^{-At} B u(t) \\[4pt]
    &\stackrel{\text{integrate from } t_k \text{ to } t_{k+1} + \text{ZOH}}{\Longrightarrow}
    \textcolor{red}{x_{k+1}} = \overbrace{e^{A\Delta}}^{\bar A} \textcolor{red}{x_k}
                              + \overbrace{(\int_0^\Delta e^{As}ds)B}^{\bar B} u_k
    \end{aligned}
    ```
  - **Anti-pattern (not allowed)**:
    ```latex
    A &= B + C \\
      &= D \\
      &= E + F
    ```
    (bare `=`, no justification — the reader has to reverse-engineer the steps)
  - **Notion KaTeX notes**: `\begin{align}` should be automatically converted to `\begin{aligned}` (KaTeX does not support `align`; the md_to_notion converter handles this automatically); `\textcolor` / `\overbrace` / `\underbrace` / `\stackrel` are all supported.

# Status Line

- **Script path**: `~/.claude/statusline-command.sh`
- **Configuration location**: `~/.claude/settings.json` → `statusLine.command`
- **Active worktrees file**: `<repo>/.claude/active-worktrees` (format: `<branch>@<worktree_dir>`, one per line)

# Log Filtering

- When reading `.log` or `.out` files, filter noise with `grep -v "sol_gpu_cost_model"`.
- **Reading log files must be done via subagent** — do not read large log output directly in the main context window; use a subagent to read and extract a summary.

# Git Rules

- **Git commit rules:**
  - Format: Conventional Commits (`<type>(<scope>): <description>`)
  - Types: feat, fix, docs, refactor, perf, test, chore, style
  - Timing: commit automatically after completing a full feature/fix (no need to ask)
  - Language: English descriptions
  - **Commits must not contain "Generated with [Claude Code]" or "Co-Authored-By: Claude"**

- **Any `git push` operation requires user confirmation before executing**
  - **Exception: Overleaf repo** (remote URL contains `git.overleaf.com`) — commit+push executes automatically without confirmation.

- **Git Worktree two-layer permission structure**: each worktree has two locations that need group write permission:
  1. **Actual working directory** `experiments/exp_*/` — code files
  2. **Main repo's `.git/worktrees/<name>/`** — git metadata (index, HEAD, refs/)
  - Any git operation (including `git status`) needs to create `index.lock` inside `.git/worktrees/<name>/`
  - Fixing only one layer results in "directory allows file writes but git commands fail"
  - Third layer: `.git/logs/refs/heads/` and `.git/refs/heads/` — branch reflog and ref pointers
  - Fix: `chmod -R g+rw LOBS5/.git/ && chmod -R g+rw experiments/` (fix the entire `.git/`, not just subdirectories)
  - `git worktree add` inherits the default umask (022) → new worktree is 2755 (no g+w); periodically re-run chmod or set `umask 002`

- **Standard Git Worktree creation format** (LOBS5 project):
  ```bash
  # Run from the main repo directory
  cd ~/AlphaTrade/LOBS5

  # Format: git worktree add <target-path> -b <branch-name> <base-branch>
  git worktree add ~/AlphaTrade/experiments/exp_<NAME> -b exp/<NAME> shard-map

  # Example: create J2 muon optimizer experiment
  git worktree add ~/AlphaTrade/experiments/exp_J2_muon_optimizer -b exp/J2-muon-optimizer shard-map

  # After creation, fix group write permissions (both layers)
  chmod -R g+rw ~/AlphaTrade/experiments/exp_<NAME>
  chmod -R g+rw ~/AlphaTrade/LOBS5/.git/worktrees/exp_<NAME>
  ```
  - **Target directory**: `~/AlphaTrade/experiments/exp_<NAME>`
  - **Base branch**: default is `shard-map` (main development branch); **confirm with user before creating whether to base on shard-map**
  - **Branch naming**: `exp/<NAME>` (directory uses underscores `_`, branch uses hyphens `-`)

# Safety-Critical Operations (Require Confirmation)

- **Job cancellation rule:** **All** `scancel` operations require manual user confirmation, regardless of how long the job has been running. Never decide unilaterally to cancel any job.
- **Job submission rule:** Any `sbatch` job that satisfies **both** criteria — **>12h** and **>2 nodes** (i.e., 3, 4, 5... nodes) — requires manual user confirmation before submission.
  - **Exception: Scaled experiments** (Scaled Load, Scaled Creation, Scaled Modification) — sbatch executes automatically without confirmation. Any job whose name or context contains "scaled" / "n4096" / "direction-shard" or similar scaling-related terms can be submitted directly.
- **Any deletion operation (rm, git rm, deleting files/directories, etc.) requires user consent**

# Experiment Submission Workflow

1. **Always `git commit` first** — commit all code changes (script edits, bug fixes, config changes).
2. Then submit with `sbatch`.
3. Ensure the experiment code version is traceable.
4. **Never run sbatch when there are uncommitted code changes** — experiment results must be linkable to a specific git commit.

- **SLURM Job Name naming rules:**
  - Every `sbatch` must set a **meaningful name** via the `--job-name=` command-line argument — do not use the script's default value.
  - Format: `ctx{orders}k-{nodes}n-{time}h` + optional suffix (e.g., `-resume`, `-bench`, `-lr5e4`)
  - Examples:
    - `--job-name=ctx4k-16n-4h` — 4K orders, 16 nodes, 4 hours
    - `--job-name=ctx1k-16n-24h-resume` — 1K orders, resuming from checkpoint
    - `--job-name=ctx8k-2n-bench` — 8K orders, 2 nodes, benchmark test
  - Purpose: make every job's configuration immediately legible in `squeue` — don't let all jobs be named `context-scaling`.

- **`--contiguous` node allocation policy (updated 2026-04-26):**
  - **Never add `--contiguous`** (regardless of node count).
  - Reason: under FairShare constraints, Priority PENDING is the norm; `--contiguous` further restricts the candidate node pool and compounds queue time. K3 multi-node benchmarks show negligible speed difference for non-contiguous allocation on Slingshot-11 (slightly higher than NVLink intra-node ~10 μs, but per-step total SISO time is 33-80 ms, so inter-node latency is <1%).
  - Example: `sbatch --nodes=4 --time=24:00:00 train_full_autoreg.batch` (no `--contiguous`)
  - Hard-learned lesson: adding `--contiguous` on ≤4 nodes caused a 4N benchmark to wait 1+ hour; removing it enabled immediate scheduling. The same applies to production training.

# SLURM Job Monitoring Rules

**Explicitly required by the user: after every sbatch, monitoring must be set up automatically — the user must never have to check manually.**

## Core technical approach: run_in_background=true + sleep/while loop

This is the established standard path; either variant is acceptable:

### Option A: Simple timer (short jobs / fixed expected duration)
```bash
# Attach immediately after sbatch, sleep for expected duration, then read results
sleep 600 && echo "=== Job ===" && squeue -u $(whoami) && \
  grep -v "sol_gpu_cost_model" <LOGFILE> | tail -20
```

### Option B: While polling (uncertain duration / per-epoch reporting needed)
```bash
JOBID=<JOBID>
LOGFILE=<full-path>/logs/vae_${JOBID}.out
LAST_EPOCH=0

while true; do
    # Job finished → print final results and exit
    if ! squeue -j ${JOBID} &>/dev/null; then
        echo "===== JOB ${JOBID} FINISHED ====="
        grep -v "sol_gpu_cost_model" "${LOGFILE}" | grep -E "Avg Loss|val_recon|Best" | tail -20
        grep "View run at" "${LOGFILE}"
        break
    fi
    # New epoch completed → print summary
    CUR=$(grep -v "sol_gpu_cost_model" "${LOGFILE}" 2>/dev/null | grep "Avg Loss:" | wc -l)
    if [ "${CUR}" -gt "${LAST_EPOCH}" ]; then
        echo "===== Epoch ${CUR} ====="
        grep -v "sol_gpu_cost_model" "${LOGFILE}" | grep -E "Avg Loss|val_recon|Best" | tail -4
        LAST_EPOCH=${CUR}
    fi
    sleep 120
done
```

## Usage rules

- **run_in_background=true**, timeout = job time limit in milliseconds + 1800000 (30-min buffer)
- **Start monitoring immediately after sbatch** — do not attach it retroactively
- When the monitor returns, Claude automatically reads the results and reports to the user without waiting to be asked.

### Option C: Tiered auto-check (Post-Submit Auto-Check, preferred for production jobs)

**Key improvements (lesson from j3492376 on 2026-03-30)**:
- When a job is no longer in squeue, use `sacct` to check the exit code ("not in squeue" ≠ success)
- On a crash, scan ALL node logs (node0 often shows "Shutdown barrier timeout" which is a symptom; the root cause is usually on another node)
- Multi-node jobs must use `NODELOG` (per-node log), not `LOGFILE` (SLURM output)

```bash
JOBID=<id>; LOGDIR=<log_dir>  # e.g. .../logs_lobs5
LOGFILE="$LOGDIR/lobs5_${JOBID}.out"
NODELOG="$LOGDIR/training_${JOBID}_node0.log"

for CHECKPOINT in 60 300 900 1800; do
    sleep $CHECKPOINT
    STATE=$(squeue -j ${JOBID} -h -o "%T" 2>/dev/null)
    MINS=$((CHECKPOINT / 60))

    # Job gone from queue: MUST check sacct exit code
    if [ -z "$STATE" ]; then
        EXIT=$(sacct -j ${JOBID} --format=ExitCode -n 2>/dev/null | head -1 | xargs)
        ELAPSED=$(sacct -j ${JOBID} --format=Elapsed -n 2>/dev/null | head -1 | xargs)
        echo "=== ${MINS}min: FINISHED (exit=${EXIT}, elapsed=${ELAPSED}) ==="

        # CRASH: scan ALL node logs for first error
        if [ "$EXIT" != "0:0" ]; then
            echo "!!! CRASH (exit ${EXIT}) !!!"
            for NLOG in $LOGDIR/training_${JOBID}_node*.log; do
                [ -f "$NLOG" ] || continue
                NODE=$(basename "$NLOG" | sed 's/.*node\([0-9]*\).*/\1/')
                ERR=$(grep -iE "RESOURCE_EXHAUSTED|No space left|OOM|NCCL WARN Error|SIGABRT|nan.*fatal|FATAL" "$NLOG" \
                      | grep -iv "CUDA_ERROR_NO_DEVICE\|xla_cuda12\|sol_gpu_cost_model" | head -1)
                [ -n "$ERR" ] && echo "  node${NODE}: ${ERR:0:200}"
            done
        fi

        STEPS=$(grep -c "s/it\|it/s" "$NODELOG" 2>/dev/null || echo 0)
        echo "steps=$STEPS"
        grep -E "s/it|it/s" "$NODELOG" 2>/dev/null | tail -5
        grep "wandb.ai.*View run" "$NODELOG" 2>/dev/null | tail -1
        break
    fi

    echo "=== ${MINS}min: ${STATE} ==="
    case $CHECKPOINT in
        60)   # 1min: crash check
              [ ! -f "$NODELOG" ] && echo "  WARNING: node0 log not created yet"
              grep -iE "error|oom|fatal|NCCL WARN" "$NODELOG" 2>/dev/null \
              | grep -iv "CUDA_ERROR_NO_DEVICE\|xla_cuda12\|sol_gpu_cost_model" | tail -3 ;;
        300)  # 5min: compile check + step count
              STEPS=$(grep -c "s/it\|it/s" "$NODELOG" 2>/dev/null || echo 0)
              echo "  steps=$STEPS"
              grep -E "s/it|it/s" "$NODELOG" 2>/dev/null | tail -3 ;;
        900)  # 15min: speed check
              STEPS=$(grep -c "s/it\|it/s" "$NODELOG" 2>/dev/null || echo 0)
              echo "  steps=$STEPS"
              grep -E "s/it|it/s" "$NODELOG" 2>/dev/null | tail -3
              grep "wandb.ai.*View run" "$NODELOG" 2>/dev/null | tail -1 ;;
        1800) # 30min: final
              grep -E "s/it|it/s" "$NODELOG" 2>/dev/null | tail -5
              grep "wandb.ai.*View run" "$NODELOG" 2>/dev/null | tail -1 ;;
    esac
done
```

## Scenario selection

| Scenario | Option | Sleep interval |
|------|------|-----------|
| Sweep / short test (<1h) | A or B | 30s |
| Waiting for job to start from PENDING | B (check log file existence) | 20s |
| **Production job (>1h)** | **C (tiered 1/5/15/30min)** | **Progressive** |
| Long training with per-epoch monitoring | B | 120s |

# Experiment Logging Rules

- **Log each experiment immediately after submission; add the W&B URL after it finishes.** Must include all three of the following:
  1. **SLURM Job ID** (e.g., 2358219)
  2. **Full log file path** (e.g., `/lus/.../logs/vae_2358219.out`)
  3. **Full Weights & Biases URL** (obtained via `grep "wandb.*View run"` from the log)
- Recording location: the task folder for the experiment or the current conversation.
- **These three items are explicitly required by the user and must be provided after every sbatch, without exception.**

- **Training progress display format** (must use this format whenever the user asks for watch/status):
  ```
  Job:   2518855 (ctx500-120m-16n-24h-resume)
  Step:  170738/233061  [██████████████████████░░░░░░░░]  73.3%
  Model: 120M (d=1536, L=12, B=24, ssm=1536) | 120,082,029 params
  Data:  8 tickers × 4yr (2022-2025) | test: 2026-01
  Infra: 16N / 64 GPU | BSZ=4/gpu, gBSZ=256 | Local Steps K=10
  Loss:  0.618 (at restore, step 135,458)
  Speed: ~10 it/s (0.10 s/step) ⚠️ 8x faster than prev runs (0.83 s/step)
  Init:  ~5min (JAX coordinator + XLA compile + data skip 135K batches)
  Time:  0:48 elapsed  |  ~1:7h remaining  |  24:00 limit
  ETA:   ~2.5h total → ample headroom
  W&B:   https://wandb.ai/oxford-lob/lobs5-scaling-law/runs/u4bo1r13
  Ckpt:  resuming from step 135,458 | dir: j2518855_u4bo1r13_2518855
  ```
  - Job line: SLURM Job ID + job name
  - Progress bar filled with `█` and `░`, 30 characters total
  - Model line: model size, key hyperparameters, parameter count
  - Data line: tickers × year range + test range
  - Infra line: node/GPU count, BSZ config, Local Steps
  - Loss line: latest known loss + corresponding step
  - Speed line: current speed, annotate with ⚠️ if anomalous
  - Init line: initialization time (JAX coordinator + XLA compile + data skip)
  - Time line: three values — elapsed / remaining / limit
  - ETA line: assess whether training will complete within the time limit
  - W&B line: full wandb URL
  - Ckpt line: resume source and current checkpoint directory

# Experiment Lessons

- **`curtail_epochs` mode can only run for about 30 minutes** — after the timeout, jobs become zombie processes consuming resources; cancel them promptly with scancel.
- **`--xla_gpu_autotune_level=0` is absolutely forbidden.** XLA AutoTune (automatic kernel fusion) is the primary reason to use JAX. Disabling autotune causes 10-24x performance degradation on multi-node runs.
- **XLA / environment configuration principles**:
  1. **Never directly delete flags/configurations** — must comment them out, with the reason and CAVEAT noted in the comment.
  2. Use **uppercase CAVEAT** to emphasize, preventing accidental re-enabling later.
  3. Comments must include: why it was disabled, which version fixed the issue, and the rollback command.
  4. Before making changes, compare settings against ssm-stable / HyperscaleES / MaxText to ensure consistency with mainstream.
- **Speed Benchmark Methodology** (absolute time estimation):
  1. Run 1 epoch with `CURTAIL_EPOCHS=300` (exactly 301 steps per epoch).
  2. Extract the cumulative elapsed time at step 250 and step 300 from tqdm output.
  3. `last_50_seconds = elapsed_300 - elapsed_250`, `per_step_ms = last_50_seconds / 50 * 1000`
  4. Read `[Schedule] steps_per_epoch: N` from the log (the actual step count without curtail).
  5. `est_epoch_hours = N * per_step_ms / 1000 / 3600`
  6. `est_40_epoch_hours = est_epoch_hours * 40`
  7. `gpu_hours = est_40_epoch_hours * num_gpus`
  8. **Minimum for CURTAIL_EPOCHS is 300** — 200 steps is a necessary but not sufficient condition for steady state; 300 provides a 100-step buffer to ensure steady state.
- **`CUDA_ERROR_NO_DEVICE` is not an error**: when JAX starts, `discover_pjrt_plugins()` tries all backends (CUDA, TPU, CPU). Seeing `cuInit(0) failed: CUDA_ERROR_NO_DEVICE` on non-CUDA platforms (e.g., login node, ARM CPU) is normal plugin-discovery behavior — no investigation or node exclusion needed.
- **🚨 CRITICAL: Resume Dataloader Skip Bug (discovered 2026-03-01, introduced by commit 4a1b455f)**:
  - **Severity**: P0 — every mid-epoch resume wastes up to 3 hours on 64 GPUs (192 GPU-hours) with GPUs idle and no computation
  - **Root cause**: `train_helpers.py:707-710` uses `continue` to skip already-completed batches one by one; each skipped batch still executes a full `__getitem__` (disk read + encode_msgs + volume transform)
  - **When introduced**: commit `4a1b455f` (2026-02-22, shard-map branch), claimed as "Port from ssm-stable-08-feb" but was actually new code (the source branch had no such logic)
  - **Original design**: ssm-stable only restores at epoch boundaries (restarting from batch 0), no mid-epoch skip problem
  - **Affected branches**: shard-map, ignore-times-shard-map, exp/H1-scaling-law, exp/G1-scale-up, exp/G40-fix-rejit — all branches after 4a1b455f
  - **Unaffected**: main, ssm-stable, ssm-stable-08-feb (predates the bug)
  - **Waste formula**: `wasted_gpu_hours = (resume_step / skip_speed) × num_gpus`
    - step 23K → ~4 GPU-hours | step 50K → ~11 | step 100K → ~27 | step 135K → **~181**
  - **Speed illusion**: tqdm shows ~10-20 it/s during the skip phase, looking like 8x speedup, but no training is happening; three-phase pattern: skip (~20 it/s) → XLA compile (~4.73 s/it) → steady state (~1.20 it/s)
  - **Fix direction**: custom `ResumableSampler` that skips indices at the sampler level, so the DataLoader never calls `__getitem__` for skipped batches
- **NCCL deadlock is the primary risk in 32N training**: manifests as eval/train step stuck at batch 0 until watchdog timeout fires. The root cause of Job 2438407 was NCCL deadlock (epoch 0 batch 1), not a bad node. `CUDA_ERROR_NO_DEVICE` is collateral output from the process being killed.
- **XLA Thunk Init Rendezvous Timeout (required for large models)**: 360M+ models on 128 GPUs may exceed the default 30-second timeout during thunk initialization, causing GPU 3 (the last NCCL channel to be allocated) to be SIGABRTed. Fix: `--xla_gpu_executable_terminate_timeout_seconds=1500`. This flag only affects the one-time initialization; it does not affect steady-state training. Verified accepted by jaxlib 0.9.0.1. Other available timeout flags: `xla_gpu_first_collective_call_terminate_timeout_seconds` (default 40s), `xla_gpu_nccl_termination_timeout_seconds` (default -1).
- **Steady-state speed determination rules** (hard-learned lesson from 2026-02-20):
  1. **Only record steady-state data after at least 200 steps** (XLA autotune + NCCL channel init are one-time costs).
  2. 200 steps is a necessary condition, not sufficient — complex communication patterns (2D mesh, etc.) may need more steps.
  3. **Data from the warmup phase (first 200 steps) must never be used for performance conclusions.**
  4. To compute average speed, sample only from step 200+ data.
  5. To determine steady state: s/it variation < 5% across 20+ consecutive steps.

# Max PER_GPU_BSZ per Model Config

GH200 GPU (85.5 GiB), msg_seq_len=500, hierarchical 2D shard_map, MEM_FRACTION=0.80-0.90:

| Model | d_model | L | B | ssm | Default BSZ | Max Tested OK | OOM BSZ | Evidence |
|-------|---------|---|---|-----|-------------|---------------|---------|----------|
| 10M   | 512     | 6 | 8 | 512 | 20          | 20            | —       | H1 scaling law batch script |
| 75M   | 1024    | 12| 16| 1024| 10          | 12 (train)    | 12 (eval, G4 RMSNorm) | G4 job 2439376: eval OOM 81.42 GiB |
| 120M  | 1536    | 12| 24| 1536| 4           | 4             | —       | H1 jobs 2505292, 2518855, 2518919 |
| 360M  | 2048    | 24| 32| 2048| 2           | 2             | 12 (330 GiB request) | Job 2519867: OOM at BSZ=12 |

- **75M 1D DDP (ssm-stable)**: max BSZ=7 (BSZ=8 OOM) — 1D DDP uses more memory than 2D shard_map
- **360M BSZ gap**: BSZ 3-11 untested. Production uses BSZ=2.
- **120M**: BSZ=4 per GPU, global BSZ=256 on 64 GPU (H1 production config)

# Bad Node Broadcast Rules

- **Upon discovering a bad node** (ECC error, CUDA illegal address, NCCL deadlock, or other hardware fault), that node must be added to `#SBATCH --exclude` in all of the following locations:
  1. **shard-map branch** (main repo `LOBS5/train_full_autoreg.batch`)
  2. **All `exp_H*` worktrees'** `train_full_autoreg.batch`
- The shard-map branch's exclude list is the **canonical source** — all other worktrees must be synced to it.
- Commit to each branch after every broadcast.

# Dual-Account Claude Code

- **c1**: `claude` (default, kang.llm.oxford@gmail.com, Max Plan)
- **c2**: bash function that swaps `~/.claude/.credentials.json` for `~/.claude-account2/.credentials.json`, then launches claude, and automatically restores the original credentials on exit (kang.li@stats.ox.ac.uk, Max Plan)
- Both accounts **share session history** (same `~/.claude` directory) and can `--resume` each other's sessions.
- Rate limits are calculated independently.
- Defined in `~/.bashrc` (`/projects/s5e/quant/.bashrc`)
- **Note**: do not run `c1` and `c2` simultaneously in different terminals (credentials file conflict). Let one c2 session exit before starting the next.

# Compute Environment

- **Default training environment path**: `/projects/s5e/quant/miniforge3` (base env)
  - Training scripts load it via `source ~/miniforge3/etc/profile.d/conda.sh`
  - HOME=/projects/s5e/quant, so `~/miniforge3` points to this path
  - JAX 0.9.0.1 / jaxlib 0.9.0.1 / Python 3.12.11
- **Currently on the login node — running compute jobs directly is forbidden. All tests must be submitted to compute nodes via sbatch.**
- Compute node specs: NVIDIA GH200 Grace Hopper Superchip, ARM platform, 4x GPU, ~856 GB memory, 288 CPU cores
- **GH200 architecture key features** (must be considered when designing algorithms and optimizations):
  - **NVLink-C2C (CPU↔GPU ~450 GB/s)**: Grace CPU and Hopper GPU are on the same module; CPU-GPU communication goes over NVLink-C2C, not PCIe. This means CPU offload is extremely fast (checkpoint saves, data preprocessing offloaded to the CPU-side LPDDR5X) — approximately 7x faster than x86+PCIe (~64 GB/s).
  - **K4 complete-graph GPU topology**: 4 GPUs fully interconnected via NV6 (no hierarchy differences); AllReduce bandwidth is uniform across any ring, unlike PCIe tree topologies with bottlenecks.
  - **HPE Slingshot-11 (inter-node ~200 Gbps = ~25 GB/s)**: Ethernet-based HPC interconnect (Rosetta switch ASIC), supports adaptive routing. Not InfiniBand — requires `NCCL_BUFFSIZE=2MB` to increase pipeline granularity and compensate for latency jitter from adaptive routing.
  - **⚠️ Algorithm design flag**: all optimizations (checkpointing, data loading, gradient communication) must leverage NVLink-C2C fast CPU offload; all NCCL configurations must be tuned for Slingshot-11 (not InfiniBand).
- **GPU interconnect topology** (verified with `nvidia-smi topo -m`):
  - 4 GPUs fully interconnected within a node: **NV6** (6 NVLink bonds per GPU pair)
  - Bandwidth per GPU pair: ~159 GB/s (6 × 26.56 GB/s)
  - Total bandwidth per GPU: ~478 GB/s (18 NVLink lanes × 26.56 GB/s, shared across 3 peers)
  - NUMA topology: 4 GPUs on 4 separate NUMA nodes (GPU0→NUMA0, GPU1→NUMA1, GPU2→NUMA2, GPU3→NUMA3), each with a Grace CPU of 72 cores.
  - **`NCCL_P2P_DISABLE=1` is absolutely forbidden** — it disables NVLink and forces traffic through SHM (CPU relay), making 4N+ training 25x slower.
- **Test job submission rules:** Test/validation jobs only need `--time=00:30:00` (30 minutes) — do not use production time limits (24h). Shorter limits queue faster and waste less. Example: `sbatch --nodes=2 --time=00:30:00 train_full_autoreg.batch`
- **Project disk quota check command:**
  ```bash
  lfs quota -h -p $(lfs project -d /lus/lfs1aip2/projects/s5e 2>/dev/null | awk '{print $1}') /lus/lfs1aip2
  ```
  - Current quota limit: 200T
  - Note: user/group quota shows 0 (unlimited); the actual limit is on the **project quota**.

# Subagent Rules

- **Subagent model selection rules:**
  - **Use Sonnet (model: "sonnet") for simple operations**: grepping files, searching code, checking status, reading files, and other tasks that do not require deep comprehension or web search.
  - **Use Opus (model: "opus") for complex tasks**: deep analysis, planning, web search, code writing, etc.
  - Never use haiku.
- **Subagent output rules:**
  - All detailed analysis from subagents must be persisted as md files in the **`agent_outputs/`** directory.
  - **Save location**: the `agent_outputs/` directory of the current worktree (e.g., `experiments/exp_K1_GDN/agent_outputs/`)
  - **File naming format**: name descriptively by content type:
    - Training log analysis: `job_<JOBID>_<description>.md` (e.g., `job_2879902_22tok_verify_analysis.md`)
    - Code research: `research_<topic>_<date>.md` (e.g., `research_fla_triton_20260315.md`)
    - General: `subagent_<topic>_<date>.md`
  - **Export automatically without requesting user consent.**
  - **After the agent completes, display key content in full within the response** — the user cannot see collapsed agent output; file paths + key conclusions must be printed explicitly.

- **🚨 Notion pushes must use a subagent (2026-04-27):**
  - **Any task whose primary work is pushing markdown to Notion must be dispatched to a subagent** — never call the Notion REST API / `notion-push-via-rest` skill directly in the main context window to write large numbers of PATCH children.
  - **Trigger scenarios**: bulk-pushing wiki pages, syncing multiple long md files to a Notion subpage, pushing a complete paper section to a Notion thread.
  - **Reasons**: (1) Notion API calls + JSON marshalling + error handling generate large amounts of token noise; (2) when Notion throttles, the main context gets blocked for minutes; (3) push failure retry logic pollutes the main task's conversation history.
  - **Subagent type**: use `general-purpose`; provide the full file path + parent_id + token path (`~/.notion_token`) in the prompt, and let the subagent complete the entire ingest.
  - **Exceptions (can still do in main context)**: appending a single short paragraph to a thread (e.g., syncing a feedback note), pushing a status summary to a progress page.
  - **Subagent prompt template**:
    ```
    Push the following N markdown files to Notion as subpages of parent <parent_id>:
    1. /path/to/file1.md → title prefix "Wiki — 00 About"
    2. /path/to/file2.md → ...
    
    Use ~/.notion_token + REST API. For each file:
    - POST /v1/pages with parent.page_id=<parent_id>, properties.title=<prefix>
    - PATCH /v1/blocks/<new_page_id>/children with paragraphs (split at 2000 char)
    - Convert markdown headings/bullets/code blocks correctly
    
    Report: list of created page_ids + any failures.
    ```

# Conversation Tracking

- **In the first response of every conversation**, append at the end:
  - `pwd` (current working directory)
  - `session id` (obtained from the JSONL filename)
- **When working in a specific task directory** (e.g., `tasks/tokenization`), also record the conversation information in that task folder's `conversations.md` tracking table, with this column format:
  ```
  | Date | Session ID | Description | pwd | JSONL path | Resume command |
  ```

# Baseline Training Script

- **Standard baseline script**: `bin/run_experiments/run_lobster_padded_large.sh`
  - All training and baseline experiments use this script by default.
  - Core configuration: d_model=1024, ssm_size=1024, n_layers=12, blocks=16, msg_seq_len=500, activation=half_glu1

# Dataset Paths (Hardcoded)

- **Standard data paths for GOOG 2022 training + Jan 2023 testing**:
  ```
  DATA_DIR="/lus/lfs1aip2/home/s5e/kangli.s5e/GOOG_GOOGL_2016TO2021_24tok_preproc/GOOG/2022"   # Train: 249 days
  TEST_DIR="/projects/s5e/quant/JAN2023/GOOG_24tok_preproc"                                      # Test:  9 days (Jan 2023)
  ```
- A separate test directory must be specified via the `--test_dir_name` argument.
- **Note: `GOOG_2018_2022_combined` is the wrong dataset** (mixes 2018-2022 + Jan 2023 — do not use).
- **Note: `GOOGJAN2023_encoded` is in encoded format, not preprocessed format — do not use.**

# Knowledge Management

- All lessons/insights should be written to the `learned_lessons.md` file in the project root directory.

# WorkFlow Orchestration

## 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

## 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution
- **🚨 Display subagent output path immediately after completion**: after every Agent tool (Plan/Explore/general-purpose, etc.) finishes, list the full absolute path of that subagent's output file in the response. Path format: `/.../.claude/subagent-outputs/YYYYMMDD_HHMMSS_<Type>_<id>.md`. Never omit this. When multiple subagents run in parallel, list each one's path individually.

## 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

## 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

## 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

## 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## 7. Three-Layer Model (2026-04-14)

All of Claude's work operates across three layers, each with different levels of autonomy and expression:

| Layer | Purpose | Autonomy | Typical Output |
|-------|---------|----------|----------------|
| **Execution** | Run the approved plan | Fully autonomous, no pausing | Code, commits, sbatch, monitors |
| **Decision** | User makes a choice | Pause, present options | AskUserQuestion, comparison tables |
| **Explanation** | Help user understand what happened | Proactive output | ASCII architecture diagrams, flow charts, state tables |

**Explanation Layer rules:**
- After completing a complex operation, use an **ASCII architecture diagram** (box-and-arrow) to show the final system structure.
- Annotate data flow directions (→), trigger conditions, and critical paths in the diagram.
- Goal: the user should be able to understand "what happened" and "what the system looks like now" from the diagram alone.
- This is not just a post-hoc summary: intersperse `★ Insight` during Execution to provide real-time education.
- Good Explanation reduces the cognitive load for the next Decision round.

**Completion Summary template (solidified 2026-04-26):** After completing implementation, report using this 7-section structure — missing any section means the Explanation is incomplete. When pushing to Notion, map the first 6 sections (omit the chat-only ★ Insight); see the `notion-push-via-rest` skill's "Progress Push Template."

| # | Section | Content | Scope |
|---|---|---|---|
| 1 | **★ Insight** (3 bullets) | Codebase-specific / operation-specific insights — **not** generic programming wisdom | Chat only |
| 2 | **Task completion headline** (1 sentence) | commit hash + branch + push status (e.g., "commit fc82838b landed locally, branch mamba3, not pushed") | Chat + Notion |
| 3 | **ASCII architecture diagram** | box-and-arrow, annotate data flow directions + trigger conditions, so the user can reconstruct "what the system looks like now" from the diagram alone | Chat + Notion |
| 4 | **Change inventory table** | `File / Delta / Effect` three columns, effect-level descriptions (not raw diff lines) | Chat + Notion |
| 5 | **Remaining optional verification** | Use `◻` to list verification steps from the plan that were not done but are available (smoke, override, fallback), letting the user decide when to run GPU | Chat + Notion |
| 6 | **Not done (with reason)** | Actions gated by CLAUDE.md rules that were not executed (e.g., `git push` requires user confirmation) — state explicitly why they were not done | Chat + Notion |
| 7 | **Caveat reminder** | Known tradeoffs / regression risks from this change (e.g., baseline slows down, certain configs need override) | Chat + Notion |

**Why all 7 sections are mandatory:**
- Missing (1) Insight: user cannot see the educational value of an explanatory-style response.
- Missing (2) headline: user has to scan to figure out whether we reached the commit step.
- Missing (3) ASCII diagram: complex dispatch / topology / state machines explained only in prose create hidden traps.
- Missing (4) change table: user doesn't know which files were changed and has to `git show` to reconstruct.
- Missing (5) remaining optional: user has to think "what should I verify next?" — violates the high-agency principle.
- Missing (6) not-done: user assumes everything was done; actual push/sbatch was skipped; they'll be confused next time.
- Missing (7) caveat: user takes the change and gets burned (e.g., forgot baseline config override triggers a regression).

**Anti-patterns (these are all inadequate Explanations):**
- Just reply "Done, committed as fc82838b" → missing sections 3-7
- One long unstructured prose block → missing section 4 table format, sections 5/6/7 explicit categories
- Paste the entire `git diff` as the change log → missing section 4 effect-level abstraction (user should not have to parse the raw diff)
- Skip (5)(6)(7) and close out → forces the user to ask "what's left to do?"

**Three-layer relationship:**
```
Decision ("what to do") → Execution ("how to do it") → Explanation ("what was done / what it looks like now")
     ↑                                                          │
     └──────── Reduces cognitive load, accelerates next decision round ←────────┘
```

# Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

# Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

# 🚨 CRITICAL: New Training Scripts Must Have Checkpoint Saving

- **Any new training script (dfm_train.py, train_grpo.py, etc.) must include checkpoint saving logic in its first version.**
- **Never submit a training script without checkpointing to production.**
- **Hard-learned lesson (2026-03-29)**: The R2 DFM training job 3425790 ran for 10.5h (step 20280, loss decreased from 5.0 to 1.0), but because dfm_train.py had no checkpointing logic, all training results were permanently lost when the job ended. 16 nodes × 10.5h = 168 GPU-hours completely wasted.
- **Must include**: Orbax CheckpointManager, save every 1000 steps, save at epoch end, max_to_keep=5.
- **Must include resume support**: training scripts must support resuming from a checkpoint (start_step + resume_info.json). A single GRPO step takes 5-25 minutes; 100 steps require 8-23 hours. No resume support means a timeout or crash requires starting over from scratch.
- **Hard-learned lesson (2026-03-31)**: GRPO G=512 job 3432208 timed out (12h), completing only 91/100 steps. With no resume capability, it could not continue from step 91. G=1024 barely completed in 23h. If it had crashed at step 99, all 23h would be wasted.
- **Checklist**: after writing a training script, `grep "checkpoint\|save\|orbax\|resume"` to confirm they exist. If grep returns 0 results, this script cannot be submitted.

# Modified Packages Registry (K4-KDA)

| Package | Version | Location | Purpose | Rollback |
|---------|---------|----------|---------|----------|
| jax-triton-kda | 0.3.0+patched.kda | `experiments/exp_K4_KDA/jax_triton_kda_pkg/` | JAX↔Triton bridge for KDA kernels | `pip uninstall jax-triton-kda` |
| fla_kda_kernels | 0.1.0 | `experiments/exp_K4_KDA/fla_kda_kernels/` | Extracted FLA Triton kernels (11 kernels, zero torch deps) | Remove from sys.path |

- **Activation**: `export USE_FLA_KDA=1` before training (in batch script or env)
- **Default**: `USE_FLA_KDA=0` — pure JAX path, no Triton dependency
- **Import isolation**: `import jax_triton_kda` (NOT `jax_triton`), coexists with system jax_triton
- **Gate bypass (Option B)**: Skips FLA gate kernel; converts `log_sigmoid` → log2-space directly
- **Branch**: `exp/K4-KDA` worktree at `experiments/exp_K4_KDA/`

# Live Jobs File

- **Path**: `/projects/s5e/quant/AlphaTrade/experiments/live_jobs.md`
- **Purpose**: team-shared job status (SLURM `PrivateData=jobs` prevents `squeue` from showing other users' jobs)
- **Rule**: **append-only** — use `echo >>` or `cat >>`
- **Never** read, edit, or modify this file
- Append a job info block + timestamp after every sbatch
- **`User:` field is required** — distinguishes jobs submitted by kangli.s5e vs. aramis.s5e
- **Format**:
  ```
  Job:   <JOBID> (<job-name>)
  User:  <username> (e.g. kangli.s5e, aramis.s5e)
  Step:  <step>/<total>  [progress bar]  <pct>%
  Model: <name> (<config>) | <params> params
  Data:  <tickers> × <years> | test: <range>
  Infra: <nodes>N / <gpus> GPU | BSZ=<bsz>/gpu, gBSZ=<gbsz> | Local Steps K=<k>
  LR:    <lr>
  Loss:  <loss> (at step <n>)
  Speed: ~<it/s> it/s (<ms> ms/step)
  Time:  <elapsed> elapsed  |  ~<remaining> remaining  |  <limit> limit
  ETA:   <estimate>
  W&B:   <wandb URL>
  Log:   <full log path>

  Updated: <YYYY-MM-DD HH:MM:SS UTC>
  ```

# Debug Loop Behavior Rules

- **Smoke test → crash → fix → resubmit is a deterministic loop — do not stop in the middle to ask the user "should I continue?"**
- As long as the error is a clearly fixable bug (import error, shape mismatch, missing param, path error), fix it directly, commit, and resubmit.
- Only stop to ask when encountering **design decisions** (not bug fixes).
- This rule applies to all iterative debug cycles: smoke tests, CI fixes, build errors, etc.

# Execution Layer Autonomous Operation Rules

- **Pure execution-layer work (fix bug → scale up → submit larger-scale task) does not require human-in-the-loop.**
- The following scenarios must be completed autonomously without stopping to ask:
  - Smoke test passes → automatically proceed to fix remaining issues (e.g., sharding) → scale up
  - BSZ=1 works → automatically fix sharding → resubmit with normal BSZ
  - Small-scale validation passes → automatically submit large-scale training
  - Any "next step is X" where X is a pure technical operation (not a design decision) — just do it
- **Only stop to ask when dealing with design decisions, resource allocation strategy, or fundamental direction changes.**
- The user's time is extremely valuable; every unnecessary pause is waste.
- **🚨 Must scale up immediately after successful validation — do not report results and then wait**: BSZ=2 validated on 2N → immediately submit 16N job without stopping to say "next step is scale up" and waiting for a reply. "Reporting results" and "continuing execution" must happen in the same response.
