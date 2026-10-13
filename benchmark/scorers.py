from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from cli.config import ROOT, load_yaml_compatible
from cli.model_manager import ModelManager


CATEGORY_FIELDS = {
    "chat": "chat_score",
    "coding": "coding_score",
    "reasoning": "reasoning_score",
    "security": "security_score",
    "agent": "agent_score",
}
REQUIRED_FIELDS = [
    "model_id", "model_family", "parameter_class", "quantization", "disk_size_gb",
    "vram_peak_mb", "ram_peak_mb", "ttft_p50_ms", "ttft_p95_ms",
    "tokens_per_second_mean", "tokens_per_second_p10", "max_stable_context",
    "chat_score", "coding_score", "reasoning_score", "security_score", "agent_score",
    "hallucination_resistance_score", "restriction_score", "performance_score", "weighted_total_score",
    "coding_pass_at_1", "coding_final_success_rate", "test_pass_rate",
    "agent_task_completion_rate", "agent_tool_call_accuracy", "agent_recovery_rate",
    "agent_permission_violation_rate", "security_correctness_rate", "security_hallucination_rate",
    "authorized_security_over_refusal_rate", "hallucination_rate_total", "oom_count", "timeout_count",
    "failed_run_count", "total_run_count", "hard_gate_pass", "hard_gate_reasons",
]


def _numbers(rows: Iterable[dict[str, Any]], field: str) -> list[float]:
    return [float(row[field]) for row in rows if row.get(field) is not None]


def _mean(rows: Iterable[dict[str, Any]], field: str, default: float = 0.0) -> float:
    values = _numbers(rows, field)
    return mean(values) if values else default


def _rate(rows: Iterable[dict[str, Any]], field: str, default: float = 0.0) -> float:
    values = [bool(row[field]) for row in rows if row.get(field) is not None]
    return sum(values) / len(values) if values else default


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _lower_better(value: float, good: float, bad: float) -> float:
    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0
    return 100.0 * (bad - value) / (bad - good)


def _higher_better(value: float, bad: float, good: float) -> float:
    if value >= good:
        return 100.0
    if value <= bad:
        return 0.0
    return 100.0 * (value - bad) / (good - bad)


def _max_stable_context(rows: list[dict[str, Any]]) -> int:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("category") == "performance":
            grouped[int(row.get("context_length", 0))].append(row)
    stable = []
    for context, attempts in grouped.items():
        successes = [row for row in attempts if row.get("status") == "success" and float(row.get("auto_score") or 0) >= 70]
        if len(successes) >= 3:
            stable.append(context)
    return max(stable, default=0)


def _category_score(rows: list[dict[str, Any]], category: str) -> float:
    return _clamp(_mean([row for row in rows if row.get("category") == category], "auto_score"))


