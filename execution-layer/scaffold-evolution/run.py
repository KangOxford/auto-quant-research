#!/usr/bin/env python3
"""Run registered scaffold-evolution scenario suites."""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_registry(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        registry = json.load(f)
    if not isinstance(registry, dict) or not isinstance(registry.get("suites"), list):
        raise ValueError(f"{path}: expected object with 'suites' array")
    return registry


def run_suite(repo_root: Path, evaluator: Path, suite: dict[str, Any]) -> int:
    fixture = suite["fixture"]
    candidates = sorted(glob.glob(str(repo_root / suite["candidates"])))
    if not candidates:
        print(f"scaffold-evolution: no candidates matched {suite['candidates']}", file=sys.stderr)
        return 2

    command = [
        sys.executable,
        str(evaluator),
        "--fixture",
        fixture,
        "--candidates",
        *[str(Path(path).relative_to(repo_root)) for path in candidates],
        "--verifier",
        json.dumps(suite["verifier"]),
        "--out-md",
        suite["out_md"],
    ]
    if suite.get("out_json"):
        command.extend(["--out-json", suite["out_json"]])
    completed = subprocess.run(command, cwd=repo_root, check=False)
    return completed.returncode


def normalize_path(path: str) -> str:
    return path.strip().lstrip("./")


def path_matches_prefix(path: str, prefix: str) -> bool:
    path = normalize_path(path)
    prefix = normalize_path(prefix)
    if not prefix:
        return False
    if prefix.endswith("/"):
        return path.startswith(prefix)
    return path == prefix or path.startswith(prefix + "/")


def suite_matches_changed_paths(suite: dict[str, Any], changed_paths: set[str]) -> bool:
    if not changed_paths:
        return True
    triggers = [*suite.get("targets", []), *suite.get("trigger_paths", [])]
    if not triggers:
        return False
    return any(path_matches_prefix(path, trigger) for path in changed_paths for trigger in triggers)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scaffold-evolution scenario suites.")
    parser.add_argument("--registry", default="execution-layer/scaffold-evolution/suite-registry.json", help="Suite registry JSON path")
    parser.add_argument("--suite", action="append", help="Optional suite_id filter. Can be repeated.")
    parser.add_argument("--changed-paths", help="Optional newline-delimited file list. Runs only suites whose targets or trigger_paths match.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[1]
    registry_path = repo_root / args.registry
    evaluator = script_dir / "evaluate.py"

    try:
        registry = load_registry(registry_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"scaffold-evolution: {exc}", file=sys.stderr)
        return 2

    selected = set(args.suite or [])
    changed_paths: set[str] = set()
    if args.changed_paths:
        try:
            changed_paths = {normalize_path(line) for line in Path(args.changed_paths).read_text(encoding="utf-8").splitlines() if line.strip()}
        except OSError as exc:
            print(f"scaffold-evolution: cannot read changed paths: {exc}", file=sys.stderr)
            return 2

    failures = 0
    matched = 0
    for suite in registry["suites"]:
        suite_id = suite.get("suite_id", "")
        if selected and suite_id not in selected:
            continue
        if not suite_matches_changed_paths(suite, changed_paths):
            continue
        matched += 1
        try:
            code = run_suite(repo_root, evaluator, suite)
        except KeyError as exc:
            print(f"scaffold-evolution: suite {suite_id or '<unknown>'} missing {exc}", file=sys.stderr)
            code = 2
        if code:
            failures += 1

    if selected and matched == 0:
        print(f"scaffold-evolution: no registered suite matched: {', '.join(sorted(selected))}", file=sys.stderr)
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
