---
name: finding-lobbench-results
description: Use when asked to find existing LOBbench results for a checkpoint, SLURM job, wandb run, or experiment — before submitting a new bench job. Symptoms: "any lob bench results for X", "has this been benchmarked", "find WS-21/IC/DirAcc for checkpoint Y", "show me the LOBbench for run Z", "is there a bench already for job N".
---

# Finding LOBbench Results

## Overview

LOBbench results for a checkpoint often **already exist** in the pipeline `results_*` directories — usually run by Aramis. Running a new bench job wastes 1+ GPU-hours per ticker when the data is already there. **Always search existing results before invoking `/bench`.**

## Core Principle

**Search order is not optional.** Checking `agent_outputs/` first saves the most time: if someone has already analyzed this run, they left the exact path + a CSV of extracted metrics. Pipeline directories are the raw-data fallback.

```
User asks → agent_outputs/ → kangli lob_pipeline → aramis lob_pipeline → conclude "none exist"
```

## Discovery Steps

### Step 1 — Resolve the 3 identifiers

Every LOBbench run can be keyed by any of these. Given one, derive the others:

| Given | How to get the rest |
|-------|---------------------|
| Checkpoint dir `j<JOBID>_<WANDB_ID>_<JOBID>` | Parse the name — `JOBID` and `WANDB_ID` are embedded |
| SLURM Job ID | Use `find-wandb` skill to get wandb run ID + step + config |
| Wandb run ID | `find wandb/ -name "*<WANDB_ID>*"` to locate metadata |
| Experiment name (e.g. "mamba3 78M") | Look up in `experiments/exp_*/agent_outputs/` or `wandb-metadata.json` |

Always resolve the **checkpoint step** — results dirs embed it as `s<STEP>` (e.g. `s46050`).

### Step 2 — Check `agent_outputs/` FIRST

This is the highest-ROI search. If anyone on the team analyzed this run, they wrote a `.md` summary + a `.csv` of extracted metrics pointing at the exact pipeline dirs.

```bash
EXP=/lus/lfs1aip2/projects/s5e/quant/AlphaTrade/experiments/exp_<NAME>
ls "$EXP/agent_outputs/" | grep -iE "lobbench|bench|h250|h500|result|multiticker"
```

Look for:
- `*_lobbench.md` — narrative analysis with table of metrics
- `*_h250.csv` / `*_h500.csv` — pre-extracted metrics (ready to read)
- `phase_*_results.md` — ablation-style LOBbench comparisons

### Step 3 — Search both `lob_pipeline/` locations

There are **two** pipelines. Check both (read-only in either is fine):

| Location | Contents |
|----------|----------|
| `~/AlphaTrade/lob_pipeline/` (kangli clone) | Usually has kangli's runs; MUST be used for **running** new inference |
| `/lus/lfs1aip2/projects/s5e/lob_pipeline/` (aramis) | Usually has aramis's runs — **most Mamba3/scaling-law results live here** |

```bash
# Search both locations in parallel
for PIPE in ~/AlphaTrade/lob_pipeline /lus/lfs1aip2/projects/s5e/lob_pipeline; do
  ls "$PIPE/" 2>/dev/null | grep -iE "<MODEL_TAG>|s<STEP>|<WANDB_ID>|<JOBID>"
done
```

**CLAUDE.md caveat**: the "only use kangli clone" rule is about **submitting new jobs**, not reading existing pickles. Reading aramis's `results_*/scores_clean/*.pkl` is allowed.

### Step 4 — Decode the results directory naming

The pipeline follows consistent conventions. Parsing the dirname tells you the full config without opening files:

| Pattern | Meaning |
|---------|---------|
| `results_ext-<name>-s<STEP>-c<C>g<G>` | **Extended** eval (uncond + cond + divergence + context + downstream). `ext-` = full suite. |
| `results_<name>-s<STEP>-<TICKER>-c<C>g<G>-v2` | Single-ticker multi-ticker generalization run |
| `results_<name>-<SIZE>-s<STEP>-c<C>g<G>` | Scaling-law run (e.g., `mamba3-14m-s13700-c250g250`) |
| `results_<name>-<cfg>-TSLA` (etc.) | Ticker-specific rerun |
| `c<C>g<G>` | `C`=conditioning msgs, `G`=generated msgs. `c250g250` = h250 horizon. `c500g500` = h500. |

### Step 5 — Inside each results dir

```
results_<NAME>/
├─ scores/          # raw bootstrap pickles (101 resamples)
├─ scores_clean/    # outlier-cleaned pickles — use these for reporting
└─ plots/           # PNG histograms + summary_stats_all.png
```

Pickle naming: `scores_{cond,uncond,div,context,time_lagged}_<TICKER>_<NAME>_integrated_<JOBID>.pkl`

### Step 6 — Extract metrics

If the `agent_outputs/*.csv` exists, read it directly — already has columns `ws_mean/lo/hi, ks_*, l1_*, ic_sp_*, ic_pe_*, diracc, sharpe`. Otherwise `pd.read_pickle(scores_clean/...)`.

**Pearson IC only** (per user preference): use column `ic_pe_mean`, not `ic_sp_mean`. CSVs carry both.

## Quick Reference

| Task | Command |
|------|---------|
| Find by job ID | `find /lus/lfs1aip2/projects/s5e/lob_pipeline ~/AlphaTrade/lob_pipeline -maxdepth 2 -name "*<JOBID>*"` |
| Find by step | `ls */lob_pipeline/ \| grep "s<STEP>"` |
| Find agent analysis | `ls experiments/exp_*/agent_outputs/ \| grep -iE "bench\|result"` |
| Resolve wandb → jobid | use `find-wandb` skill |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Searching only `~/AlphaTrade/lob_pipeline/` | Aramis runs most Mamba3/scaling-law benches. Also search `/lus/lfs1aip2/projects/s5e/lob_pipeline/`. |
| Reporting Spearman IC | User wants **Pearson** (`ic_pe_*`). Always grep CSV columns. |
| Opening `scores/` (raw) pickles | Use `scores_clean/` for reporting — outliers removed. |
| Running `/bench` without checking first | Wastes 1+ GPU-hour/ticker. `agent_outputs/` check takes 10 seconds. |
| Confusing `c250g250` vs `c500g500` | These are **different horizons** (h250 vs h500). Never mix numbers from different dirs. |
| Assuming "no results" from partial search | Search all 3 keys (JOBID, WANDB_ID, step) AND both pipelines AND `agent_outputs/`. |

## Report Format

When returning results, always provide:

1. **Directory paths** — full absolute paths (user rule: no relative paths)
2. **Metrics table** — WS-21 / KS-21 / L1-21 / **IC Pearson** / DirAcc / Sharpe
3. **Horizon** — h250 vs h500, noted explicitly
4. **Source** — which CSV or pickle; which SLURM job produced the inference
5. **Related analysis files** — list of `agent_outputs/*.md` that discuss this run

## When to Escalate to `/bench`

Only after confirming **all** of the following fail:

- [ ] No matching `agent_outputs/*lobbench*.md`
- [ ] No `results_*` dir in kangli clone matching name/step/jobid/wandb
- [ ] No `results_*` dir in aramis pipeline matching name/step/jobid/wandb
- [ ] User wants a ticker/horizon that isn't in existing results

Then use `/bench` per the bench skill. Runs in kangli clone only.
