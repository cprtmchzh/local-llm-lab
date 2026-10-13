# Codex 실행 프롬프트 — Local LLM Lab

아래 작업을 시작하기 전에 Repository 루트의 `SPEC.md`와 `EVALUATION_SCHEMA.md`를 전부 읽어라.

두 문서를 본 프로젝트의 Source of Truth로 사용한다.

## 목표

Windows + Ryzen 7 7800X3D + RTX 5070 Ti 16GB + RAM 32GB 환경에서 다음을 구축한다.

- Local LLM Runtime
- CLI Chat
- Coding
- Security Research
- Coding Agent
- Model Benchmark
- Model Selection
- 재검토 가능한 Evaluation Output

최종 목적은 특정 모델을 미리 정하는 것이 아니라, 실제 PC에서 여러 모델을 동일 조건으로 검증한 뒤 역할별 최적 모델을 선정하는 것이다.

---

# 반드시 지킬 원칙

1. 현재 시스템 상태를 추측하지 말고 실제 명령으로 조사한다.
2. 처음부터 모든 모델을 다운로드하지 않는다.
3. 가장 먼저 8B~10B급 모델 하나로 GPU 추론을 검증한다.
4. 각 Phase가 동작한 뒤 다음 Phase로 진행한다.
5. 오류가 발생하면 원인을 조사하고 수정한 뒤 계속 진행한다.
6. Runtime/Model 이름과 버전은 현재 실제 배포 상태를 확인하여 사용한다.
7. Benchmark가 끝나기 전 특정 모델을 최종 선정하지 않는다.
8. 저거절/abliterated 모델은 반드시 원본 또는 일반 모델과 비교한다.
9. 단순 거절률보다 정확성, Hallucination, Coding/Agent 성공률을 더 중요하게 평가한다.
10. LLM 답변 자유도와 Host 명령 실행 권한을 분리한다.
11. Host 전체를 unrestricted shell로 노출하지 않는다.
12. Cloud/API 사용은 기본값으로 사용하지 않는다.
13. 설정은 config 파일로 분리한다.
14. 구현과 동시에 README와 docs를 갱신한다.
15. 테스트와 실제 명령 실행 없이 “완료”라고 판단하지 않는다.

---


# 개발 / 실행 / 관리 머신 규칙

이 프로젝트는 다음 역할을 명확히 분리한다.

```text
Mac     = 개발 / 편집 / Codex 작업
Windows = 실제 Local LLM 실행 / NVIDIA GPU / Benchmark
GitHub  = 중앙 Repository / 동기화 / 버전관리
```

Codex는 현재 자신이 실행되는 머신의 역할을 확인하고 그 역할에 맞는 작업만 수행한다.

## Mac에서 수행

- Repository 구조 작성
- Python/CLI/Agent 코드 구현
- Benchmark Harness 작성
- Config 및 문서 작성
- Unit Test
- OS 독립 로직 검증
- Git commit / push

Mac에서는 RTX 5070 Ti 관련 성능 수치를 최종값으로 확정하지 않는다.

## Windows에서 수행

- Ollama 실제 설치/실행
- 모델 다운로드
- NVIDIA GPU 추론 확인
- `nvidia-smi`
- VRAM 측정
- TTFT 측정
- token/s 측정
- Context Length Benchmark
- OOM 검증
- OpenCode/Agent 실제 실행
- WSL2/Docker Sandbox 검증
- 공식 Benchmark 생성

Windows에서 실행한 결과만 최종 Hardware/Performance Benchmark로 인정한다.

## GitHub

관리 대상:
- Source Code
- Config
- Documentation
- Test
- Benchmark Schema
- 집계/요약 결과
- 변경 이력

기본 Push 제외:
- Ollama 모델 파일
- 대형 모델 Cache
- `.env`
- Credential
- 개인정보
- Prompt/Response 원문 로그
- 대용량 Raw Benchmark Artifact

## Cross-platform 구현

공통 Python 코드는 OS 독립적으로 작성한다.

OS별 스크립트:

```text
scripts/mac/
scripts/windows/
```

작업 흐름:

```text
Mac 개발
→ GitHub push
→ Windows pull
→ Windows 실행/검증
→ 결과 push
→ Mac 분석/수정
→ 반복
```

Benchmark 결과에는 반드시 실행 머신 정보와 `execution_role`을 기록한다.


---

# 작업 순서

## Phase 1 — Repository 및 Environment

- 기존 Repository 확인
- 필요한 폴더 생성
- `scripts/check_environment.ps1` 구현
- 실제 실행
- GPU/VRAM/Driver/Python/Ollama/WSL/Docker/Disk 확인
- `review_bundle/environment_snapshot.json` 생성

## Phase 2 — Runtime

- Ollama 설치 확인
- 필요 시 설치
- localhost 실행
- local API 확인
- privacy/cloud 설정 확인
- NVIDIA GPU 사용 확인