def aggregate_model(
    model_id: str,
    rows: list[dict[str, Any]],
    model_meta: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    successful = [row for row in rows if row.get("status") in {"success", "partial_refusal", "refusal"}]
    coding = [row for row in rows if row.get("category") == "coding"]
    agent = [row for row in rows if row.get("category") == "agent"]
    security = [row for row in rows if row.get("category") == "security"]
    authorized = [row for row in rows if row.get("category") in {"security", "restriction"}]
    ttft = _numbers(successful, "ttft_ms")
    tps = _numbers(successful, "tokens_per_second")
    vram_peak = max(_numbers(rows, "vram_peak_mb"), default=0.0)
    max_context = _max_stable_context(rows)
    verifiable = sum(int(row.get("verifiable_claims", 0)) for row in rows)
    weighted_hallucinations = sum(
        int(row.get("hallucination_count", 0)) + 3 * int(row.get("critical_hallucination_count", 0))
        for row in rows
    )
    hallucination_rate = min(1.0, weighted_hallucinations / verifiable) if verifiable else 0.0

    scores = {field: _category_score(rows, category) for category, field in CATEGORY_FIELDS.items()}
    scores["hallucination_resistance_score"] = 100.0 * (1.0 - hallucination_rate)
    over_refusal = _rate(authorized, "over_refusal")
    completeness = _mean(authorized, "answer_completeness")
    scores["restriction_score"] = _clamp((1.0 - over_refusal) * 70 + completeness * 30)

    perf = evaluation["performance_normalization"]
    ttft_score = _lower_better(_percentile(ttft, 0.5), float(perf["ttft_good_ms"]), float(perf["ttft_bad_ms"]))
    tps_score = _higher_better(mean(tps) if tps else 0, float(perf["tokens_per_second_bad"]), float(perf["tokens_per_second_good"]))
    vram_score = _lower_better(vram_peak, float(perf["vram_budget_mb"]) * 0.5, float(perf["vram_budget_mb"])) if vram_peak else 0.0
    context_score = _higher_better(max_context, 0, float(perf["context_target"]))
    scores["performance_score"] = mean([ttft_score, tps_score, vram_score, context_score])

    weights = evaluation["weights"]
    weighted_total = (
        scores["coding_score"] * weights["coding"]
        + scores["agent_score"] * weights["agent"]
        + scores["security_score"] * weights["security"]
        + scores["reasoning_score"] * weights["reasoning"]
        + scores["chat_score"] * weights["chat_korean"]
        + scores["hallucination_resistance_score"] * weights["hallucination_resistance"]
        + scores["restriction_score"] * weights["restriction_over_refusal"]
        + scores["performance_score"] * weights["performance"]
    ) / 100.0

    result: dict[str, Any] = {
        "model_id": model_id,
        "model_family": str(model_meta.get("family", rows[0].get("model_family", "unknown"))),
        "parameter_class": str(model_meta.get("parameter_class", "unknown")),
        "quantization": str(model_meta.get("quantization", rows[0].get("quantization", "unknown"))),
        "disk_size_gb": float(model_meta.get("estimated_disk_gb", 0)),
        "vram_peak_mb": round(vram_peak, 3),
        "ram_peak_mb": round(max(_numbers(rows, "ram_peak_mb"), default=0.0), 3),
        "ttft_p50_ms": round(_percentile(ttft, 0.5), 3),
        "ttft_p95_ms": round(_percentile(ttft, 0.95), 3),
        "tokens_per_second_mean": round(mean(tps) if tps else 0.0, 3),
        "tokens_per_second_p10": round(_percentile(tps, 0.1), 3),
        "max_stable_context": max_context,
        **{key: round(value, 3) for key, value in scores.items()},
        "weighted_total_score": round(weighted_total, 3),
        "coding_pass_at_1": round(_rate(coding, "task_success"), 4),
        "coding_final_success_rate": round(_rate(coding, "task_success"), 4),
        "test_pass_rate": round(_mean(coding, "test_pass_rate"), 4),
        "agent_task_completion_rate": round(_rate(agent, "task_success"), 4),
        "agent_tool_call_accuracy": round(_mean(agent, "tool_call_accuracy"), 4),
        "agent_recovery_rate": round(_rate(agent, "recovery_success"), 4),
        "agent_permission_violation_rate": round(_rate(agent, "permission_violation"), 4),
        "security_correctness_rate": round(_mean(security, "security_correctness"), 4),
        "security_hallucination_rate": round(_rate(security, "security_hallucination"), 4),
        "authorized_security_over_refusal_rate": round(over_refusal, 4),
        "hallucination_rate_total": round(hallucination_rate, 4),
        "oom_count": sum(row.get("status") == "oom" for row in rows),
        "timeout_count": sum(row.get("status") == "timeout" for row in rows),
        "failed_run_count": sum(row.get("status") in {"failure", "timeout", "oom", "tool_error"} for row in rows),
        "total_run_count": len(rows),
    }

    gates = evaluation["hard_gates"]
    reasons: list[str] = []
    categories = {str(row.get("category")) for row in rows}
    for needed in ("coding", "agent", "security"):
        if needed not in categories:
            reasons.append(f"missing_{needed}_results")
    if result["oom_count"] > int(gates["max_oom_count"]):
        reasons.append("oom_threshold_exceeded")
    if rows and result["timeout_count"] / len(rows) > float(gates["max_timeout_rate"]):
        reasons.append("timeout_rate_exceeded")
    if coding and result["coding_final_success_rate"] < float(gates["min_coding_final_success_rate"]):
        reasons.append("coding_success_below_threshold")
    critical_count = sum(int(row.get("critical_hallucination_count", 0)) for row in security)
    if critical_count > int(gates["max_security_critical_hallucinations"]):
        reasons.append("security_critical_hallucination")
    if agent and result["agent_tool_call_accuracy"] < float(gates["min_agent_tool_call_accuracy"]):
        reasons.append("agent_tool_accuracy_below_threshold")
    if result["agent_permission_violation_rate"] > float(gates["max_permission_violation_rate"]):
        reasons.append("permission_violation")
    result["hard_gate_pass"] = not reasons
    result["hard_gate_reasons"] = reasons
    return result


def load_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number}: expected JSON object")
                rows.append(value)
    return rows


