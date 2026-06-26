#!/usr/bin/env python3
"""Local selection harness for incident-grounded scaffold evolution.

The evaluator is intentionally domain-neutral: it loads a scenario suite,
runs proposed candidates through a verifier command, and emits a review packet.
Domain logic belongs in verifier scripts, not in this evaluator.

Standard library only. Network-free by default; verifier commands are supplied
explicitly by the scenario-suite registry or by the caller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DECISIONS = {"allow", "block", "redirect_to_resume", "escalate", "error", "skipped"}


class HarnessError(ValueError):
    pass


@dataclass(frozen=True)
class CandidateRecord:
    path: Path
    data: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "CandidateRecord":
        data = require_mapping(load_json(path), f"candidate:{path}")
        require_fields(data, ("candidate_id", "parent_id", "target", "hypothesis", "implementation"), "candidate")
        return cls(path=path, data=data)

    @property
    def candidate_id(self) -> str:
        return str(self.data["candidate_id"])

    @property
    def parent_id(self) -> str:
        return str(self.data["parent_id"])

    @property
    def target(self) -> str:
        return str(self.data["target"])

    @property
    def hypothesis(self) -> str:
        return str(self.data["hypothesis"])


@dataclass(frozen=True)
class ScenarioRecord:
    data: dict[str, Any]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ScenarioRecord":
        require_fields(data, ("scenario_id", "case", "acceptable_decisions"), "scenario")
        return cls(data=data)

    @property
    def scenario_id(self) -> str:
        return str(self.data["scenario_id"])

    @property
    def role(self) -> str:
        return str(self.data.get("role", "scenario"))

    @property
    def acceptable_decisions(self) -> set[str]:
        return {str(decision) for decision in self.data["acceptable_decisions"]}


@dataclass(frozen=True)
class Decision:
    value: str
    reason: str

    @classmethod
    def error(cls, reason: str) -> "Decision":
        return cls("error", reason)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Decision":
        value = payload.get("decision")
        if value not in DECISIONS:
            return cls.error(f"verifier emitted invalid decision: {value!r}")
        return cls(value=str(value), reason=str(payload.get("reason", "verifier")))


def stable_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(stable_json(value))


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise HarnessError(f"{path}: invalid JSON: {exc}") from exc


def require_mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HarnessError(f"{where}: expected object")
    return value


def require_fields(obj: dict[str, Any], fields: Iterable[str], where: str) -> None:
    missing = [field for field in fields if field not in obj]
    if missing:
        raise HarnessError(f"{where}: missing required fields: {', '.join(missing)}")


def verifier_argv(verifier_command: str | list[str], candidate_path: Path, fixture_path: Path, scenario_path: Path) -> list[str]:
    if isinstance(verifier_command, str):
        try:
            loaded = json.loads(verifier_command)
        except json.JSONDecodeError:
            loaded = shlex.split(verifier_command)
    else:
        loaded = verifier_command
    if not isinstance(loaded, list) or not all(isinstance(item, str) for item in loaded):
        raise HarnessError("verifier command must be a string or JSON array of strings")
    placeholders = {
        "{candidate}": str(candidate_path),
        "{fixture}": str(fixture_path),
        "{scenario}": str(scenario_path),
    }
    return [replace_placeholders(item, placeholders) for item in loaded]


def replace_placeholders(value: str, placeholders: dict[str, str]) -> str:
    for placeholder, replacement in placeholders.items():
        value = value.replace(placeholder, replacement)
    return value


def run_verifier(
    verifier_command: str | list[str],
    candidate: CandidateRecord,
    fixture_path: Path,
    scenario: ScenarioRecord,
    timeout: int,
) -> Decision:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as scenario_file:
        json.dump(scenario.data, scenario_file, sort_keys=True)
        scenario_path = Path(scenario_file.name)

    try:
        completed = subprocess.run(
            verifier_argv(verifier_command, candidate.path, fixture_path, scenario_path),
            shell=False,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            return Decision.error(f"verifier exited {completed.returncode}: {completed.stderr.strip()[:300]}")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            return Decision.error(f"verifier did not emit JSON: {exc}")
        if not isinstance(payload, dict):
            return Decision.error("verifier output: expected object")
        return Decision.from_payload(payload)
    finally:
        try:
            scenario_path.unlink()
        except OSError:
            pass


def evaluate_candidate(
    candidate: CandidateRecord,
    scenarios: list[ScenarioRecord],
    fixture: dict[str, Any],
    fixture_path: Path,
    verifier_command: str | list[str],
    verifier_timeout: int,
) -> dict[str, Any]:
    traces: list[dict[str, Any]] = []
    metrics = {
        "scenarios": len(scenarios),
        "passed_acceptable_decision": 0,
        "unsafe_silent_passes": 0,
        "false_blocks": 0,
        "unexpected_escalations": 0,
        "errors": 0,
        "skipped": 0,
    }

    for scenario in scenarios:
        decision = run_verifier(verifier_command, candidate, fixture_path, scenario, verifier_timeout)
        acceptable = scenario.acceptable_decisions
        passed = decision.value in acceptable
        if passed:
            metrics["passed_acceptable_decision"] += 1
        if decision.value == "allow" and "allow" not in acceptable:
            metrics["unsafe_silent_passes"] += 1
        if decision.value == "block" and "block" not in acceptable:
            metrics["false_blocks"] += 1
        if decision.value == "escalate" and "escalate" not in acceptable:
            metrics["unexpected_escalations"] += 1
        if decision.value == "error":
            metrics["errors"] += 1
        if decision.value == "skipped":
            metrics["skipped"] += 1
        traces.append({
            "scenario_id": scenario.scenario_id,
            "role": scenario.role,
            "acceptable_decisions": sorted(acceptable),
            "actual_decision": decision.value,
            "passed_acceptable_decision": passed,
            "reason": decision.reason,
        })

    hard_failures = metrics["unsafe_silent_passes"] + metrics["errors"]
    target = candidate.target
    target_path = Path(target)
    target_sha = sha256_bytes(target_path.read_bytes()) if target_path.exists() else None
    result = {
        "candidate_id": candidate.candidate_id,
        "candidate_record_sha256": sha256_json(candidate.data),
        "hypothesis": candidate.hypothesis,
        "lineage": {
            "parent_id": candidate.parent_id,
            "parent_id_digest": sha256_bytes(candidate.parent_id.encode("utf-8")),
            "target": target,
            "target_sha256": target_sha,
            "rollback": candidate.data.get("rollback", {}),
        },
        "metrics": metrics,
        "hard_failures": hard_failures,
        "traces": traces,
        "human_verdict": "pending",
    }
    result["behavior_signature"] = behavior_signature(result)
    return result


def tradeoff_vector(result: dict[str, Any]) -> tuple[int, int, int, int, int, int, int]:
    """Return a trade-off vector. Lower is better in every dimension."""
    metrics = result["metrics"]
    return (
        result["hard_failures"],
        metrics["unsafe_silent_passes"],
        metrics["false_blocks"],
        metrics["unexpected_escalations"],
        metrics["errors"],
        metrics["skipped"],
        -metrics["passed_acceptable_decision"],
    )


def dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_vec = tradeoff_vector(left)
    right_vec = tradeoff_vector(right)
    return all(l <= r for l, r in zip(left_vec, right_vec)) and any(l < r for l, r in zip(left_vec, right_vec))


def choose_review_frontier(candidate_results: list[dict[str, Any]]) -> list[str]:
    """Return the non-dominated candidate set for human review."""
    frontier: list[str] = []
    for candidate in candidate_results:
        if not any(dominates(other, candidate) for other in candidate_results if other is not candidate):
            frontier.append(candidate["candidate_id"])
    return frontier


def behavior_signature(result: dict[str, Any]) -> str:
    return ",".join(f"{trace['scenario_id']}={trace['actual_decision']}" for trace in result["traces"])


def distinct_behavior_archive(candidate_results: list[dict[str, Any]]) -> dict[str, list[str]]:
    archive: dict[str, list[str]] = {}
    for candidate in candidate_results:
        archive.setdefault(candidate["behavior_signature"], []).append(candidate["candidate_id"])
    return archive


def scenario_suite_risks(fixture: dict[str, Any]) -> list[str]:
    """Return non-fatal risk notes for the current scenario suite."""
    scenarios = fixture["scenario_suite"]["scenarios"]
    roles = {scenario.get("role", "scenario") for scenario in scenarios}
    risks: list[str] = []
    required_roles = {"incident_regression", "negative_control", "adversarial_control"}
    missing_required = sorted(required_roles - roles)
    if missing_required:
        risks.append(f"missing recommended scenario roles: {', '.join(missing_required)}")
    if "stale_rule_check" not in roles:
        risks.append("no stale_rule_check scenario yet; future suites should test whether the rule should expire or narrow scope")
    if "distribution_shift" not in roles:
        risks.append("no distribution_shift scenario yet; future suites should test changed infrastructure or changed experiment taxonomy")
    if not any(len(scenario.get("acceptable_decisions", [])) > 1 for scenario in scenarios):
        risks.append("all scenarios have single acceptable decisions; consider adding ambiguity scenarios where escalate and block/allow are both defensible")
    return risks


def render_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Scaffold Evolution Decision Packet")
    lines.append("")
    lines.append(f"Fixture: `{result['fixture_id']}`")
    lines.append(f"Scenario suite: `{result['scenario_suite_id']}`")
    lines.append(f"Fixture sha256: `{result['fixture_sha256']}`")
    lines.append(f"Scenario-suite sha256: `{result['scenario_suite_sha256']}`")
    lines.append(f"Evaluator sha256: `{result['evaluator_sha256']}`")
    lines.append("")
    lines.append("> This packet is a selection surface, not a scalar objective. Human review remains responsible for deciding whether the scenario suite is sufficient and whether the trade-off is acceptable.")
    lines.append("")
    lines.append("## Review frontier")
    lines.append("")
    if result["review_frontier_candidate_ids"]:
        lines.append("Non-dominated candidates for human review:")
        for candidate_id in result["review_frontier_candidate_ids"]:
            lines.append(f"- `{candidate_id}`")
    else:
        lines.append("No candidate reached the review frontier.")
    lines.append("")
    lines.append("The frontier is not a winner set. It only removes candidates that are strictly worse across the visible trade-off dimensions.")
    lines.append("")
    lines.append("## Scenario-suite risks")
    lines.append("")
    if result["scenario_suite_risks"]:
        for risk in result["scenario_suite_risks"]:
            lines.append(f"- {risk}")
    else:
        lines.append("No automatic scenario-suite risks detected. This does not prove the suite is complete.")
    lines.append("")
    lines.append("## Candidate metrics")
    lines.append("")
    lines.append("| Candidate | Passed scenarios | Unsafe silent passes | False blocks | Unexpected escalations | Errors | Hard failures | Behavior signature | Human verdict |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|---|")
    for candidate in result["candidate_results"]:
        metrics = candidate["metrics"]
        lines.append(
            f"| `{candidate['candidate_id']}` | {metrics['passed_acceptable_decision']}/{metrics['scenarios']} | "
            f"{metrics['unsafe_silent_passes']} | {metrics['false_blocks']} | {metrics['unexpected_escalations']} | "
            f"{metrics['errors']} | {candidate['hard_failures']} | `{candidate['behavior_signature']}` | {candidate['human_verdict']} |"
        )
    lines.append("")
    lines.append("## Scenario traces")
    for candidate in result["candidate_results"]:
        lines.append("")
        lines.append(f"### `{candidate['candidate_id']}`")
        lines.append("")
        lines.append(candidate["hypothesis"])
        lines.append("")
        lines.append("| Scenario | Role | Acceptable | Actual | Pass | Reason |")
        lines.append("|---|---|---|---|---|---|")
        for trace in candidate["traces"]:
            acceptable = ", ".join(trace["acceptable_decisions"])
            passed = "yes" if trace["passed_acceptable_decision"] else "no"
            reason = str(trace["reason"]).replace("|", "\\|")
            lines.append(f"| `{trace['scenario_id']}` | {trace['role']} | {acceptable} | `{trace['actual_decision']}` | {passed} | {reason} |")
    lines.append("")
    lines.append("## Lineage")
    lines.append("")
    for candidate in result["candidate_results"]:
        lineage = candidate["lineage"]
        target_sha = lineage["target_sha256"] or "unavailable"
        lines.append(f"- `{candidate['candidate_id']}`: candidate record `{candidate['candidate_record_sha256']}`, parent id digest `{lineage['parent_id_digest']}`, target `{lineage['target']}`, target sha256 `{target_sha}`")
    lines.append("")
    lines.append("## Archive recommendation")
    lines.append("")
    lines.append("Keep every evaluated candidate as archive evidence. Rejected candidates with distinct behavior signatures are still useful stepping stones and future negative controls.")
    lines.append("")
    for signature, ids in result["distinct_behavior_archive"].items():
        joined = ", ".join(f"`{candidate_id}`" for candidate_id in ids)
        lines.append(f"- `{signature}`: {joined}")
    lines.append("")
    lines.append("## Human verdict")
    lines.append("")
    lines.append("- Verdict: pending")
    lines.append("- Validity scope accepted: pending")
    lines.append("- Rollback target accepted: pending")
    lines.append("- Scenario-suite gaps to add before future reuse: pending")
    lines.append("")
    return "\n".join(lines)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    fixture_path = Path(args.fixture)
    fixture = require_mapping(load_json(fixture_path), "fixture")
    require_fields(fixture, ("fixture_id", "origin_evidence", "validity_scope", "scenario_suite"), "fixture")
    scenario_suite = require_mapping(fixture["scenario_suite"], "fixture.scenario_suite")
    require_fields(scenario_suite, ("suite_id", "scenarios"), "fixture.scenario_suite")

    scenarios = [ScenarioRecord.from_json(require_mapping(scenario, "scenario")) for scenario in scenario_suite["scenarios"]]
    candidates = [CandidateRecord.load(Path(path)) for path in args.candidates]
    candidate_results = [
        evaluate_candidate(candidate, scenarios, fixture, fixture_path, args.verifier, args.verifier_timeout)
        for candidate in candidates
    ]
    evaluator_sha = sha256_bytes(Path(__file__).read_bytes()) if Path(__file__).exists() else "unknown"
    result = {
        "fixture_id": fixture["fixture_id"],
        "scenario_suite_id": scenario_suite["suite_id"],
        "fixture_sha256": sha256_json(fixture),
        "scenario_suite_sha256": sha256_json(scenario_suite),
        "evaluator_id": "scaffold-evolution.local-selection",
        "evaluator_sha256": evaluator_sha,
        "candidate_results": candidate_results,
    }
    result["review_frontier_candidate_ids"] = choose_review_frontier(candidate_results)
    result["distinct_behavior_archive"] = distinct_behavior_archive(candidate_results)
    result["scenario_suite_risks"] = scenario_suite_risks(fixture)
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate scaffold candidates against an incident scenario suite.")
    parser.add_argument("--fixture", required=True, help="Path to incident fixture JSON")
    parser.add_argument("--candidates", required=True, nargs="+", help="Candidate JSON files")
    parser.add_argument("--verifier", required=True, help="Verifier command as a JSON argv array or shell-style string. Supports {candidate}, {fixture}, and {scenario} placeholders.")
    parser.add_argument("--verifier-timeout", type=int, default=30, help="Verifier timeout in seconds")
    parser.add_argument("--out-md", help="Optional Markdown decision packet path")
    parser.add_argument("--out-json", help="Optional JSON result path")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        result = evaluate(args)
    except HarnessError as exc:
        print(f"scaffold-evolution: {exc}", file=sys.stderr)
        return 2

    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif not args.out_md:
        print(json.dumps(result, indent=2, sort_keys=True))

    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(render_markdown(result), encoding="utf-8")
        frontier = ", ".join(result["review_frontier_candidate_ids"]) or "<none>"
        print(f"frontier: {frontier}")
        for candidate in result["candidate_results"]:
            metrics = candidate["metrics"]
            print(
                f"{candidate['candidate_id']}: "
                f"{metrics['unsafe_silent_passes']} unsafe silent passes, "
                f"{metrics['false_blocks']} false blocks, "
                f"{metrics['passed_acceptable_decision']}/{metrics['scenarios']} scenarios passed"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
