# Review bundle

이 폴더는 추천을 신뢰하지 않고도 원시 결과부터 독립적으로 재검토하기 위한 package입니다.

공식 Windows benchmark 후 다음 파일이 생성됩니다: `environment_snapshot.json`, `model_manifest.json`, `evaluation_config.json`, `benchmark_catalog.json`, `raw_results.jsonl`, `aggregate_scores.json`, `aggregate_scores.csv`, `offensive_summary.json`, `codex_recommendation.json`, `final_report.md`.

검토 순서는 `evaluation_config.json`과 `benchmark_catalog.json`을 확인한 뒤 `raw_results.jsonl`에서 점수를 재계산하고, 마지막에만 `codex_recommendation.json`을 비교하는 방식이 권장됩니다. Mac snapshot은 개발 기록일 뿐 공식 성능 증거가 아닙니다.
