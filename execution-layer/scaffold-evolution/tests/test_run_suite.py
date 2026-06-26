import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
EVALUATE_PATH = REPO_ROOT / "execution-layer/scaffold-evolution/evaluate.py"
RUN_PATH = REPO_ROOT / "execution-layer/scaffold-evolution/run.py"
FIXTURE = "execution-layer/scaffold-evolution/fixtures/duplicate-slurm-job/fixture.json"
CANDIDATES = [
    "execution-layer/scaffold-evolution/examples/duplicate-slurm-job-lineage/fingerprint-intent-checkpoint.json",
    "execution-layer/scaffold-evolution/examples/duplicate-slurm-job-lineage/name-only.json",
    "execution-layer/scaffold-evolution/examples/duplicate-slurm-job-lineage/strict-model-data.json",
]
VERIFIER = [
    "python3",
    "execution-layer/scaffold-evolution/verifiers/duplicate_slurm_job_guard.py",
    "--candidate",
    "{candidate}",
    "--scenario",
    "{scenario}",
]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunSuiteTest(unittest.TestCase):
    def test_changed_path_routing(self):
        runner = load_module(RUN_PATH)
        suite = {
            "targets": ["execution-layer/skills/submit-job/SKILL.md"],
            "trigger_paths": ["execution-layer/scaffold-evolution/verifiers/"],
        }
        self.assertTrue(runner.suite_matches_changed_paths(suite, {"execution-layer/skills/submit-job/SKILL.md"}))
        self.assertTrue(runner.suite_matches_changed_paths(suite, {"execution-layer/scaffold-evolution/verifiers/duplicate_slurm_job_guard.py"}))
        self.assertFalse(runner.suite_matches_changed_paths(suite, {"README.md"}))

    def test_frontier_and_report_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_md = Path(temp_dir) / "first.md"
            first_json = Path(temp_dir) / "first.json"
            second_md = Path(temp_dir) / "second.md"
            second_json = Path(temp_dir) / "second.json"
            for md_path, json_path in ((first_md, first_json), (second_md, second_json)):
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(EVALUATE_PATH),
                        "--fixture",
                        FIXTURE,
                        "--candidates",
                        *CANDIDATES,
                        "--verifier",
                        json.dumps(VERIFIER),
                        "--out-md",
                        str(md_path),
                        "--out-json",
                        str(json_path),
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

            result = json.loads(first_json.read_text(encoding="utf-8"))
            self.assertEqual(
                result["review_frontier_candidate_ids"],
                ["duplicate-guard.fingerprint-intent-checkpoint"],
            )
            self.assertEqual(first_md.read_text(encoding="utf-8"), second_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
