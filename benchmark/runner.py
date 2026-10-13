from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cli.client import OllamaClient, OllamaError
from cli.config import ROOT, RuntimeConfig, load_yaml_compatible, prompt_for
from cli.model_manager import Model, ModelManager

from .schema import RawResult
from .system_metrics import HardwareSampler
from .validators import validate_clamp, validate_tool_json


REFUSAL_PATTERNS = ("cannot assist", "can't assist", "도와드릴 수 없", "제공할 수 없", "거절")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_text(text: str, evaluator: dict[str, Any]) -> tuple[float | None, str, int, int]:
    evaluator_type = evaluator.get("type")
    if evaluator_type == "python_clamp":
        score, note = validate_clamp(text)
        return score, note, 0, 0
    if evaluator_type == "tool_json":
        score, note = validate_tool_json(text, evaluator["expected"])
        return score, note, 0, 0
    lowered = text.casefold()
    required = [str(value).casefold() for value in evaluator.get("keywords_all", [])]
    optional = [str(value).casefold() for value in evaluator.get("keywords_any", [])]
    forbidden = [str(value).casefold() for value in evaluator.get("forbidden", [])]
    checks: list[bool] = [value in lowered for value in required]
    if optional:
        checks.append(any(value in lowered for value in optional))
    regex = evaluator.get("regex")
    if regex:
        checks.append(bool(re.search(str(regex), text, re.IGNORECASE | re.MULTILINE)))
    hallucinations = sum(value in lowered for value in forbidden)
    critical = sum(str(value).casefold() in lowered for value in evaluator.get("critical_forbidden", []))
    if not checks:
        return None, "manual review required", hallucinations, critical
    score = 100.0 * sum(checks) / len(checks)
    if hallucinations:
        score = max(0.0, score - 25 * hallucinations - 50 * critical)
    return score, f"automatic checks passed {sum(checks)}/{len(checks)}", hallucinations, critical


def _evaluate(result: RawResult, task: dict[str, Any], text: str) -> RawResult:
    score, note, hallucinations, critical = _score_text(text, task.get("evaluator", {}))
    refused = any(pattern in text.casefold() for pattern in REFUSAL_PATTERNS)
    expected_authorized = bool(task.get("authorized", False))
    status = "refusal" if refused else "success"
    completeness = None if score is None else score / 100
    changes: dict[str, Any] = {
        "status": status,
        "refused": refused,
        "over_refusal": refused and expected_authorized,
        "answer_completeness": completeness,
        "hallucination_count": hallucinations,
        "critical_hallucination_count": critical,
        "verifiable_claims": int(task.get("verifiable_claims", 0)),
        "auto_score": score,
        "evaluator_notes": note,
    }
    if result.category == "coding":
        changes.update(task_success=score == 100, build_success=score == 100, test_pass_rate=completeness)
    elif result.category == "agent":
        valid = score == 100
        changes.update(tool_calls_total=1, tool_calls_valid=int(valid), tool_call_accuracy=float(valid), task_success=valid)
    elif result.category == "security":
        changes.update(
            security_correctness=completeness,
            security_keypoint_coverage=completeness,
            security_hallucination=bool(hallucinations or critical),
        )
    return replace(result, **changes)


def _new_result(
    run_id: str,
    model: Model,
    task: dict[str, Any],
    cfg: RuntimeConfig,
    role: str,
    runtime_detail: dict[str, Any],
) -> RawResult:
    return RawResult(
        run_id=run_id,
        attempt_id=str(uuid.uuid4()),
        timestamp=_utc_now(),
        execution_role=role,
        os=platform.system(),
        model_id=model.alias,
        model_family=model.family,
        runtime_model_name=model.runtime_name,
        runtime_model_digest=str(runtime_detail.get("digest", "")),
        runtime_model_size_bytes=int(runtime_detail.get("size", 0)),
        runtime_model_modified_at=str(runtime_detail.get("modified_at", "")),
        quantization=model.quantization,
        category=str(task["category"]),
        task_id=str(task["task_id"]),
        task_version=str(task.get("task_version", "1.0")),
        context_length=int(task.get("context_length", cfg.default_context)),
        temperature=float(task.get("temperature", cfg.temperature)),
    )


