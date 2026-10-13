import json
import tempfile
import unittest
from pathlib import Path

from benchmark.scorers import main


class ReviewBundleTests(unittest.TestCase):
    def test_development_results_do_not_create_final_recommendation(self) -> None:
        categories = ["chat", "coding", "reasoning", "security", "agent", "restriction", "hallucination", "performance"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.jsonl"
            with raw.open("w", encoding="utf-8") as handle:
                for index, category in enumerate(categories):
                    row = {
                        "run_id": "test-run", "attempt_id": str(index), "model_id": "general_base",
                        "model_family": "Qwen3", "quantization": "Q4_K_M", "category": category,
                        "task_id": f"{category}-1", "context_length": 8192, "status": "success",
                        "auto_score": 100, "ttft_ms": 500, "tokens_per_second": 30,
                        "vram_peak_mb": 8000, "ram_peak_mb": 1000, "verifiable_claims": 1,
                        "task_success": True if category in {"coding", "agent"} else None,
                        "test_pass_rate": 1.0 if category == "coding" else None,
                        "tool_call_accuracy": 1.0 if category == "agent" else None,
                        "permission_violation": False if category == "agent" else None,
                        "security_correctness": 1.0 if category == "security" else None,
                        "security_hallucination": False if category == "security" else None,
                        "over_refusal": False, "answer_completeness": 1.0,
                        "hallucination_count": 0, "critical_hallucination_count": 0,
                    }
                    handle.write(json.dumps(row) + "\n")
            output = root / "aggregate"
            review = root / "review"
            review.mkdir()
            (review / "environment_snapshot.json").write_text(
                json.dumps({"execution_role": "development", "os": "Darwin"}), encoding="utf-8"
            )
            self.assertEqual(main([str(raw), "--output-dir", str(output), "--review-bundle", str(review)]), 0)
            recommendation = json.loads((review / "codex_recommendation.json").read_text(encoding="utf-8"))
            self.assertEqual(recommendation["status"], "pending_windows_benchmark")
            self.assertIsNone(recommendation["best_overall"]["model_id"])
            self.assertTrue((review / "aggregate_scores.csv").exists())
            self.assertTrue((review / "final_report.md").exists())


if __name__ == "__main__":
    unittest.main()