## Phase 3 — First Model

- 8B~10B급 범용 모델 하나 선택
- 설치
- chat
- coding
- streaming
- GPU
- TTFT
- token/s
검증

이 단계 성공 전에는 대형 모델을 추가 설치하지 않는다.

## Phase 4 — CLI

다음을 구현한다.

```text
llm
llm --model <alias> --mode <mode>
```

지원:
- chat
- coding
- security
- agent
- model switch
- context
- stats
- gpu
- reset

## Phase 5 — Models

비교용 후보를 선정한다.

최소:
- General Base
- Low-Restriction/Abliterated
- Reasoning/Security
- Agent Candidate

현재 Registry에서 존재하는 정확한 태그를 사용한다.

`review_bundle/model_manifest.json`에 실제 모델 정보를 저장한다.

## Phase 6 — Benchmark Harness

`SPEC.md`와 `EVALUATION_SCHEMA.md`에 정의된 Category를 구현한다.

- Chat
- Coding
- Reasoning
- Security
- Agent
- Restriction/Over-refusal
- Hallucination
- Performance
- Context Stability
- Authorized Offensive Lab (isolated Docker target only)

## Phase 7 — Raw Results

각 benchmark attempt마다 반드시 한 줄의 JSONL을 저장한다.

성공뿐 아니라:
- failure
- refusal
- timeout
- OOM
- tool error
도 저장한다.

원시 결과는 후처리로 덮어쓰지 않는다.

## Phase 8 — Scoring

`EVALUATION_SCHEMA.md`의 가중치와 normalization을 적용하여 모델별 점수를 계산한다.

결과:
- category score
- total score
- hard gate status

를 생성한다.

## Phase 9 — Coding Agent

OpenCode 또는 동등한 CLI Agent를 검토하여 가장 적절한 방식을 사용한다.

Agent는:
- repository read
- edit
- test
- build/lint
- git diff
를 수행할 수 있어야 한다.

Network, destructive command, project 외부 접근은 permission layer로 통제한다.

가능하면 WSL2/Docker sandbox에서 실행한다.

## Phase 10 — Final Evaluation

역할별 추천:

```text
DEFAULT_CHAT_MODEL
CODING_MODEL
SECURITY_MODEL
AGENT_MODEL
FAST_MODEL
BEST_OVERALL_MODEL
```

를 결정한다.

그러나 추천 결과와 원시 데이터는 반드시 분리한다.

---

# 매우 중요한 최종 산출물

모든 평가가 끝나면 다음 폴더를 생성한다.

```text
review_bundle/
├─ environment_snapshot.json
├─ model_manifest.json
├─ evaluation_config.json
├─ benchmark_catalog.json
├─ raw_results.jsonl
├─ aggregate_scores.json
├─ aggregate_scores.csv
├─ offensive_summary.json
├─ codex_recommendation.json
├─ final_report.md
└─ README.md
```

이 폴더는 Codex의 결론을 신뢰하지 않아도 다른 AI 또는 사람이 독립적으로 다시 평가할 수 있어야 한다.

---

# Codex 추천 파일

`codex_recommendation.json`은 다음 구조를 따른다.

```json
{
  "best_overall": {
    "model_id": "",
    "score": 0,
    "reasons": []
  },
  "roles": {
    "chat": "",
    "coding": "",
    "security": "",
    "agent": "",
    "fast": ""
  },
  "rejected_candidates": [
    {
      "model_id": "",
      "reason": ""
    }
  ],
  "tradeoffs": [],
  "confidence": 0.0
}
```

---

# 외부 검토를 위한 규칙

`review_bundle/raw_results.jsonl`과 `aggregate_scores.json`에는 Codex의 주관적인 추천 문장을 넣지 않는다.

다음은 객관 데이터로만 구성한다.

- 모델 정보
- 환경
- Task
- 실제 결과
- 자동 검증 결과
- 시간
- 메모리
- 성공/실패
- 거절
- Hallucination
- Tool 결과
- 점수 계산값

나중에 이 `review_bundle/` 폴더를 ChatGPT에 제공하여 Codex의 추천과 별개로 다시 판단할 수 있어야 한다.

---

# 진행 방식

지금은 Phase 1부터 시작한다.

먼저:
1. Repository를 조사한다.
2. 환경 점검 스크립트를 작성한다.
3. 실제 실행한다.
4. `environment_snapshot.json`을 생성한다.
5. 발견된 환경과 문제를 정리한다.
6. 바로 해결 가능한 문제는 해결한다.
7. Phase 2로 진행한다.

사용자에게 이미 제공된 정보는 다시 질문하지 말고 실제 시스템 검사로 확인한다.

정말로 실행을 막는 정보가 없는 한 구현을 계속 진행한다.