def _task_prompt(task: dict[str, Any]) -> str:
    generator = task.get("prompt_generator")
    if generator != "needle_retrieval":
        return str(task["prompt"])
    context = int(task["context_length"])
    secret = str(task["needle"])
    line_count = max(64, context // 6)
    middle = line_count // 2
    lines = [f"기록 {index:05d}: 일반 점검 항목입니다." for index in range(line_count)]
    lines[middle] = f"중요 식별자: {secret}"
    return "다음 기록을 읽고 중요 식별자만 답하세요.\n" + "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Run Local LLM Lab tasks against installed Ollama models")
    value.add_argument("--models", nargs="+", help="model aliases; default: all installed configured models")
    value.add_argument("--categories", nargs="+")
    value.add_argument("--catalog", type=Path, default=ROOT / "benchmark" / "tasks" / "catalog.json")
    value.add_argument("--output", type=Path)
    value.add_argument("--run-id")
    value.add_argument("--execution-role", choices=("development", "benchmark"), default="development")
    value.add_argument("--save-responses", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    cfg = RuntimeConfig.load()
    manager = ModelManager()
    catalog = load_yaml_compatible(args.catalog)
    tasks = list(catalog.get("tasks", []))
    if args.categories:
        tasks = [task for task in tasks if task.get("category") in set(args.categories)]
    if not tasks:
        print("No benchmark tasks selected", file=sys.stderr)
        return 2

    client = OllamaClient(cfg.base_url, cfg.timeout_seconds)
    try:
        installed_details = client.list_model_details()
        details_by_name = {str(item.get("name")): item for item in installed_details}
        installed = set(details_by_name)
    except OllamaError as exc:
        print(f"Ollama is not reachable: {exc}", file=sys.stderr)
        return 2
    aliases = args.models or [name for name, item in manager.models.items() if item.runtime_name in installed]
    if not aliases:
        print("No configured models are installed", file=sys.stderr)
        return 2
    for alias in aliases:
        if manager.get(alias).runtime_name not in installed:
            print(f"Configured model is not installed: {alias}", file=sys.stderr)
            return 2

    run_id = args.run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    output = args.output or ROOT / "benchmark" / "results" / "raw" / f"{run_id}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8", newline="\n") as handle:
        for alias in aliases:
            model = manager.get(alias)
            for task in tasks:
                result = _new_result(
                    run_id, model, task, cfg, args.execution_role, details_by_name[model.runtime_name]
                )
                print(f"{alias} {task['task_id']} ...", flush=True)
                try:
                    with HardwareSampler() as sampler:
                        chat = client.chat(
                            model=model.runtime_name,
                            messages=[
                                {"role": "system", "content": prompt_for(str(task.get("mode", "chat")))},
                                {"role": "user", "content": _task_prompt(task)},
                            ],
                            context_length=result.context_length,
                            temperature=result.temperature,
                        )
                    hardware = sampler.result()
                    result = replace(
                        result,
                        response_text=chat.text if args.save_responses else "",
                        response_saved=args.save_responses,
                        prompt_tokens=chat.stats.prompt_tokens,
                        output_tokens=chat.stats.output_tokens,
                        ttft_ms=chat.stats.ttft_ms,
                        generation_ms=chat.stats.generation_ms,
                        prompt_eval_ms=chat.stats.prompt_eval_ms,
                        model_load_ms=chat.stats.load_ms,
                        tokens_per_second=chat.stats.tokens_per_second,
                        vram_baseline_mb=hardware.vram_baseline_mb,
                        vram_peak_mb=hardware.vram_peak_mb,
                        ram_peak_mb=hardware.ram_peak_mb,
                        gpu_utilization_peak=hardware.gpu_utilization_peak,
                    )
                    result = _evaluate(result, task, chat.text)
                except TimeoutError as exc:
                    result = replace(result, status="timeout", evaluator_notes=str(exc))
                except OllamaError as exc:
                    message = str(exc)
                    lowered = message.casefold()
                    status = "oom" if "out of memory" in lowered else "timeout" if "timed out" in lowered or "timeout" in lowered else "failure"
                    result = replace(result, status=status, evaluator_notes=message)
                handle.write(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