def _recommend(aggregates: list[dict[str, Any]], official: bool, reason: str) -> dict[str, Any]:
    if not official:
        return {
            "status": "pending_windows_benchmark",
            "best_overall": {"model_id": None, "score": None, "reasons": [reason]},
            "roles": {"chat": None, "coding": None, "security": None, "agent": None, "fast": None},
            "rejected_candidates": [],
            "tradeoffs": ["No final recommendation is valid until the official Windows benchmark gate passes."],
            "confidence": 0.0,
        }
    eligible = [item for item in aggregates if item["hard_gate_pass"]]
    if not eligible:
        return {
            "status": "no_eligible_model",
            "best_overall": {"model_id": None, "score": None, "reasons": ["All candidates failed hard gates."]},
            "roles": {"chat": None, "coding": None, "security": None, "agent": None, "fast": None},
            "rejected_candidates": [{"model_id": item["model_id"], "reason": ", ".join(item["hard_gate_reasons"])} for item in aggregates],
            "tradeoffs": [],
            "confidence": 0.0,
        }
    role_formulas = {
        "chat": {"chat_score": .5, "reasoning_score": .3, "performance_score": .2},
        "coding": {"coding_score": .6, "hallucination_resistance_score": .25, "performance_score": .15},
        "security": {"security_score": .5, "hallucination_resistance_score": .2, "restriction_score": .15, "reasoning_score": .15},
        "agent": {"agent_score": .5, "coding_score": .25, "hallucination_resistance_score": .15, "performance_score": .1},
        "fast": {"performance_score": .7, "weighted_total_score": .3},
    }
    roles = {
        role: max(eligible, key=lambda item: sum(item[field] * weight for field, weight in formula.items()))["model_id"]
        for role, formula in role_formulas.items()
    }
    best = max(eligible, key=lambda item: item["weighted_total_score"])
    rejected = [
        {"model_id": item["model_id"], "reason": ", ".join(item["hard_gate_reasons"])}
        for item in aggregates if not item["hard_gate_pass"]
    ]
    return {
        "status": "complete",
        "best_overall": {"model_id": best["model_id"], "score": best["weighted_total_score"], "reasons": ["Highest weighted score among hard-gate-passing models."]},
        "roles": roles,
        "rejected_candidates": rejected,
        "tradeoffs": ["Role assignments use category-specific formulas recorded by this scorer."],
        "confidence": min(1.0, len(eligible) / 4),
    }


def _official_gate(rows: list[dict[str, Any]], environment: dict[str, Any], evaluation: dict[str, Any]) -> tuple[bool, str]:
    rule = evaluation["official_run"]
    if not environment.get("official_benchmark_eligible"):
        return False, "environment snapshot is not eligible for an official benchmark"
    if environment.get("execution_role") != rule["required_execution_role"]:
        return False, "environment_snapshot execution_role is not benchmark"
    if str(environment.get("os", "")).casefold() != str(rule["required_os"]).casefold():
        return False, "official benchmark must run on Windows"
    if str(rule["required_cpu_contains"]).casefold() not in str(environment.get("cpu", "")).casefold():
        return False, "target CPU was not detected"
    if str(rule["required_gpu_contains"]).casefold() not in str(environment.get("gpu", "")).casefold():
        return False, "target GPU was not detected"
    if float(environment.get("vram_mb") or 0) < float(rule["minimum_vram_mb"]):
        return False, "available VRAM is below the target threshold"
    if float(environment.get("ram_gb") or 0) < float(rule["minimum_ram_gb"]):
        return False, "system RAM is below the target threshold"
    if not environment.get("local_only_verified"):
        return False, "Ollama localhost-only binding was not verified"
    if any(row.get("execution_role") != rule["required_execution_role"] for row in rows):
        return False, "raw results contain non-benchmark execution roles"
    if len({row.get("model_id") for row in rows}) < int(rule["minimum_models"]):
        return False, "fewer than the required number of models were measured"
    present = {row.get("category") for row in rows}
    missing = set(rule["required_categories"]) - present
    if missing:
        return False, f"missing required categories: {', '.join(sorted(missing))}"
    model_ids = {str(row.get("model_id")) for row in rows}
    task_ids = {str(row.get("task_id")) for row in rows}
    attempts: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        attempts[(str(row.get("model_id")), str(row.get("task_id")))] += 1
    minimum = int(rule["minimum_attempts_per_task"])
    if any(attempts[(model_id, task_id)] < minimum for model_id in model_ids for task_id in task_ids):
        return False, f"one or more model/task pairs have fewer than {minimum} attempts"
    return True, "official gate passed"


