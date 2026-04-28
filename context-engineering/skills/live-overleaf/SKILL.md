---
name: live-overleaf
description: Write/edit LaTeX content and push to Overleaf. Use when user says "tex", "latex", "overleaf", "update paper", "live update", "write section", "appendix", or asks for any modification to the quant2026 paper. Includes 5-level time-decay revision highlights with mandatory cascade on every edit and 100% paragraph coverage.
---

# Live Overleaf: LaTeX Writing & Push

When writing or editing LaTeX content (`.tex` files), follow these rules strictly.

## Overleaf Repo

**There are TWO `quant2026.tex` files on disk. Always write to the day-to-day draft, NEVER to the NeurIPS submission repo unless the user explicitly says so.**

| Repo | Path | Role | Touch? |
|------|------|------|--------|
| **Day-to-day draft** | `~/AlphaTrade/LOBS5/overleaf/69b804b1b5022d27002331fa/` | **Per-topic files** under `drafts/<user>/`, see Per-Topic Layout below | ✅ YES (default) |
| NeurIPS submission | `~/overleaf/quant_foundation_model_neurips_2026/quant2026.tex` | ~8000 lines monolithic, frozen for NeurIPS 2026 deadline | ❌ NO (unless user says "NeurIPS version") |
| Legacy monolith snapshot | `drafts/kang/main/quant2026_<date>.tex` | Dated assembly of per-topic files | Read-only reference |
| (stub) | `~/AlphaTrade/LOBS5/overleaf/69b804b1*/main_tex/main_quant2026.tex` | 0-byte placeholder | ❌ NO (ignore) |

The two live versions diverge because the NeurIPS repo is trimmed for conference page limits; they are **not symlinks of each other**. The day-to-day repo was split from monolithic `drafts/quant2026.tex` into per-topic files during 2026-03/04.

```bash
# Default workflow (day-to-day draft)
cd /lus/lfs1aip2/projects/s5e/quant/AlphaTrade/LOBS5/overleaf/69b804b1b5022d27002331fa

# Step 1: always sync BEFORE editing — Overleaf editor pushes silently
git fetch origin master && git rebase origin/master 2>/dev/null || {
    git stash push -m "pre-sync" && git rebase origin/master && git stash pop
}

# Step 2: pick or create the per-topic file
TEX=drafts/kang/<your_topic>.tex   # e.g. drafts/kang/match_engine.tex

# Step 3: edit, commit, push (auto for Overleaf, no confirmation needed)
git add "$TEX" && git commit -m "<msg>"
git push origin master || {
    # Race: Overleaf editor pushed during our edit
    git stash push -m "pre-push-recovery"
    git pull --rebase origin master
    git stash pop
    git push origin master
}
```

**Push-reject recovery is the norm, not an exception.** Overleaf's web editor auto-pushes on every keystroke batch, so any local edit that takes longer than a few seconds will race with a remote commit. Always assume the push will be rejected and have the stash-rebase-pop recovery ready. Never `--force` push to Overleaf: it will overwrite the user's browser-side edits.

### Per-Topic Layout (current live reality, 2026-04)

`drafts/quant2026.tex` no longer exists as a single file at the drafts root. Each collaborator owns a subdirectory with standalone `.tex` files, each sharing a per-user preamble.

| Subdirectory | Owner | Contains |
|--------------|-------|----------|
| `drafts/kang/` | Kang | main working area: `preamble.tex`, `pretraining.tex`, `posttraining_dfm.tex`, `posttraining_rl_es.tex`, `agentic_rl.tex`, `ai_infra.tex`, `tokenisation_and_data.tex`, `transformer_nsa.tex`, `baselines.tex`, `match_engine.tex` |
| `drafts/kang/main/` | Kang | `quant2026_<date>.tex` dated monolithic snapshots |
| `drafts/aramis/` | Aramis | per-topic files |
| `drafts/valentin_quant2026.tex` | Valentin | single-file draft |
| `drafts/fundamentailab/` | external | collaborator work |
| `drafts/core/` | shared | section-level shared content |
| `drafts/isambard_summit_2026.tex` | | Isambard Summit 2026 standalone draft |
| `drafts/ticker_list.tex` | | SP500 ticker list appendix |

