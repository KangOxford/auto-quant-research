# Scaffold Evolution Lab

Optional, local selection packets for durable changes to the Auto Quant Research scaffold.

The existing scaffold already has mutation paths: sessions produce lessons, `claudeception` extracts reusable skills, and hooks can make edits low-friction. This directory handles the selection side only. It does not generate new rules and it does not approve them automatically.

## Quick Start

From the repository root:

```bash
python3 -m unittest discover execution-layer/scaffold-evolution/tests
python3 execution-layer/scaffold-evolution/run.py --suite duplicate-slurm-job.scenario-suite
```

The generated demo packet is written to:

```text
execution-layer/scaffold-evolution/reports/duplicate-slurm-job-decision.md
```

Expected result: the name-only and strict model/data guards expose different failure modes, while the fingerprint + intent + checkpoint-chain guard prevents the duplicate-job incident without blocking declared ablations or seed sweeps.

## Selection Packet

A packet records the evidence around a proposed scaffold mutation:

- origin incident or rationale;
- replayable scenarios with incident, negative-control, adversarial, stale-rule, or distribution-shift roles;
- candidate lineage, rollback target, and exact hashes;
- verifier trace for each scenario;
- hard-failure and trade-off metrics;
- non-dominated review frontier;
- scenario-suite risk notes;
- human verdict placeholder.

The evaluator is intentionally generic. Domain logic lives in verifier scripts registered in `suite-registry.json`, so new scaffold domains add scenario suites and verifiers instead of adding branches to `evaluate.py`.

## Why This Is Not A Fixed Objective

The harness does not emit one scalar fitness value. It emits a review surface over a scenario suite. A suite should contain counterexamples beside the incident case so the scaffold does not overfit one memorable failure.

Rejected candidates are kept when they expose distinct behavior. They are useful as archived stepping stones and future negative controls.

## Duplicate Slurm Job Fixture

The first fixture is derived from the public `submit-job` skill. That skill records a duplicate-job failure where a fresh start and a resume of the same experiment ran in parallel for 13 hours, wasting 208 node-hours.

The fixture is synthetic and redacted. It does not call `squeue`; it replays current normalized Mamba3/LOBS5/26tok/Muon+AdamW metadata records.

## Optional Submit-Job Check

If normalized job metadata is available before `sbatch`, the duplicate guard can be run directly:

```bash
python3 execution-layer/scaffold-evolution/verifiers/duplicate_slurm_job_guard.py \
  --input /path/to/normalized-job-case.json \
  --strategy fingerprint_intent_checkpoint
```

The input may be either a scenario-like object with `case`, or the case object itself with `pending_submission`, `live_jobs`, and `checkpoint_chains`.

## Stop Hook

`execution-layer/hooks/scaffold-evolution-stop.sh` is the Stop-hook path for refreshing scenario-suite packets after relevant scaffold changes. Wire it into the active Claude hooks directory and `Stop` hook list with:

```json
{
  "type": "command",
  "command": "bash ${HOME}/.claude/hooks/scaffold-evolution-stop.sh",
  "timeout": 30
}
```

The hook hashes the relevant dirty diff and file content before running, ignores generated reports, and routes changed paths through `suite-registry.json`.

## Private Verifiers

Private data, model code, credentials, checkpoints, and cluster paths should stay out of the public repo. A private verifier can still participate as a local black-box command that receives candidate and scenario paths and writes:

```json
{"decision": "block", "reason": "same checkpoint lineage is already running"}
```

The same seam can later wrap market-world-model checks such as deterministic replay, no-op interventions, mechanical book validity, counterfactual provenance, queue reactivity, and response stress. Those verifiers should remain local unless their fixtures are safe to publish.
