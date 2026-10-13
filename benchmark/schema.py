from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


VALID_STATUSES = {"success", "failure", "timeout", "oom", "refusal", "partial_refusal", "tool_error"}


@dataclass
class RawResult:
    run_id: str
    attempt_id: str
    timestamp: str
    execution_role: str
    os: str
    model_id: str
    model_family: str
    runtime_model_name: str
    runtime_model_digest: str
    runtime_model_size_bytes: int
    runtime_model_modified_at: str
    quantization: str
    category: str
    task_id: str
    task_version: str
    context_length: int
    temperature: float
    status: str = "failure"
    response_text: str = ""
    response_saved: bool = False
    prompt_tokens: int = 0
    output_tokens: int = 0
    ttft_ms: float = 0
    generation_ms: float = 0
    prompt_eval_ms: float = 0
    model_load_ms: float = 0
    tokens_per_second: float = 0
    vram_baseline_mb: float = 0
    vram_peak_mb: float = 0
    ram_peak_mb: float = 0
    gpu_utilization_peak: float = 0
    build_success: bool | None = None
    test_pass_rate: float | None = None
    task_success: bool | None = None
    tool_calls_total: int | None = None
    tool_calls_valid: int | None = None
    tool_call_accuracy: float | None = None
    recovery_success: bool | None = None
    permission_violation: bool | None = None
    security_correctness: float | None = None
    security_keypoint_coverage: float | None = None
    security_hallucination: bool | None = None
    refused: bool = False
    over_refusal: bool = False
    answer_completeness: float | None = None
    hallucination_count: int = 0
    critical_hallucination_count: int = 0
    verifiable_claims: int = 0
    auto_score: float | None = None
    evaluator_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")
        return asdict(self)
