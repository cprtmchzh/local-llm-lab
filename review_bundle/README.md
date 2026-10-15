# Review bundle

이 폴더는 추천을 신뢰하지 않고도 원시 결과부터 독립적으로 재검토하기 위한 package입니다.

공식 Windows benchmark 후 다음 파일이 생성됩니다: `environment_snapshot.json`, `model_manifest.json`, `evaluation_config.json`, `benchmark_catalog.json`, `raw_results.jsonl`, `evidence_manifest.json`, `aggregate_scores.json`, `aggregate_scores.csv`, `offensive_summary.json`, `codex_recommendation.json`, `final_report.md`.

검토 순서는 `evidence_manifest.json`의 SHA-256을 확인하고, `evaluation_config.json`과 `benchmark_catalog.json`을 검토한 뒤 `raw_results.jsonl`에서 점수를 재계산하고, 마지막에만 `codex_recommendation.json`을 비교하는 방식이 권장됩니다.

```bash
python -m benchmark.evidence --review-bundle review_bundle
```

현재 번들은 집계 재현이 가능하지만 과거 실행에서 응답 본문을 저장하지 않았으므로 개별 evaluator 판정의 원문 감사는 불가능합니다. 이 제한은 `evidence_manifest.json`과 `final_report.md`에 명시되어 있습니다.
