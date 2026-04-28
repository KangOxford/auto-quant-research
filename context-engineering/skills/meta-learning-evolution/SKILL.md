---
name: meta-learning-evolution
description: Design meta-learning systems that evolve code/configs (loss functions, reward functions, hyperparams) using GA and/or LLM proposals. Covers when to use GA vs LLM, prompt design, and experiment structure.
version: 1.0.0
allowed-tools: Bash, Write, Read, Edit, Agent
alwaysApply: false
---

# Meta-Learning Evolution Design

## When to Use

- Evolving loss functions, reward functions, or training configs
- Using LLM to generate code that gets evaluated automatically
- Any "outer loop optimizes inner loop" setup (AutoML, NAS, etc.)
- User mentions "meta-learning", "evolve", "auto-discover", "search for optimal"

## Tool Selection: GA vs LLM

**Critical insight: LLM and GA excel at different sub-tasks. Using the wrong tool causes failure.**

| Task | Best Tool | Why |
|------|-----------|-----|
| Invent new concepts (e.g. "use Sortino instead of Sharpe") | **LLM** | Requires domain knowledge + creativity |
| Optimize weights/combinations of known components | **GA** | Structured numerical search, no API cost |
| Curriculum scheduling / hyperparameter tuning | **Grid search or GA** | Low-dimensional continuous optimization |
| Generate arbitrary Python code | **LLM** | Can create novel functions |

**Anti-pattern**: Using LLM for weight optimization. It will anchor on the first success and produce 20 near-identical variants (exploration collapse).

## LLM Proposal Prompt Design (Learned the Hard Way)

### Must Include
1. **Source code of top-K winners** (not just names + scores)
2. **Explicit failed patterns** with reasons
3. **Diversity pressure** after N failed rounds: list 5+ fundamentally different directions

### Must NOT
- Show only leaderboard table without code (LLM can't learn from names)
- Rely on "try something different" instruction (LLM interprets this as "minor variant")
- Let LLM optimize weights (it will hallucinate "0.7 should be 0.8")

## GA Genome Design for Code Evolution

Represent code as structured genomes, not raw strings:

```python
genome = {
    "terms": [
        {"name": "pnl", "weight": 1.0, "sign": -1},      # maximize
        {"name": "sortino", "weight": 0.5, "sign": -1},
    ],
    "curriculum": {"enabled": False, "rate": 0.2},
    "temperature": 100.0,
}
```

Then `genome_to_code(genome)` generates the actual function. This makes crossover/mutation well-defined.

## Two-Level Evolution (Best of Both)

```
Level 1 (GA): optimize weights + combinations of known primitives
  → runs every generation, no API needed
Level 2 (LLM): invent new primitives when GA stagnates
  → runs only on stagnation, expensive but creative
```

Stagnation = no improvement for N generations. LLM invents 1-2 new terms, which get injected into GA's vocabulary.

## Experiment Structure: 2x2 Matrix

When comparing search method × domain, always run independently:

```
           Model A    Model B
GA         Job 1      Job 2
LLM        Job 3      Job 4
```

Do NOT combine into one fitness (e.g. mean of both models). Run separately, then cross-evaluate winners.

## Key Findings from Practice

1. **winrate_margin (hinge loss)** was the #1 discovery. GA found it; LLM never explored it. Hinge loss provides sharper gradient signal than smooth tanh for direction prediction.
2. **No curriculum needed**: GA found that curriculum scheduling (LLM's key "insight") was unnecessary. The curriculum just delayed convergence.
3. **3 tickers is enough for Stage 1**: AMZN (easy), BLK (hard), APA (medium) provides diverse signal. Full 31-ticker eval only for top candidates.

## Verification

- GA best SR should exceed hand-designed baselines within 2-3 generations
- LLM should produce diverse proposals (check name diversity, not just SR)
- Cross-model evaluation: best loss from Model A should also improve Model B
