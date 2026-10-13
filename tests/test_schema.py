import unittest
from dataclasses import fields

from benchmark.schema import RawResult


class RawSchemaTests(unittest.TestCase):
    def test_required_external_fields_are_present(self) -> None:
        required = {
            "run_id", "attempt_id", "timestamp", "model_id", "model_family", "runtime_model_name",
            "quantization", "category", "task_id", "task_version", "context_length", "temperature",
            "status", "response_text", "response_saved", "prompt_tokens", "output_tokens", "ttft_ms",
            "generation_ms", "tokens_per_second", "vram_baseline_mb", "vram_peak_mb", "ram_peak_mb",
            "build_success", "test_pass_rate", "task_success", "tool_calls_total", "tool_calls_valid",
            "tool_call_accuracy", "recovery_success", "permission_violation", "security_correctness",
            "security_keypoint_coverage", "security_hallucination", "refused", "over_refusal",
            "answer_completeness", "hallucination_count", "critical_hallucination_count", "auto_score",
            "evaluator_notes",
        }
        self.assertTrue(required.issubset({field.name for field in fields(RawResult)}))

    def test_offensive_extension_fields_are_present(self) -> None:
        expected = {"subcategory", "lab_isolated", "target_scope", "flag_captured"}
        self.assertTrue(expected.issubset({field.name for field in fields(RawResult)}))


if __name__ == "__main__":
    unittest.main()
