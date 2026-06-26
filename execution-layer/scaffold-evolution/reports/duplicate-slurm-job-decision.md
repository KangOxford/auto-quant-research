# Scaffold Evolution Decision Packet

Fixture: `incident.duplicate-slurm-job.public-demo`
Scenario suite: `duplicate-slurm-job.scenario-suite`
Fixture sha256: `5cdc25053d0e1cb4fe0ab0af60e5247d8a80c9663b1309a893d16238ce060eac`
Scenario-suite sha256: `40fde477d7231e3bb86270a75e43070d449b890c0fa3a7a1c74c4507c618b097`
Evaluator sha256: `109316d2bf0098ac2b38f8a62c6c07eb2b6bc3e3e96afb9527ae9523691c448f`

> This packet is a selection surface, not a scalar objective. Human review remains responsible for deciding whether the scenario suite is sufficient and whether the trade-off is acceptable.

## Review frontier

Non-dominated candidates for human review:
- `duplicate-guard.fingerprint-intent-checkpoint`

The frontier is not a winner set. It only removes candidates that are strictly worse across the visible trade-off dimensions.

## Scenario-suite risks

- no stale_rule_check scenario yet; future suites should test whether the rule should expire or narrow scope
- all scenarios have single acceptable decisions; consider adding ambiguity scenarios where escalate and block/allow are both defensible

## Candidate metrics

| Candidate | Passed scenarios | Unsafe silent passes | False blocks | Unexpected escalations | Errors | Hard failures | Behavior signature | Human verdict |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `duplicate-guard.fingerprint-intent-checkpoint` | 8/8 | 0 | 0 | 0 | 0 | 0 | `renamed_duplicate_running=block,same_name_different_config=allow,learning_rate_ablation=allow,fresh_start_with_checkpoint_chain=redirect_to_resume,missing_critical_metadata=escalate,mamba3_same_seed_duplicate=block,mamba3_seed_sweep=allow,mamba3_seed_change_without_intent=escalate` | pending |
| `duplicate-guard.name-only` | 2/8 | 5 | 1 | 0 | 0 | 5 | `renamed_duplicate_running=allow,same_name_different_config=block,learning_rate_ablation=allow,fresh_start_with_checkpoint_chain=allow,missing_critical_metadata=allow,mamba3_same_seed_duplicate=allow,mamba3_seed_sweep=allow,mamba3_seed_change_without_intent=allow` | pending |
| `duplicate-guard.strict-model-data` | 4/8 | 1 | 3 | 0 | 0 | 1 | `renamed_duplicate_running=block,same_name_different_config=allow,learning_rate_ablation=block,fresh_start_with_checkpoint_chain=allow,missing_critical_metadata=escalate,mamba3_same_seed_duplicate=block,mamba3_seed_sweep=block,mamba3_seed_change_without_intent=block` | pending |

## Scenario traces

### `duplicate-guard.fingerprint-intent-checkpoint`

A normalized experiment fingerprint, launch intent, and checkpoint-chain check prevents duplicate jobs without blocking legitimate ablations.

| Scenario | Role | Acceptable | Actual | Pass | Reason |
|---|---|---|---|---|---|
| `renamed_duplicate_running` | incident_regression | block | `block` | yes | live job synthetic-3260152 has the same full experiment fingerprint |
| `same_name_different_config` | negative_control | allow | `allow` | yes | no full-fingerprint duplicate or ignored checkpoint chain found |
| `learning_rate_ablation` | negative_control | allow | `allow` | yes | no full-fingerprint duplicate or ignored checkpoint chain found |
| `fresh_start_with_checkpoint_chain` | incident_prevention | redirect_to_resume | `redirect_to_resume` | yes | checkpoint chain synthetic-chain-mamba3-s42 matches full experiment fingerprint |
| `missing_critical_metadata` | adversarial_control | escalate | `escalate` | yes | missing critical config fields: token_mode, learning_rate |
| `mamba3_same_seed_duplicate` | distribution_shift | block | `block` | yes | live job synthetic-mamba3-001 has the same full experiment fingerprint |
| `mamba3_seed_sweep` | negative_control | allow | `allow` | yes | no full-fingerprint duplicate or ignored checkpoint chain found |
| `mamba3_seed_change_without_intent` | adversarial_control | escalate | `escalate` | yes | same experiment except seed without explicit replica/seed_sweep intent |

### `duplicate-guard.name-only`

Blocking duplicate job names is a cheap guard against accidental duplicate submissions.

