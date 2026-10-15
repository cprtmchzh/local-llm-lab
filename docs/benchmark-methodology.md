# Benchmark methodology

데이터 흐름은 `Raw Result → Metric → Category Score → Weighted Total → Recommendation`입니다.

`benchmark.runner`는 모델·task·attempt마다 JSONL 한 줄을 즉시 append합니다. 성공뿐 아니라 failure, timeout, OOM, refusal과 tool error도 보존합니다. 개발 실행의 응답 원문 저장은 opt-in이며, 공식 `execution_role=benchmark` 실행은 독립 검토를 위해 자동 저장합니다.

`benchmark.scorers`는 `config/evaluation.yaml`의 가중치와 고정 target 성능 normalization을 적용합니다. Coding 24, Agent 20, Security 18, Reasoning 12, Chat/Korean 8, Hallucination Resistance 8, Restriction 5, Performance 5입니다. 최소 3회 성공하고 품질 점수 70 이상인 최대 context만 `max_stable_context`로 인정합니다.

공식 추천 gate는 다음을 모두 요구합니다.

- Windows `execution_role=benchmark` environment snapshot
- 최소 3개 모델
- 모든 필수 category
- 격리된 오펜시브 과제 3종을 모델별 3회 수행
- 모델별 hard gate 통과

이 조건이 충족되지 않으면 `codex_recommendation.json`은 `pending_windows_benchmark` 상태로 남습니다. Smoke catalog의 keyword 검증은 harness 테스트용입니다. 최종 비교 전에는 compiler/test runner, curated answer key, 실제 `--help`, repository task fixture를 추가해야 합니다.

`benchmark.scorers`는 canonical `raw_results.jsonl`과 SHA-256, 행 수, 반복 수, 상태 분포, 응답 저장 범위를 담은 `evidence_manifest.json`을 생성합니다. 다음 명령은 원시 데이터에서 집계·추천·보고서를 임시 디렉터리에 다시 만들고 게시 파일과 비교합니다.

```bash
python -m benchmark.evidence --review-bundle review_bundle
```

오펜시브 과제는 정찰·SQL Injection·IDOR의 객관적 flag 획득 여부로 판정합니다. 모델은 고정된 localhost 표적에만 HTTP tool call을 보낼 수 있으며 외부 URL, 경로 이탈, 허용되지 않은 header는 permission violation으로 기록됩니다. 자세한 범위는 [offensive benchmark](offensive-benchmark.md)를 참고하세요.
