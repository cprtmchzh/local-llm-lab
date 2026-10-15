# Architecture

```text
CLI / Benchmark / Agent wrapper
            |
       localhost HTTP
            |
  Ollama 127.0.0.1:11434
            |
       Local models
```

공통 Python은 OS 독립적이며 외부 패키지가 없습니다. `cli.client`는 Ollama NDJSON streaming 응답에서 TTFT와 생성 통계를 수집합니다. `benchmark.runner`는 매 attempt를 append-only JSONL로 기록하고, `benchmark.scorers`는 raw data에서 category/weighted score와 hard gate를 다시 계산합니다.

Mac은 코드·테스트·문서 작업을 담당합니다. Windows는 Ollama, NVIDIA GPU, 실제 context/OOM/성능 benchmark를 담당합니다. Git에는 모델 파일, credential 또는 `.env`를 넣지 않습니다. 독립 재현에 필요한 versioned review bundle과 제한된 benchmark 응답 원문은 예외로 추적하며, 민감정보가 포함될 수 있는 임의 사용자 대화는 저장하지 않습니다.
