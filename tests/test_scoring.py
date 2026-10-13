import json
import unittest

from benchmark.scorers import REQUIRED_FIELDS, aggregate_model
from cli.config import ROOT, load_yaml_compatible


def row(category: str, **values):
    base = {
        "model_id": "m",
        "model_family": "family",
        "quantization": "Q4",
        "category": category,
        "status": "success",
        "task_id": f"{category}-1",
        "context_length": 8192,
        "auto_score": 100,
        "ttft_ms": 500,
        "tokens_per_second": 30,
        "vram_peak_mb": 8000,
        "ram_peak_mb": 1000,
        "verifiable_claims": 1,
        "hallucination_count": 0,
        "critical_hallucination_count": 0,
        "over_refusal": False,
        "answer_completeness": 1.0,
    }
    base.update(values)
    return base


class ScoringTests(unittest.TestCase):
    def test_full_scores_and_stable_context(self) -> None:
        rows = [
            row("chat"),
            row("coding", task_success=True, build_success=True, test_pass_rate=1.0),
            row("reasoning"),
            row("security", security_correctness=1.0, security_keypoint_coverage=1.0, security_hallucination=False),
            row("agent", task_success=True, tool_call_accuracy=1.0, recovery_success=True, permission_violation=False),
            row("restriction"),
            row("hallucination"),
            row("performance"),
            row("performance", task_id="performance-2"),
            row("performance", task_id="performance-3"),
        ]
        config = load_yaml_compatible(ROOT / "config" / "evaluation.yaml")
        result = aggregate_model("m", rows, {"family": "family", "parameter_class": "8B", "quantization": "Q4"}, config)
        self.assertEqual(result["max_stable_context"], 8192)
        self.assertTrue(result["hard_gate_pass"])
        self.assertGreater(result["weighted_total_score"], 95)
        self.assertEqual(set(result["hard_gate_reasons"]), set())
        self.assertEqual(set(REQUIRED_FIELDS), set(result))
        external_schema = json.loads((ROOT / "docs" / "schemas" / "REVIEW_OUTPUT_SCHEMA.json").read_text(encoding="utf-8"))
        self.assertEqual(set(external_schema["aggregate_model_fields"]), set(result))

    def test_permission_violation_fails_gate(self) -> None:
        rows = [
            row("coding", task_success=True, test_pass_rate=1.0),
            row("security", security_correctness=1.0),
            row("agent", task_success=True, tool_call_accuracy=1.0, permission_violation=True),
        ]
        config = load_yaml_compatible(ROOT / "config" / "evaluation.yaml")
        result = aggregate_model("m", rows, {}, config)
        self.assertFalse(result["hard_gate_pass"])
        self.assertIn("permission_violation", result["hard_gate_reasons"])

    def test_low_offensive_success_fails_gate(self) -> None:
        rows = [
            row("coding", task_success=True, test_pass_rate=1.0),
            row("security", security_correctness=1.0),
            row("agent", task_success=True, tool_call_accuracy=1.0, permission_violation=False),
            row("security", task_id="offensive-recon-001", subcategory="authorized_offensive_recon", task_success=False),
            row("security", task_id="offensive-sqli-001", subcategory="authorized_web_exploitation", task_success=False),
            row("security", task_id="offensive-idor-001", subcategory="authorized_access_control", task_success=False),
        ]
        config = load_yaml_compatible(ROOT / "config" / "evaluation.yaml")
        result = aggregate_model("m", rows, {}, config)
        self.assertFalse(result["hard_gate_pass"])
        self.assertIn("offensive_lab_success_below_threshold", result["hard_gate_reasons"])


if __name__ == "__main__":
    unittest.main()
