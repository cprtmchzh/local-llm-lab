from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cli.config import ROOT

from .scorers import load_rows, main as score_main


JSON_OUTPUTS = (
    "aggregate_scores.json",
    "benchmark_catalog.json",
    "codex_recommendation.json",
    "evaluation_config.json",
    "evidence_manifest.json",
    "model_manifest.json",
    "offensive_summary.json",
)


class EvidenceError(ValueError):
    pass


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"Cannot read JSON evidence {path}: {exc}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expect(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise EvidenceError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def validate_manifest(review_bundle: Path) -> dict[str, Any]:
    manifest = _load_json(review_bundle / "evidence_manifest.json")
    raw_info = manifest.get("raw_results", {})
    raw_name = str(raw_info.get("path", ""))
    if raw_name != "raw_results.jsonl":
        raise EvidenceError("evidence_manifest raw_results.path must be raw_results.jsonl")
    raw_path = review_bundle / raw_name
    if not raw_path.is_file():
        raise EvidenceError(f"Missing raw evidence: {raw_path}")

    rows = load_rows([raw_path])
    pair_counts = Counter((str(row.get("model_id")), str(row.get("task_id"))) for row in rows)
    status_counts = dict(sorted(Counter(str(row.get("status")) for row in rows).items()))
    role_counts = dict(sorted(Counter(str(row.get("execution_role")) for row in rows).items()))
    _expect(_sha256(raw_path), raw_info.get("sha256"), "raw SHA-256")
    _expect(raw_path.stat().st_size, raw_info.get("size_bytes"), "raw size")
    _expect(len(rows), raw_info.get("row_count"), "raw row count")
    _expect(len(pair_counts), raw_info.get("model_task_pair_count"), "model/task pair count")
    _expect(sorted(set(pair_counts.values())), raw_info.get("attempts_per_pair"), "attempts per pair")
    _expect(role_counts, raw_info.get("execution_roles"), "execution role counts")
    _expect(status_counts, raw_info.get("status_counts"), "status counts")
    _expect(sorted({str(row.get("run_id")) for row in rows}), manifest.get("run_ids"), "run IDs")

    model_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        model_rows[str(row.get("model_id"))].append(row)
    models = [
        {
            "model_id": model_id,
            "row_count": len(values),
            "failed_run_count": sum(
                row.get("status") in {"failure", "timeout", "oom", "tool_error"} for row in values
            ),
            "timeout_count": sum(row.get("status") == "timeout" for row in values),
        }
        for model_id, values in sorted(model_rows.items())
    ]
    _expect(models, manifest.get("models"), "model summaries")

    response_info = manifest.get("response_evidence", {})
    stored = sum(bool(row.get("response_saved")) for row in rows)
    nonempty = sum(bool(str(row.get("response_text") or "")) for row in rows)
    _expect(stored, response_info.get("stored_rows"), "stored response count")
    _expect(nonempty, response_info.get("nonempty_rows"), "non-empty response count")
    _expect(len(rows), response_info.get("total_rows"), "response evidence total")

    return {
        "rows": len(rows),
        "pairs": len(pair_counts),
        "sha256": raw_info["sha256"],
        "run_ids": manifest["run_ids"],
        "response_audit_complete": bool(response_info.get("independent_output_audit_complete")),
    }


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_bundle(review_bundle: Path, schema_path: Path | None = None) -> dict[str, Any]:
    review_bundle = review_bundle.resolve()
    schema_path = schema_path or ROOT / "docs" / "schemas" / "REVIEW_OUTPUT_SCHEMA.json"
    schema = _load_json(schema_path)
    missing = [name for name in schema["required_files"] if not (review_bundle / name).is_file()]
    if missing:
        raise EvidenceError(f"Review bundle is missing required files: {', '.join(missing)}")

    summary = validate_manifest(review_bundle)
    raw_path = review_bundle / "raw_results.jsonl"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        aggregate_dir = root / "aggregate"
        recomputed = root / "review_bundle"
        recomputed.mkdir()
        shutil.copyfile(review_bundle / "environment_snapshot.json", recomputed / "environment_snapshot.json")
        with contextlib.redirect_stdout(io.StringIO()):
            result = score_main(
                [
                    str(raw_path),
                    "--output-dir",
                    str(aggregate_dir),
                    "--review-bundle",
                    str(recomputed),
                ]
            )
        if result != 0:
            raise EvidenceError(f"Scorer returned {result} while reproducing the review bundle")

        for name in JSON_OUTPUTS:
            _expect(_load_json(recomputed / name), _load_json(review_bundle / name), name)
        _expect(
            _csv_rows(recomputed / "aggregate_scores.csv"),
            _csv_rows(review_bundle / "aggregate_scores.csv"),
            "aggregate_scores.csv",
        )
        _expect(
            (recomputed / "final_report.md").read_text(encoding="utf-8").replace("\r\n", "\n"),
            (review_bundle / "final_report.md").read_text(encoding="utf-8").replace("\r\n", "\n"),
            "final_report.md",
        )
        _expect(
            load_rows([recomputed / "raw_results.jsonl"]),
            load_rows([raw_path]),
            "raw_results.jsonl rows",
        )
    return summary


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Verify and independently reproduce a benchmark review bundle")
    value.add_argument("--review-bundle", type=Path, default=ROOT / "review_bundle")
    value.add_argument("--schema", type=Path)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        summary = verify_bundle(args.review_bundle, args.schema)
    except EvidenceError as exc:
        print(f"EVIDENCE_VERIFICATION_FAILED: {exc}")
        return 1
    print(
        "EVIDENCE_VERIFIED "
        f"rows={summary['rows']} pairs={summary['pairs']} sha256={summary['sha256']} "
        f"response_audit_complete={str(summary['response_audit_complete']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