**Creating a new topic file** (template from `drafts/kang/ai_infra.tex`):

```latex
\documentclass{article}
\input{drafts/kang/preamble}

\title{<Topic Title>}
\date{<Month Year>}

\begin{document}
\maketitle
\tableofcontents

\section{<first section>}
...

\end{document}
```

Save as `drafts/kang/<topic>.tex`. In the Overleaf web editor, double-click the file in the left panel to set it as the compile target. Each topic file is independently compilable; no include chain.

### Key Sections (legacy index, refers to monolithic `drafts/quant2026.tex` before the 2026-04 split)

Verify line numbers with `grep -n "^\\\\section{" $TEX` before editing — they drift as content grows.

| Section | Anchor (current) | What to update |
|---------|------------------|----------------|
| Introduction | L449 | Overview, contributions |
| Data Preprocessing | L498 | Book representation pipeline |
| Tokenisation | L686 | Token encoding schemes |
| Model Architecture | L934 | GDN, NSA, SwiGLU, Mamba3 |
| Closed-Loop Inference | L1252 | Inference pipeline |
| Distributed Training | L1319 | Sharding, parallelism |
| Experimental Results | L1467 | Scaling law, per-ticker, MarS comparison |
| Post-Training | L2717 | DFM, GRPO, EggRoll ES |
| Agentic RL | L4883 | Post-training to agentic |
| **\appendix** | **L4992** | All appendix sections below this |
| GRPO Post-Training Scaling | L6160 | Companion eval data |

## 5-Level Time-Decay Revision Highlights (MANDATORY)

**Every edit MUST follow this protocol.** The paper preamble (L20-38) defines a 5-level green-fade highlight stack. Newest edit = brightest (L1), older revisions fade through L2-L5, then drop off.

### Macro stack (already defined in `quant2026.tex` preamble)

```latex
\hlnew{...}    % L1 NEWEST — vivid green   greenHL1 (RGB 80,210,80)
\hlLii{...}    % L2 — one revision back     greenHL2 (RGB 130,220,130)
\hlLiii{...}   % L3 — two revisions back    greenHL3 (RGB 170,230,170)
\hlLiv{...}    % L4 — three revisions back  greenHL4 (RGB 200,240,200)
\hlLv{...}     % L5 OLDEST — barely visible greenHL5 (RGB 225,250,225)
\hlgone{...}   % off the stack (pass-through, no highlight)
```

**IMPORTANT:** Command names MUST be all-letters (no digits). LaTeX tokenizer splits `\hlL2` into `\hlL` + `2`, causing compilation failure.

### Cascade rule — EVERY edit, BEFORE adding new wraps

Run this perl one-liner on the `.tex` file BEFORE you write new content. It downgrades every existing highlight by one level so the new edit can claim the L1 (brightest) slot exclusively.

```bash
perl -i -pe '
  s/\\hlLv\{/\\hlgone{/g;        # L5 oldest -> drop off the stack
  s/\\hlLiv\{/\\hlLv{/g;         # L4 -> L5
  s/\\hlLiii\{/\\hlLiv{/g;       # L3 -> L4
  s/\\hlLii\{/\\hlLiii{/g;       # L2 -> L3
  s/\\hlnew\{/\\hlLii{/g;        # L1 newest from prev edit -> L2
' "$TEX"
```

**Order matters.** If you do L2->L3 before L3->L4, you'll cascade the same content twice. Always go from oldest (L5) to newest (L1).

### 100% coverage rule

Every body paragraph in the new edit must be wrapped in `\hlnew{...}`. Even when the edit spans a full page. Headings and floats are exceptions:

| Element | Wrap in `\hlnew`? |
|---------|-------------------|
| Body paragraph (prose) | YES, every one |
| `\section{}`, `\subsection{}`, `\paragraph{}` titles | NO (breaks TOC) |
| Table cells (text/numbers or a single `$...$` block) | YES per cell with new value |
| Table cells with **two or more** adjacent `$...$` blocks | **NO** — use `\colorbox{greenHL1}{$...$}` (see caveat) |
| `\caption{}` text | YES |
| Display math `\begin{align}` | NO (use `\colorbox{greenHL1}{$...$}` if must mark) |
| Inline math `$...$` in body prose | YES, inside the `\hlnew{}` |
| `\cite{}`, `\ref{}` | YES (preamble has `\soulregister` for both) |
| Code listings `\begin{lstlisting}` | NO (soul incompatible) |

