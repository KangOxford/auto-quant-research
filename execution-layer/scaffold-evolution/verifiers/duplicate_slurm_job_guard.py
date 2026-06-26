#!/usr/bin/env python3
"""Duplicate-job verifier for the current normalized experiment metadata shape."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable

MODEL_DATA_FIELDS = (
    "model_family",
    "ssm_type",
    "d_model",
    "n_layers",
    "ssm_size_base",
    "blocks",
    "token_mode",
    "dataset",
)
TRAINING_FIELDS = (
    "msg_seq_len",
    "batch_size",
    "optimizer",
    "learning_rate",
    "wandb_project",
)
SEED_FIELDS = ("seed",)
FULL_FINGERPRINT_FIELDS = (*MODEL_DATA_FIELDS, *TRAINING_FIELDS, *SEED_FIELDS)

ABLATION_INTENTS = {"ablation", "sweep", "robustness"}
SEED_SWEEP_INTENTS = {"replica", "seed_sweep"}


class VerifierError(ValueError):
    pass


@dataclass(frozen=True)
class Decision:
    value: str
    reason: str

    def to_json(self) -> dict[str, str]:
        return {"decision": self.value, "reason": self.reason}


@dataclass(frozen=True)
class DuplicateGuardCandidate:
    strategy: str


@dataclass(frozen=True)
class DuplicateGuardScenario:
    pending_submission: dict[str, Any]
    live_jobs: list[dict[str, Any]]
    checkpoint_chains: list[dict[str, Any]]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require_mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VerifierError(f"{where}: expected object")
    return value


def require_list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise VerifierError(f"{where}: expected array")
    return value


def parse_candidate(record: dict[str, Any]) -> DuplicateGuardCandidate:
    implementation = require_mapping(record.get("implementation"), "candidate.implementation")
    if implementation.get("kind") != "duplicate_job_guard":
        raise VerifierError(f"unsupported candidate kind: {implementation.get('kind')!r}")
    strategy = implementation.get("strategy")
    if not isinstance(strategy, str):
        raise VerifierError("candidate.implementation.strategy: expected string")
    return DuplicateGuardCandidate(strategy=strategy)


def parse_case(case: dict[str, Any], where: str = "scenario.case") -> DuplicateGuardScenario:
    pending = require_mapping(case.get("pending_submission"), f"{where}.pending_submission")
    live_jobs = [require_mapping(job, f"{where}.live_jobs[]") for job in require_list(case.get("live_jobs", []), f"{where}.live_jobs")]
    checkpoint_chains = [
        require_mapping(chain, f"{where}.checkpoint_chains[]")
        for chain in require_list(case.get("checkpoint_chains", []), f"{where}.checkpoint_chains")
    ]
    return DuplicateGuardScenario(
        pending_submission=pending,
        live_jobs=live_jobs,
        checkpoint_chains=checkpoint_chains,
    )


def parse_scenario(record: dict[str, Any]) -> DuplicateGuardScenario:
    return parse_case(require_mapping(record.get("case"), "scenario.case"))


def normalize_decimal(value: Any) -> Any:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return value
    return format(parsed.normalize(), "f")


def normalize_optimizer(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", "", value.strip().lower())


def normalize_token_mode(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return re.sub(r"^token_mode\s*=\s*", "", value.strip().lower())


def normalize_seed(value: Any) -> Any:
    try:
        return str(int(str(value).strip()))
    except (TypeError, ValueError):
        return value


def normalize_tickers(value: Any) -> Any:
    if isinstance(value, str):
        raw = [part for part in re.split(r"[,\s]+", value) if part]
    elif isinstance(value, list):
        raw = value
    else:
        return value
    return sorted({str(item).strip().upper() for item in raw if str(item).strip()})


def normalize_field(field: str, value: Any) -> Any:
    if field == "learning_rate":
        return normalize_decimal(value)
    if field == "optimizer":
        return normalize_optimizer(value)
    if field == "token_mode":
        return normalize_token_mode(value)
    if field == "seed":
        return normalize_seed(value)
    if field == "tickers":
        return normalize_tickers(value)
    if isinstance(value, dict):
        return {key: normalize_field(key, nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [normalize_field(field, item) for item in value]
    if isinstance(value, (int, float)):
        return normalize_decimal(value)
    if isinstance(value, str):
        return value.strip().lower()
    return value


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    return {field: normalize_field(field, value) for field, value in config.items()}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def missing_config_fields(config: dict[str, Any], fields: Iterable[str]) -> list[str]:
    return [field for field in fields if field not in config or config[field] in (None, "", [])]


def fingerprint(config: dict[str, Any], fields: Iterable[str]) -> tuple[tuple[str, str], ...]:
    normalized = normalize_config(config)
    return tuple((field, canonical(normalized.get(field))) for field in fields)


def same_fingerprint(a: dict[str, Any], b: dict[str, Any], fields: Iterable[str]) -> bool:
    return fingerprint(a, fields) == fingerprint(b, fields)


def material_train_diffs(a: dict[str, Any], b: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
    diffs: dict[str, tuple[Any, Any]] = {}
    normalized_a = normalize_config(a)
    normalized_b = normalize_config(b)
    for field in (*TRAINING_FIELDS, *SEED_FIELDS):
        if canonical(normalized_a.get(field)) != canonical(normalized_b.get(field)):
            diffs[field] = (a.get(field), b.get(field))
    return diffs


def seed_only(diffs: dict[str, tuple[Any, Any]]) -> bool:
    return bool(diffs) and set(diffs) <= set(SEED_FIELDS)


def decision(value: str, reason: str) -> Decision:
    return Decision(value, reason)


def config_from(record: dict[str, Any], where: str) -> dict[str, Any]:
    return require_mapping(record.get("config"), f"{where}.config")


def job_label(job: dict[str, Any]) -> str:
    return str(job.get("job_id", "<unknown>"))


def decide_name_only(scenario: DuplicateGuardScenario) -> Decision:
    pending_name = scenario.pending_submission.get("job_name")
    for job in scenario.live_jobs:
        if job.get("job_name") == pending_name:
            return decision("block", f"job name {pending_name!r} already exists")
    return decision("allow", "no live job has the same name")


def decide_strict_model_data(scenario: DuplicateGuardScenario) -> Decision:
    pending_config = config_from(scenario.pending_submission, "scenario.case.pending_submission")
    missing = missing_config_fields(pending_config, MODEL_DATA_FIELDS)
    if missing:
        return decision("escalate", f"missing model/data fields: {', '.join(missing)}")

    for job in scenario.live_jobs:
        job_config = config_from(job, "scenario.case.live_jobs[]")
        if same_fingerprint(pending_config, job_config, MODEL_DATA_FIELDS):
            return decision("block", "same model/data fingerprint is already running")
    return decision("allow", "no live job has the same model/data fingerprint")


def decide_fingerprint_intent_checkpoint(scenario: DuplicateGuardScenario) -> Decision:
    pending_config = config_from(scenario.pending_submission, "scenario.case.pending_submission")
    pending_intent = normalize_field("intent", scenario.pending_submission.get("intent", ""))

    missing = missing_config_fields(pending_config, FULL_FINGERPRINT_FIELDS)
    if missing:
        return decision("escalate", f"missing critical config fields: {', '.join(missing)}")

    if pending_intent == "fresh_start":
        for chain in scenario.checkpoint_chains:
            chain_config = config_from(chain, "scenario.case.checkpoint_chains[]")
            if not missing_config_fields(chain_config, FULL_FINGERPRINT_FIELDS) and same_fingerprint(pending_config, chain_config, FULL_FINGERPRINT_FIELDS):
                return decision("redirect_to_resume", f"checkpoint chain {chain.get('chain_id', '<unknown>')} matches full experiment fingerprint")

    for job in scenario.live_jobs:
        job_config = config_from(job, "scenario.case.live_jobs[]")
        job_missing = missing_config_fields(job_config, FULL_FINGERPRINT_FIELDS)
        if job_missing:
            return decision("escalate", f"live job {job_label(job)} is missing metadata: {', '.join(job_missing)}")

        if same_fingerprint(pending_config, job_config, FULL_FINGERPRINT_FIELDS):
            return decision("block", f"live job {job_label(job)} has the same full experiment fingerprint")

        if same_fingerprint(pending_config, job_config, MODEL_DATA_FIELDS):
            diffs = material_train_diffs(pending_config, job_config)
            if seed_only(diffs):
                if pending_intent in SEED_SWEEP_INTENTS:
                    continue
                return decision("escalate", "same experiment except seed without explicit replica/seed_sweep intent")
            if pending_intent in ABLATION_INTENTS and diffs:
                continue
            return decision("escalate", "same model/data but changed training fields without explicit ablation/sweep intent")

    return decision("allow", "no full-fingerprint duplicate or ignored checkpoint chain found")


Strategy = Callable[[DuplicateGuardScenario], Decision]

STRATEGIES: dict[str, Strategy] = {
    "name_only": decide_name_only,
    "strict_model_data": decide_strict_model_data,
    "fingerprint_intent_checkpoint": decide_fingerprint_intent_checkpoint,
}


def verify(candidate: DuplicateGuardCandidate, scenario: DuplicateGuardScenario) -> Decision:
    strategy_fn = STRATEGIES.get(candidate.strategy)
    if strategy_fn is None:
        return decision("error", f"unknown duplicate-job strategy: {candidate.strategy!r}")
    return strategy_fn(scenario)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify one duplicate-job candidate against one scenario or normalized job case.")
    parser.add_argument("--candidate", help="Candidate JSON path")
    parser.add_argument("--scenario", help="Scenario JSON path")
    parser.add_argument("--input", help="Normalized job-case JSON path for direct local checks")
    parser.add_argument("--strategy", default="fingerprint_intent_checkpoint", help="Strategy for --input mode")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.input:
            payload = require_mapping(load_json(Path(args.input)), "input")
            candidate = DuplicateGuardCandidate(strategy=args.strategy)
            scenario = parse_case(require_mapping(payload.get("case", payload), "input.case"), "input.case")
        else:
            if not args.candidate or not args.scenario:
                raise VerifierError("--candidate and --scenario are required unless --input is used")
            candidate = parse_candidate(require_mapping(load_json(Path(args.candidate)), "candidate"))
            scenario = parse_scenario(require_mapping(load_json(Path(args.scenario)), "scenario"))
        result = verify(candidate, scenario)
    except (OSError, json.JSONDecodeError, VerifierError) as exc:
        result = decision("error", str(exc))
    print(json.dumps(result.to_json(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