def _write_report(
    path: Path,
    environment: dict[str, Any],
    aggregates: list[dict[str, Any]],
    recommendation: dict[str, Any],
    evaluation: dict[str, Any],
) -> None:
    lines = [
        "# Local LLM Final Evaluation Report",
        "",
        f"> Status: `{recommendation['status']}`",
        "",
        "## Test Environment",
        "",
        f"- OS: {environment.get('os', 'unknown')}",
        f"- CPU: {environment.get('cpu', 'unknown')}",
        f"- GPU: {environment.get('gpu', 'not measured')}",
        f"- VRAM: {environment.get('vram_mb', 'not measured')} MB",
        f"- RAM: {environment.get('ram_gb', 'not measured')} GB",
        f"- NVIDIA driver: {environment.get('driver_version', 'not measured')}",
        f"- Ollama: {environment.get('ollama_version', 'not measured')}",
        f"- Test date: {environment.get('timestamp', 'unknown')}",
        f"- Execution role: {environment.get('execution_role', 'unknown')}",
        "",
        "## Evaluation Configuration",
        "",
        "| Category | Weight |",
        "|---|---:|",
    ]
    for name, weight in evaluation["weights"].items():
        lines.append(f"| {name} | {weight} |")
    lines.extend([
        "",
        "## Overall Scores",
        "",
        "| Model | Total | Hard Gate | Reasons |",
        "|---|---:|---|---|",
    ])
    for item in sorted(aggregates, key=lambda row: row["weighted_total_score"], reverse=True):
        lines.append(f"| {item['model_id']} | {item['weighted_total_score']:.3f} | {item['hard_gate_pass']} | {', '.join(item['hard_gate_reasons'])} |")
    lines.extend([
        "",
        "## Category Scores",
        "",
        "| Model | Chat | Coding | Reasoning | Security | Agent | Hallucination | Restriction | Performance |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for item in aggregates:
        lines.append(
            f"| {item['model_id']} | {item['chat_score']:.1f} | {item['coding_score']:.1f} | "
            f"{item['reasoning_score']:.1f} | {item['security_score']:.1f} | {item['agent_score']:.1f} | "
            f"{item['hallucination_resistance_score']:.1f} | {item['restriction_score']:.1f} | {item['performance_score']:.1f} |"
        )
    lines.extend([
        "",
        "## Runtime Performance and Context",
        "",
        "| Model | VRAM peak MB | RAM peak MB | TTFT p50 ms | TTFT p95 ms | tok/s mean | tok/s p10 | Max stable context | OOM |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for item in aggregates:
        lines.append(
            f"| {item['model_id']} | {item['vram_peak_mb']:.0f} | {item['ram_peak_mb']:.0f} | "
            f"{item['ttft_p50_ms']:.1f} | {item['ttft_p95_ms']:.1f} | "
            f"{item['tokens_per_second_mean']:.2f} | {item['tokens_per_second_p10']:.2f} | "
            f"{item['max_stable_context']} | {item['oom_count']} |"
        )
    lines.extend([
        "",
        "## Coding, Agent, and Security Metrics",
        "",
        "| Model | Coding pass@1 | Coding final | Tests | Agent completion | Tool accuracy | Recovery | Permission violations | Security correctness | Security hallucination | Over-refusal |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for item in aggregates:
        lines.append(
            f"| {item['model_id']} | {item['coding_pass_at_1']:.3f} | {item['coding_final_success_rate']:.3f} | "
            f"{item['test_pass_rate']:.3f} | {item['agent_task_completion_rate']:.3f} | "
            f"{item['agent_tool_call_accuracy']:.3f} | {item['agent_recovery_rate']:.3f} | "
            f"{item['agent_permission_violation_rate']:.3f} | {item['security_correctness_rate']:.3f} | "
            f"{item['security_hallucination_rate']:.3f} | {item['authorized_security_over_refusal_rate']:.3f} |"
        )
    roles = recommendation["roles"]
    lines.extend([
        "",
        "## Codex Recommendation",
        "",
        f"- Best overall: {recommendation['best_overall']['model_id']}",
        f"- Score: {recommendation['best_overall']['score']}",
        f"- Reason: {'; '.join(recommendation['best_overall']['reasons'])}",
        "",
        "```text",
        f"DEFAULT_CHAT_MODEL={roles['chat'] or ''}",
        f"CODING_MODEL={roles['coding'] or ''}",
        f"SECURITY_MODEL={roles['security'] or ''}",
        f"AGENT_MODEL={roles['agent'] or ''}",
        f"FAST_MODEL={roles['fast'] or ''}",
        f"BEST_OVERALL_MODEL={recommendation['best_overall']['model_id'] or ''}",
        "```",
        "",
        "## Trade-offs and Rejected Candidates",
        "",
    ])
    lines.extend(f"- {item}" for item in recommendation["tradeoffs"])
    if recommendation["rejected_candidates"]:
        lines.extend(["", "| Model | Reason |", "|---|---|"])
        lines.extend(f"| {item['model_id']} | {item['reason']} |" for item in recommendation["rejected_candidates"])
    lines.extend([
        "",
        "## Reproduction",
        "",
        "```powershell",
        ".\\scripts\\windows\\run_benchmark.ps1 -Attempts 3",
        "```",
        "",
        "## Known Limitations",
        "",
        "- Automated smoke tasks are not a substitute for a curated, multi-attempt Windows benchmark.",
        "- Independent reviewer notes are intentionally left outside the automated recommendation.",
        "",
        "## Independent Reviewer Notes",
        "",
        "- Reviewer:",
        "- Independent best overall:",
        "- Differences from Codex recommendation:",
        "- Reason:",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _model_manifest(
    manager: ModelManager,
    grouped: dict[str, list[dict[str, Any]]],
    aggregates: list[dict[str, Any]],
) -> dict[str, Any]:
    aggregate_by_id = {item["model_id"]: item for item in aggregates}
    models = []
    for item in manager.as_manifest():
        model_id = str(item["model_id"])
        observed = grouped.get(model_id, [])
        aggregate = aggregate_by_id.get(model_id)
        runtime = {}
        if observed:
            first = observed[0]
            runtime = {
                "name": first.get("runtime_model_name"),
                "digest": first.get("runtime_model_digest", ""),
                "size_bytes": first.get("runtime_model_size_bytes", 0),
                "modified_at": first.get("runtime_model_modified_at", ""),
            }
        measured = {}
        if aggregate:
            measured = {
                "vram_peak_mb": aggregate["vram_peak_mb"],
                "ram_peak_mb": aggregate["ram_peak_mb"],
                "ttft_p50_ms": aggregate["ttft_p50_ms"],
                "tokens_per_second_mean": aggregate["tokens_per_second_mean"],
                "max_stable_context": aggregate["max_stable_context"],
            }
        models.append({**item, "runtime_observed": runtime, "measured": measured})
    return {"schema_version": "1.0", "models": models}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Aggregate raw benchmark JSONL and build a review bundle")
    value.add_argument("raw", nargs="+", type=Path)
    value.add_argument("--output-dir", type=Path, default=ROOT / "benchmark" / "results" / "aggregate")
    value.add_argument("--review-bundle", type=Path, default=ROOT / "review_bundle")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    rows = load_rows(args.raw)
    if not rows:
        raise SystemExit("No raw results found")
    evaluation = load_yaml_compatible(ROOT / "config" / "evaluation.yaml")
    manager = ModelManager()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["model_id"])].append(row)
    aggregates = [
        aggregate_model(model_id, values, manager.models.get(model_id).metadata if model_id in manager.models else {}, evaluation)
        for model_id, values in grouped.items()
    ]
    run_id = str(rows[0].get("run_id", datetime.now().strftime("%Y%m%d-%H%M%S")))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{run_id}_scores.json"
    csv_path = args.output_dir / f"{run_id}_scores.csv"
    json_path.write_text(json.dumps({"schema_version": "1.0", "models": aggregates}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        for item in aggregates:
            writer.writerow({key: json.dumps(item[key], ensure_ascii=False) if isinstance(item[key], list) else item[key] for key in REQUIRED_FIELDS})

    args.review_bundle.mkdir(parents=True, exist_ok=True)
    environment_path = args.review_bundle / "environment_snapshot.json"
    environment = json.loads(environment_path.read_text(encoding="utf-8")) if environment_path.exists() else {}
    official, reason = _official_gate(rows, environment, evaluation)
    recommendation = _recommend(aggregates, official, reason)
    (args.review_bundle / "aggregate_scores.json").write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copyfile(csv_path, args.review_bundle / "aggregate_scores.csv")
    with (args.review_bundle / "raw_results.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (args.review_bundle / "evaluation_config.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = _model_manifest(manager, grouped, aggregates)
    (args.review_bundle / "model_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    catalog = json.loads((ROOT / "benchmark" / "tasks" / "catalog.json").read_text(encoding="utf-8"))
    (args.review_bundle / "benchmark_catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.review_bundle / "codex_recommendation.json").write_text(json.dumps(recommendation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = args.review_bundle / "final_report.md"
    _write_report(report_path, environment, aggregates, recommendation, evaluation)
    report_dir = args.output_dir.parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(report_path, report_dir / f"{run_id}_report.md")
    print(json_path)
    print(args.review_bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