### Idiomatic patterns

```latex
% NEW PARAGRAPH (entire paragraph wrapped):
\hlnew{The Mamba3 SISO model achieves a final cross-entropy of $0.563$
on the 26-token GOOG validation set, $0.012$ below the AdamW baseline
trained with identical hyperparameters.}

% NEW TABLE ROW, one math block per cell (OK):
GOOG & \hlnew{$0.0438$} & \hlnew{$0.142$} & \hlnew{$0.572$} \\

% NEW TABLE ROW, TWO adjacent math blocks per cell (BROKEN — soul UL@on bug):
% BAD:  \hlnew{$0.2140^{\ast\ast\ast}$ $(0.0106)$}
% GOOD: \colorbox{greenHL1}{$0.2140^{\ast\ast\ast}\ (0.0106)$}   % single math span
% GOOD: \colorbox{greenHL1}{$0.2140^{\ast\ast\ast}$ $(0.0106)$}  % colorbox tolerates both

% PARTIAL EDIT inside an old paragraph (only the changed phrase):
\hlLiii{The base model is} \hlnew{a 78M-parameter Mamba3 SISO} \hlLiii{trained on 8 tickers.}
```

### Caveat: `\hlnew{$a$ $b$}` in table cells triggers soul `\UL@on` bug

Symptom (cascades across every row of the table):

```
Argument of \UL@on has an extra }.
Package soul Error: Reconstruction failed.
Paragraph ended before \UL@on was complete.
```

Root cause: `\hl`/`\hlnew`/`\sout` come from the `soul` package which parses contents character-by-character. Two adjacent `$...$` math spans separated by a space, inside a `\hlnew{}` that lives inside a table cell next to other cells with math, confuses soul's state machine. The error appears even though the same `\hlnew{$a$ $b$}` pattern works in body prose.

Workarounds, in order of preference:

1. **Merge the two math spans into one** with `\ ` or `\text{}`:
   `\hlnew{$0.2140^{\ast\ast\ast}\ (0.0106)$}` — one `$...$` block, works.

2. **Swap `\hlnew` for `\colorbox`** for that cell:
   `\colorbox{greenHL1}{$0.2140^{\ast\ast\ast}$ $(0.0106)$}` — colorbox has no soul machinery, tolerates multiple math spans.

3. **For mock/struck-through math**: `\colorbox{yellow!60}{$\sout{a\ b}$}` is equivalent to `\hl{\sout{$a$ $b$}}` and sidesteps the bug.

4. **For footnote markers**: prefer `\textsuperscript{m}` over `$^{\text{m}}$` in any cell that also uses soul commands; text-mode superscript doesn't perturb soul's parser.

### Type-diversity self-check (after every commit)

Run this to confirm the recent edit produces a visible time gradient:

```bash
for L in new Lii Liii Liv Lv; do
  count=$(grep -cE "\\\\hl${L}\\{" "$TEX")
  echo "hl${L}: ${count}"
done
```

A healthy paper after several revision rounds shows non-zero counts on at least 3 levels (L1, L2, L3). If you see only L1 and L5, the cascade is being skipped — fix the workflow.

### Update Patterns

Adding new eval results to a table:
```latex
\begin{table}[ht]
\centering
\caption{...}
\begin{tabular}{rrrr}
\toprule
Step & IC$_{h_{249}}$ & DA$_{h_{249}}$ & ... \\
\midrule
0 (SFT) & 0.190 & 57.1\% & baseline \\
5       & ... & ... & ... \\  % ← add new rows here
\bottomrule
\end{tabular}
\end{table}
```

Updating a paragraph with new numbers: find the paragraph, edit in-place. Don't duplicate content.

## Core Principles

1. **Mathematical derivations must use aligned equations**: When a derivation can be expanded, take the space and write it out step by step. Showing the derivation process actually improves the overall presentation.

