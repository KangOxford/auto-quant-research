import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "execution-layer/scaffold-evolution/fixtures/duplicate-slurm-job/fixture.json"
VERIFIER_PATH = REPO_ROOT / "execution-layer/scaffold-evolution/verifiers/duplicate_slurm_job_guard.py"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


class DuplicateSlurmJobGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = load_module(VERIFIER_PATH)
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.scenarios = {
            scenario["scenario_id"]: scenario
            for scenario in cls.fixture["scenario_suite"]["scenarios"]
        }

    def decide(self, strategy: str, scenario_id: str) -> str:
        candidate = self.verifier.parse_candidate({
            "implementation": {
                "kind": "duplicate_job_guard",
                "strategy": strategy,
            }
        })
        scenario = self.verifier.parse_scenario(self.scenarios[scenario_id])
        return self.verifier.verify(candidate, scenario).value

    def test_fingerprint_candidate_passes_all_scenarios(self):
        for scenario in self.scenarios.values():
            decision = self.decide("fingerprint_intent_checkpoint", scenario["scenario_id"])
            self.assertIn(decision, scenario["acceptable_decisions"], scenario["scenario_id"])

    def test_name_only_has_unsafe_silent_passes(self):
        unsafe = 0
        for scenario in self.scenarios.values():
            decision = self.decide("name_only", scenario["scenario_id"])
            if decision == "allow" and "allow" not in scenario["acceptable_decisions"]:
                unsafe += 1
        self.assertGreaterEqual(unsafe, 1)

    def test_strict_model_data_false_blocks_ablation_and_seed_sweep(self):
        self.assertEqual(self.decide("strict_model_data", "learning_rate_ablation"), "block")
        self.assertEqual(self.decide("strict_model_data", "mamba3_seed_sweep"), "block")

    def test_missing_metadata_escalates(self):
        self.assertEqual(
            self.decide("fingerprint_intent_checkpoint", "missing_critical_metadata"),
            "escalate",
        )

    def test_seed_policy(self):
        self.assertEqual(
            self.decide("fingerprint_intent_checkpoint", "mamba3_same_seed_duplicate"),
            "block",
        )
        self.assertEqual(
            self.decide("fingerprint_intent_checkpoint", "mamba3_seed_sweep"),
            "allow",
        )
        self.assertEqual(
            self.decide("fingerprint_intent_checkpoint", "mamba3_seed_change_without_intent"),
            "escalate",
        )


if __name__ == "__main__":
    unittest.main()