| Scenario | Role | Acceptable | Actual | Pass | Reason |
|---|---|---|---|---|---|
| `renamed_duplicate_running` | incident_regression | block | `allow` | no | no live job has the same name |
| `same_name_different_config` | negative_control | allow | `block` | no | job name 'ctx-test' already exists |
| `learning_rate_ablation` | negative_control | allow | `allow` | yes | no live job has the same name |
| `fresh_start_with_checkpoint_chain` | incident_prevention | redirect_to_resume | `allow` | no | no live job has the same name |
| `missing_critical_metadata` | adversarial_control | escalate | `allow` | no | no live job has the same name |
| `mamba3_same_seed_duplicate` | distribution_shift | block | `allow` | no | no live job has the same name |
| `mamba3_seed_sweep` | negative_control | allow | `allow` | yes | no live job has the same name |
| `mamba3_seed_change_without_intent` | adversarial_control | escalate | `allow` | no | no live job has the same name |

### `duplicate-guard.strict-model-data`

Blocking any concurrent job with the same model/data fingerprint prevents duplicate compute waste.

| Scenario | Role | Acceptable | Actual | Pass | Reason |
|---|---|---|---|---|---|
| `renamed_duplicate_running` | incident_regression | block | `block` | yes | same model/data fingerprint is already running |
| `same_name_different_config` | negative_control | allow | `allow` | yes | no live job has the same model/data fingerprint |
| `learning_rate_ablation` | negative_control | allow | `block` | no | same model/data fingerprint is already running |
| `fresh_start_with_checkpoint_chain` | incident_prevention | redirect_to_resume | `allow` | no | no live job has the same model/data fingerprint |
| `missing_critical_metadata` | adversarial_control | escalate | `escalate` | yes | missing model/data fields: token_mode |
| `mamba3_same_seed_duplicate` | distribution_shift | block | `block` | yes | same model/data fingerprint is already running |
| `mamba3_seed_sweep` | negative_control | allow | `block` | no | same model/data fingerprint is already running |
| `mamba3_seed_change_without_intent` | adversarial_control | escalate | `block` | no | same model/data fingerprint is already running |

## Lineage

- `duplicate-guard.fingerprint-intent-checkpoint`: candidate record `bd988c95b97e6b8b7aed4136a33e3de5901505039cf932f69492946769b4bf6e`, parent id digest `7f65256f1e733965d8dec5def362f0862729a86ff5fcd9952df8ad902a1451a6`, target `execution-layer/skills/submit-job/SKILL.md`, target sha256 `eee7e6cb0bc2dd7a07721134d79d14dfcd9ea057c2247139e924f9dc47898ffc`
- `duplicate-guard.name-only`: candidate record `d3bc42d4894203acb89ceb9c7ab1198955454e24a4802f19f85f2590502cc4e6`, parent id digest `7f65256f1e733965d8dec5def362f0862729a86ff5fcd9952df8ad902a1451a6`, target `execution-layer/skills/submit-job/SKILL.md`, target sha256 `eee7e6cb0bc2dd7a07721134d79d14dfcd9ea057c2247139e924f9dc47898ffc`
- `duplicate-guard.strict-model-data`: candidate record `80a336913569694774d8e7193b2bf6b64412228381cbdcf9074f6af64156696f`, parent id digest `7f65256f1e733965d8dec5def362f0862729a86ff5fcd9952df8ad902a1451a6`, target `execution-layer/skills/submit-job/SKILL.md`, target sha256 `eee7e6cb0bc2dd7a07721134d79d14dfcd9ea057c2247139e924f9dc47898ffc`

## Archive recommendation

Keep every evaluated candidate as archive evidence. Rejected candidates with distinct behavior signatures are still useful stepping stones and future negative controls.

- `renamed_duplicate_running=block,same_name_different_config=allow,learning_rate_ablation=allow,fresh_start_with_checkpoint_chain=redirect_to_resume,missing_critical_metadata=escalate,mamba3_same_seed_duplicate=block,mamba3_seed_sweep=allow,mamba3_seed_change_without_intent=escalate`: `duplicate-guard.fingerprint-intent-checkpoint`
- `renamed_duplicate_running=allow,same_name_different_config=block,learning_rate_ablation=allow,fresh_start_with_checkpoint_chain=allow,missing_critical_metadata=allow,mamba3_same_seed_duplicate=allow,mamba3_seed_sweep=allow,mamba3_seed_change_without_intent=allow`: `duplicate-guard.name-only`
- `renamed_duplicate_running=block,same_name_different_config=allow,learning_rate_ablation=block,fresh_start_with_checkpoint_chain=allow,missing_critical_metadata=escalate,mamba3_same_seed_duplicate=block,mamba3_seed_sweep=block,mamba3_seed_change_without_intent=block`: `duplicate-guard.strict-model-data`

## Human verdict

- Verdict: pending
- Validity scope accepted: pending
- Rollback target accepted: pending
- Scenario-suite gaps to add before future reuse: pending