2. **Annotate with horizontal braces**: Mathematical content must be written in LaTeX and annotated with `\underbrace{}` or `\overbrace{}`.

3. **Write in "zero-equals" aligned form**:
```latex
\begin{align}
    \text{Compute}
    &= \text{Steps}_{\text{day}} \times \text{FLOPs}_{\text{step}} \\
    &= \text{Steps}_{\text{day}} \times (6 \times B \times L \times M) \\
    &= \frac{1}{M} \times (6 \times 128 \times 4800 \times M) \\
    &= 6 \times 128 \times 4800.
\end{align}
```

## Formatting Rules

### Paragraphs (NOT lists)
- **`\begin{enumerate}` and `\begin{itemize}` are forbidden**
- All content must be written as coherent prose paragraphs
- Paragraphs must flow logically: the end of each paragraph must connect naturally to the beginning of the next

### No Em-Dashes
- **`---` (em-dash) is forbidden**
- Rewrite using commas, colons, parentheses, or separate clauses
- Exception: `---` in tables to indicate "no data"

### Algorithm Figures
- Provide `\begin{algorithm}` environment figures whenever possible
- Use the `algorithmic` or `algpseudocode` package
- Algorithm figures must clearly show inputs, outputs, loops, and conditionals

### Equation Style
- Multi-line equations use `align` or `aligned`
- Variable definitions use `\text{}` or `\mathrm{}`
- Annotate subscripts with meaning: `\theta_{\text{base}}`
- Important equations have `\label{eq:...}` and `\underbrace{}`

### TikZ Diagrams
- Use TikZ for flowcharts and comparison diagrams
- Nodes: `block/.style={rectangle, draw, rounded corners}`
- Arrows: `{-{Stealth[length=2.5mm]}, thick}`

## Template: Derivation Block

```latex
\paragraph{Gradient estimation.}
The EggRoll gradient at step~$t$ expands as follows.
For each perturbation direction~$i$ in the antithetic set
$\{+\varepsilon_i, -\varepsilon_i\}_{i=1}^{G/2}$, the fitness
score~$f_i$ measures the Pearson IC of the rollout.
The zeroth-order gradient estimate is then
\begin{align}
    \hat{g}_t
    &= \frac{1}{G}\sum_{i=1}^{G}
       \underbrace{f_i}_{\text{fitness}}
       \cdot
       \underbrace{\varepsilon_i}_{\text{perturbation}} \\
    &= \frac{1}{G}\sum_{j=1}^{G/2}
       \bigl(f_{2j} - f_{2j+1}\bigr)
       \cdot \varepsilon_j,
    \label{eq:es-gradient}
\end{align}
where the second line uses the antithetic identity
$\varepsilon_{2j} = -\varepsilon_{2j+1}$.
The variance reduction from antithetic sampling
scales as~$\mathcal{O}(1/G)$ rather than~$\mathcal{O}(1/\sqrt{G})$
for independent samples.
```

## Checklist Before Submitting

- [ ] No `\begin{itemize}` or `\begin{enumerate}` in body text
- [ ] No `---` (em-dash) in prose
- [ ] All multi-step math uses `align` with `&=` alignment
- [ ] Key terms annotated with `\underbrace{}`
- [ ] Paragraphs flow logically (each follows from the previous)
- [ ] At least one `\begin{algorithm}` if describing a procedure
- [ ] Labels on all referenced equations
- [ ] **Any new appendix section describing a model/pipeline/architecture MUST contain a figure** (reproduce from body with `\includegraphics` or add TikZ). Text-only + equations is not enough; reviewers expect a visual.
- [ ] **Cascade ran BEFORE adding new content**: `\hlnew->\hlL2`, `\hlL2->\hlL3`, ..., `\hlL5->\hlgone`
- [ ] **Every new body paragraph wrapped in `\hlnew{...}`** (100% coverage rule)
- [ ] **Type-diversity check passes**: at least 3 of {L1,L2,L3,L4,L5} have non-zero counts after a few rounds
- [ ] After push, **tell the user to Recompile on Overleaf** (changes are not visible until recompile; suggest "Recompile from scratch" if stale cache suspected)
