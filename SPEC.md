# Local LLM Lab — 설계·구현·검증 명세서

## 1. 목적

본 프로젝트는 다음 Windows PC에서 외부 LLM API 의존을 최소화하고, Chat / Coding / Agent / 정보보안 연구에 사용할 수 있는 로컬 LLM 환경을 구축하고 검증하는 것을 목표로 한다.

### 대상 환경

| 항목 | 값 |
|---|---|
| OS | Windows |
| CPU | AMD Ryzen 7 7800X3D |
| GPU | NVIDIA RTX 5070 Ti |
| VRAM | 16 GB |
| RAM | 32 GB |
| 사용 가능 저장공간 | 약 500 GB |
| 주요 용도 | Chat, Coding, Agent, Security Research |
| 주 실행 방식 | CLI |
| 추가 예산 | 없음 |

### 핵심 요구사항

1. 로컬 추론을 기본값으로 한다.
2. 모델, 시스템 프롬프트, 컨텍스트 길이, 양자화 옵션을 사용자가 통제할 수 있어야 한다.
3. 프로젝트 코드와 프롬프트가 외부 서비스로 전송되지 않는 구성을 기본으로 한다.
4. 일반 모델과 저제약/저거절 파생 모델을 동일한 조건으로 비교할 수 있어야 한다.
5. 단순 답변 거절률이 아니라 정확성, 코딩 성공률, Agent 성공률, 보안 지식 정확성, Hallucination을 함께 평가한다.
6. Codex가 자동으로 최종 모델을 추천하되, 사람이 원시 결과를 재검토할 수 있는 산출물을 반드시 남긴다.
7. LLM의 답변 자유도와 실제 Host 명령 실행 권한을 분리한다.
8. 실행 명령은 가능한 한 재현 가능해야 한다.

---

# 2. 최종 아키텍처

```text
Windows Host
│
├─ PowerShell / Windows Terminal
│
├─ Local LLM Runtime
│   └─ Ollama (1차 기본 Runtime)
│       └─ 127.0.0.1:11434
│
├─ Models
│   ├─ General Base
│   ├─ Low-Restriction / Abliterated Candidate
│   ├─ Reasoning Candidate
│   └─ Agent Candidate
│
├─ Local CLI
│   ├─ chat
│   ├─ coding
│   ├─ security
│   └─ agent
│
├─ Agent Layer
│   ├─ OpenCode 또는 동등 CLI Agent
│   └─ Custom Wrapper (필요 시)
│
├─ Sandbox
│   ├─ WSL2
│   └─ Docker (선택)
│
└─ Evaluation Harness
    ├─ Chat
    ├─ Coding
    ├─ Reasoning
    ├─ Security
    ├─ Agent
    ├─ Restriction / Over-refusal
    ├─ Hallucination
    ├─ Performance
    └─ Context Stability
```

---

# 3. 구현 원칙

- 처음부터 모든 기능을 구현하지 않는다.
- 각 Phase가 실제로 동작하는 것을 검증한 뒤 다음 단계로 넘어간다.
- 환경, 모델 이름, 버전, 설치 여부를 추측하지 않는다.
- 모델 이름과 태그는 구현 시점에 현재 Registry/공식 배포 정보를 확인하여 확정한다.
- 첫 모델 하나로 GPU 추론을 검증한 뒤 추가 모델을 설치한다.
- 모든 중요한 설정은 코드에 Hard Coding하지 않고 config 파일로 분리한다.
- Benchmark 이전에는 최종 모델을 확정하지 않는다.
- 결과가 나쁜 저제약 모델을 단순히 “거절이 적다”는 이유로 채택하지 않는다.
- 모든 자동 추천 결과는 원시 결과로 역검증 가능해야 한다.

---


# 개발 / 실행 / 관리 환경 분리 원칙

본 프로젝트는 개발 머신과 실제 LLM 실행 머신을 분리하여 운영한다.

## 역할 분담

| 역할 | 환경 | 주요 작업 |
|---|---|---|
| 개발 / 편집 | macOS | Codex를 이용한 코드 작성, 문서 수정, Benchmark Harness 개발, CLI/Agent 로직 구현 |
| 실제 실행 / 검증 | Windows | Ollama 실행, NVIDIA GPU 추론, 모델 다운로드, VRAM/TTFT/token/s 측정, Context/OOM 검증, Agent 실환경 테스트 |
| 중앙 관리 | GitHub | Source Code, Config, Documentation, Benchmark 요약 결과, 변경 이력 관리 |

기본 흐름:

```text
Mac
 └─ Codex 기반 개발 / 수정
        │
        └─ git commit / push
                │
                ▼
GitHub
 └─ 중앙 Repository
        │
        └─ git pull
                │
                ▼
Windows
 └─ 실제 Local LLM 실행 / Benchmark / GPU 검증
        │
        └─ 결과 commit / push
                │
                ▼
GitHub
        │
        └─ Mac에서 결과 분석 / 개선
```

## 중요한 원칙

1. Mac에서 작성한 코드는 가능한 한 OS 독립적으로 구현한다.
2. RTX 5070 Ti, Ollama, NVIDIA Driver, VRAM, 실제 Context Length, TTFT, token/s 관련 검증은 Windows 결과만 공식 Benchmark로 인정한다.
3. Mac에서 측정된 LLM 성능 수치를 Windows 결과와 혼합하지 않는다.
4. Windows 머신에서 생성된 Benchmark에는 반드시 실행 환경 메타데이터를 포함한다.
5. 모델 파일 자체는 GitHub에 Push하지 않는다.
6. 대용량 Raw Result, Prompt/Response 원문, 개인 정보가 포함된 로그는 기본적으로 GitHub에 Push하지 않는다.
7. Source Code와 Config는 GitHub를 통해 양쪽 머신에서 동기화한다.
8. Windows에서 발견된 Runtime-specific 문제는 Mac에서 코드 수정 후 다시 Windows에서 검증한다.

## Script 분리

```text
scripts/
├─ mac/
│  ├─ bootstrap.sh
│  └─ dev_check.sh
└─ windows/
   ├─ check_environment.ps1
   ├─ install_ollama.ps1
   ├─ start_runtime.ps1
   ├─ gpu_status.ps1
   └─ run_benchmark.ps1
```

공통 로직은 OS 독립적인 Python 코드로 유지한다.

```text
cli/
agent/
benchmark/
config/
tests/
```

Windows 절대 경로를 Python 코드에 Hard Coding하지 않는다.

예:

```python
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
```

## Git 운영

권장 흐름:

```text
Mac 개발
→ GitHub push
→ Windows pull
→ 실행 / 검증
→ 결과 push
→ Mac 분석 / 수정
```

권장 Branch:

```text
main
dev
```

작은 규모에서는 단일 `main` 운영도 허용한다.

## 줄바꿈 관리

Repository Root에 `.gitattributes`를 둔다.

```gitattributes
* text=auto

*.sh text eol=lf
*.ps1 text eol=crlf
*.py text eol=lf
*.md text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.json text eol=lf
```

## 공식 Benchmark 실행 환경

Windows에서 생성되는 공식 Benchmark에는 최소 다음 메타데이터를 포함한다.

```json
{
  "execution_role": "benchmark",
  "os": "Windows",
  "cpu": "AMD Ryzen 7 7800X3D",
  "gpu": "NVIDIA RTX 5070 Ti",
  "vram_gb": 16,
  "ram_gb": 32
}
```

결과 경로:

```text
benchmark/results/
├─ windows-rtx5070ti/
│  ├─ raw/
│  ├─ aggregate/
│  └─ reports/
└─ mac-dev/
```

다음 지표는 Windows RTX 5070 Ti 머신에서 측정된 값만 최종 모델 선택에 사용한다.

- VRAM Peak
- RAM Peak
- TTFT
- Tokens/sec
- Model Load Time
- Max Stable Context
- OOM Count
- GPU Utilization
- Agent Runtime Performance

Chat/Coding/Security 논리 평가도 최종 비교 시 가능한 한 동일한 Windows Runtime에서 다시 실행한다.


---

# 4. 후보 모델군

정확한 모델명/태그는 실행 시점에 확인한다.

최소 다음 네 종류를 비교한다.

## A. General Base
목적:
- 일반 대화 기준점
- Coding
- Tool/Agent
- 저제약 파생 모델 대비 원본 성능 비교

권장 후보군:
- Qwen 계열 8B~14B
- 동급 최신 Open-weight General Model

## B. Low-Restriction / Abliterated
목적:
- 합법적/허가된 보안 연구 질의의 과잉 거절 감소
- 일반 기술 질의 완성도 비교

권장 후보군:
- Qwen 계열 저거절/abliterated 파생 모델
- 기타 신뢰할 수 있는 배포자의 저제약 파생 모델

## C. Reasoning / Security Candidate
목적:
- 복합 추론
- 취약점 원인 분석
- 코드/로그 분석
- 보안 연구

권장 후보군:
- DeepSeek Reasoning Distill 계열
- 동급 최신 Reasoning Model

## D. Agent Candidate
목적:
- Multi-step coding
- Tool use
- Repository 작업
- 오류 복구

권장 후보군:
- gpt-oss 20B급
- Qwen/DeepSeek의 Tool/Agent 성능이 좋은 변형

---

# 5. Runtime

1차 Runtime은 Ollama로 한다.

기본 API:
```text
http://127.0.0.1:11434
```

요구사항:
- Windows Native 실행
- NVIDIA GPU 사용
- Streaming
- 모델 교체
- 로컬 API
- Context 길이 조정
- CLI 및 Agent 연동

기본 보안/프라이버시:
- localhost bind
- cloud 기능 비활성화 가능 여부 확인 및 적용
- 외부 API를 기본값으로 사용하지 않음
- Prompt/Response 원문 로그 기본 비활성
- 로그 저장 여부 config로 제어

---

# 6. Repository 구조

```text
local-llm-lab/
├─ README.md
├─ SPEC.md
├─ CODEX_PROMPT.md
├─ docs/
│  ├─ architecture.md
│  ├─ installation.md
│  ├─ model-selection.md
│  ├─ benchmark-methodology.md
│  ├─ security.md
│  └─ final-decision.md
├─ config/
│  ├─ runtime.yaml
│  ├─ models.yaml
│  ├─ evaluation.yaml
│  └─ prompts/
│     ├─ default.txt
│     ├─ coding.txt
│     ├─ security.txt
│     └─ agent.txt
├─ scripts/
│  ├─ check_environment.ps1
│  ├─ install_runtime.ps1
│  ├─ pull_models.ps1
│  ├─ start_runtime.ps1
│  ├─ gpu_status.ps1
│  └─ run_benchmark.ps1
├─ cli/
│  ├─ main.py
│  ├─ client.py
│  ├─ config.py
│  └─ model_manager.py
├─ agent/
│  ├─ runner.py
│  ├─ permissions.py
│  ├─ sandbox.py
│  └─ adapters/
├─ benchmark/
│  ├─ runner.py
│  ├─ metrics.py
│  ├─ scorers.py
│  ├─ tasks/
│  └─ results/
│     ├─ raw/
│     ├─ aggregate/
│     └─ reports/
├─ review_bundle/
├─ tests/
└─ requirements.txt
```

---

# 7. Phase 1 — 환경 점검

`scripts/check_environment.ps1`을 작성하고 실제 실행한다.

검사항목:
- Windows version
- CPU
- RAM
- GPU
- VRAM
- NVIDIA Driver
- `nvidia-smi`
- PowerShell
- Python
- Git
- Ollama 설치 여부
- WSL2
- Docker
- 사용 가능 Disk
- 포트 11434 사용 상태

결과는 사람이 읽는 출력뿐 아니라 다음 파일에도 저장한다.

```text
review_bundle/environment_snapshot.json
```

필수 필드:
- timestamp
- os
- cpu
- ram_gb
- gpu
- vram_mb
- driver_version
- python_version
- ollama_version
- wsl_status
- docker_status
- free_disk_gb

---

# 8. Phase 2 — Runtime 구축

1. Ollama 설치 여부 확인
2. 미설치 시 설치
3. Runtime 시작
4. localhost API 연결 확인
5. GPU 사용 가능 여부 확인
6. Privacy 관련 설정 적용
7. API가 외부 인터페이스에 노출되지 않는지 확인

성공 조건:
- `/api/tags` 또는 동등 로컬 API 응답 성공
- 첫 모델 추론 성공
- `ollama ps` 또는 동등 상태 확인
- `nvidia-smi`에서 추론 중 VRAM 증가 확인

---

# 9. Phase 3 — 첫 모델 검증

처음에는 8B~10B급 모델 하나만 설치한다.

검증:
- 모델 pull
- 모델 load
- 한글 질의
- 코드 생성
- Streaming
- GPU 사용
- TTFT
- token/s
- VRAM
- RAM

실패 시 추가 모델을 다운로드하지 말고 먼저 해결한다.

---

# 10. Phase 4 — CLI

최종 목표:

```powershell
llm
llm --model <alias> --mode chat
llm --model <alias> --mode coding
llm --model <alias> --mode security
llm --model <alias> --mode agent
```

지원 명령:
```text
/models
/model
/mode
/system
/context
/reset
/stats
/gpu
/help
/exit
```

응답 후 선택적으로 표시:
```text
Model
Prompt tokens
Output tokens
TTFT
Tokens/sec
Duration
VRAM peak
RAM peak
```

---

# 11. Phase 5 — Model Manager

`config/models.yaml`에서 관리한다.

각 모델에 최소 다음 메타데이터를 저장한다.

```yaml
alias:
provider:
runtime_name:
family:
parameter_class:
quantization:
estimated_disk_gb:
roles:
source:
license:
notes:
```

실제 검증 후 다음 정보를 추가한다.

```yaml
measured:
  vram_peak_mb:
  ram_peak_mb:
  ttft_ms:
  tokens_per_second:
  max_stable_context:
```

전체 모델 목록은 최종적으로 다음 파일에도 저장한다.

```text
review_bundle/model_manifest.json
```

---

# 12. Phase 6 — System Prompt Profiles

`config/prompts/`에 분리한다.

## default
- 범용
- 짧고 명확한 응답

## coding
- 실행 가능한 코드
- 기존 구조 존중
- Test 우선
- 변경 이유와 검증 명시
- 존재하지 않는 API 추측 최소화

## security
- 정보보안 연구
- CTF
- 자체/허가된 Lab
- 취약점 분석
- 네트워크/로그 분석
- 역공학
- 보안 도구 이해

평가상 “정상적인 허가된 보안 질문을 불필요하게 거절하는지”를 별도 측정한다.

## agent
작업 루프:
```text
Inspect → Plan → Act → Observe → Verify → Re-plan → Complete
```

---

# 13. Phase 7 — 성능 측정

모든 모델에서 다음을 측정한다.

- model load time
- TTFT
- prompt evaluation time
- generation time
- output tokens
- tokens/sec
- VRAM baseline
- VRAM peak
- RAM peak
- GPU utilization peak
- OOM 여부

Context:
- 4K
- 8K
- 16K
- 32K
- 64K

모델이 지원하고 하드웨어상 현실적인 범위까지만 진행한다.

각 Context에서:
- 성공/실패
- OOM
- 속도
- 응답 품질
- 장문 정보 회수 정확도

를 기록한다.

---

# 14. Phase 8 — Benchmark Categories

## 14.1 Chat
평가:
- 한국어 이해
- 요약
- 지시 준수
- 긴 대화
- 표현 자연스러움

## 14.2 Coding
평가:
- Python
- TypeScript
- Rust
- Bug fix
- Refactoring
- Unit Test
- Multi-file patch
- Build/Test

핵심 객관 지표:
- compile/build success
- test pass rate
- task pass@1
- final task success
- patch iteration count

## 14.3 Reasoning
평가:
- 다단계 논리
- 조건 추론
- 원인 분석
- 계획 수립
- 장문 문제

## 14.4 Security
평가:
- 보안 개념
- 네트워크
- Web
- System
- Reverse Engineering
- Malware Analysis
- CTF
- 취약점 원인 분석
- 보안 도구/CLI 정확성
- 자체/허가 Lab 분석

핵심:
- technical correctness
- key point coverage
- nonexistent option/CVE/API hallucination
- over-refusal

## 14.5 Agent
난이도:
- L1: 단일 함수
- L2: 단일 파일 수정 + 테스트
- L3: 여러 파일 버그 수정
- L4: 기능 구현 + 테스트
- L5: Repository 수준 복합 작업

평가:
- task completion
- tool-call validity
- tool selection
- recovery
- test verification
- iterations
- permission-policy violations

## 14.6 Restriction / Over-refusal
합법적/허가된 테스트 컨텍스트에 대해 측정한다.

평가:
- refusal_rate
- partial_refusal_rate
- over_refusal_rate
- answer_completeness

“무조건 답변함”을 높은 품질로 간주하지 않는다.

## 14.7 Hallucination
특히 다음 오류를 별도 집계한다.
- 존재하지 않는 CLI flag
- 존재하지 않는 API
- 존재하지 않는 package/function
- 잘못된 CVE
- 잘못된 protocol claim
- 실행 불가능한 command

## 14.8 Performance
- TTFT
- tokens/sec
- VRAM
- RAM
- context stability

---

# 15. Agent 권한

답변 자유도와 실행 권한은 별도 계층으로 관리한다.

기본 정책:

| 행위 | 기본값 |
|---|---|
| 프로젝트 파일 읽기 | allow |
| 프로젝트 파일 수정 | allow/ask |
| 테스트 실행 | allow |
| build/lint | allow |
| git diff/status | allow |
| 네트워크 접근 | ask |
| 프로젝트 밖 파일 접근 | deny |
| destructive command | ask/deny |
| 관리자 권한 | deny |

Host 전체를 unrestricted shell로 열지 않는다.

---

# 16. Sandbox

권장 순서:
1. WSL2
2. Docker
3. 필요 시 Windows Sandbox

Agent가 접근하는 Repository 범위를 명확히 제한한다.

기본적으로 다음 민감 경로는 제외한다.
- SSH key
- browser profile
- credential store
- password manager
- 개인 문서
- OS 핵심 경로

---

# 17. 평가 점수 체계

최종 총점은 100점이다.

기본 가중치:

| Category | Weight |
|---|---:|
| Coding | 24 |
| Agent | 20 |
| Security | 18 |
| Reasoning | 12 |
| Chat / Korean | 8 |
| Hallucination Resistance | 8 |
| Restriction / Over-refusal | 5 |
| Performance | 5 |
| **Total** | **100** |

## 17.1 Coding Score (24)
구성 예:
- task pass@1: 35%
- final test pass: 30%
- build success: 15%
- patch correctness: 10%
- iteration efficiency: 10%

## 17.2 Agent Score (20)
- completion rate: 35%
- tool-call accuracy: 20%
- recovery success: 15%
- verification discipline: 15%
- permission correctness: 15%

## 17.3 Security Score (18)
- technical correctness: 40%
- key coverage: 25%
- tool/command accuracy: 15%
- analysis depth: 10%
- authorized-task completion: 10%

## 17.4 Reasoning Score (12)
- correctness: 60%
- consistency: 20%
- instruction adherence: 20%

## 17.5 Chat/Korean Score (8)
- relevance: 30%
- Korean quality: 30%
- instruction adherence: 20%
- context retention: 20%

## 17.6 Hallucination Resistance (8)
오류율이 낮을수록 높은 점수.

특히 보안/CLI/API hallucination에는 높은 패널티를 준다.

## 17.7 Restriction / Over-refusal (5)
허가된 정상 작업에 대한 불필요한 거절이 적을수록 높은 점수.

정확하지 않은 답변을 제공한 경우에는 이 점수가 높더라도 전체적으로 채택하지 않는다.

## 17.8 Performance (5)
- tokens/sec
- TTFT
- VRAM 효율
- context 안정성

---

# 18. Hard Gate

다음 중 하나라도 해당하면 “Default 추천”에서 제외할 수 있다.

- 반복적인 OOM
- 정상적인 Context에서 불안정
- Coding final success가 최소 기준 미달
- 심각한 보안 Hallucination
- Tool call 형식이 지속적으로 깨짐
- permission-policy violation
- Offline/Local 요구를 충족하지 못함

Hard Gate 기준은 `config/evaluation.yaml`에서 조정 가능하게 한다.

---

# 19. 원시 결과 저장

모든 Benchmark 시도는 반드시 JSONL 한 줄로 저장한다.

```text
benchmark/results/raw/<run_id>.jsonl
```

필수 필드 정의는 `EVALUATION_SCHEMA.md`를 따른다.

중요:
- 성공한 결과만 저장하지 않는다.
- 실패, timeout, OOM, refusal도 모두 저장한다.
- 사람이 직접 다시 계산할 수 있도록 원시 metric을 남긴다.
- 집계 점수만 남기지 않는다.

---

# 20. 집계 결과

다음 파일 생성:

```text
benchmark/results/aggregate/<run_id>_scores.json
benchmark/results/aggregate/<run_id>_scores.csv
benchmark/results/reports/<run_id>_report.md
```

각 모델에 대해:
- category score
- total score
- hard gate status
- strengths
- weaknesses
- recommended roles
를 기록한다.

---

# 21. Codex 자동 추천

Codex는 최종적으로 다음 역할별 모델을 추천한다.

```text
DEFAULT_CHAT_MODEL
CODING_MODEL
SECURITY_MODEL
AGENT_MODEL
FAST_MODEL
BEST_OVERALL_MODEL
```

단, 추천 근거에는 반드시:
- 총점
- 핵심 세부 지표
- Hard Gate
- 성능/VRAM trade-off
를 포함한다.

Codex의 추천 결과는 다음 파일로 저장한다.

```text
review_bundle/codex_recommendation.json
```

---

# 22. 외부 검토용 Review Bundle

최종 검증 완료 후 `review_bundle/`에 다음 파일을 반드시 복사/생성한다.

```text
review_bundle/
├─ environment_snapshot.json
├─ model_manifest.json
├─ evaluation_config.json
├─ benchmark_catalog.json
├─ raw_results.jsonl
├─ aggregate_scores.json
├─ aggregate_scores.csv
├─ codex_recommendation.json
├─ final_report.md
└─ README.md
```

이 폴더 하나만 별도 AI 또는 사람에게 제공해도 재평가가 가능해야 한다.

## 매우 중요

외부 검토자가 Codex의 자연어 결론을 보지 않고도 판단할 수 있어야 한다.

따라서:
- raw_results.jsonl에는 개별 task 결과
- aggregate_scores.json에는 계산값
- evaluation_config.json에는 weight 및 normalization
- benchmark_catalog.json에는 문제 정의 및 정답/평가 방식
을 포함한다.

---

# 23. ChatGPT 독립 검토를 위한 필수 데이터

향후 ChatGPT가 독립적으로 판단할 수 있도록 최소 다음 지표를 모델별로 남긴다.

```text
model_id
model_family
parameter_class
quantization
disk_size_gb

vram_peak_mb
ram_peak_mb

ttft_p50_ms
ttft_p95_ms
tokens_per_second_mean
tokens_per_second_p10

max_stable_context

chat_score
coding_score
reasoning_score
security_score
agent_score
hallucination_resistance_score
restriction_score
performance_score
weighted_total_score

coding_pass_at_1
coding_final_success_rate
test_pass_rate

agent_task_completion_rate
agent_tool_call_accuracy
agent_recovery_rate
agent_permission_violation_rate

security_correctness_rate
security_hallucination_rate
authorized_security_over_refusal_rate

hallucination_rate_total

oom_count
timeout_count
failed_run_count
total_run_count
```

---

# 24. Codex 결론과 외부 결론 분리

최종 보고서는 다음 두 개를 구분한다.

## A. Codex Recommendation
Codex가 자동 점수와 관찰 결과를 바탕으로 내린 결론.

## B. Reviewer Input Package
결론 없이 원시 데이터와 계산식을 제공.

Codex가 B에 자신의 주관적 추천을 섞지 않도록 한다.

---

# 25. 최종 보고서

`review_bundle/final_report.md`에 다음을 포함한다.

1. 환경
2. 모델 목록
3. Benchmark 방법
4. 모델별 총점
5. 모델별 세부점수
6. 성능
7. Context 안정성
8. Coding 결과
9. Agent 결과
10. Security 결과
11. Restriction/Over-refusal
12. Hallucination
13. Codex 추천
14. 역할별 추천
15. 알려진 한계
16. 재현 명령

---

# 26. Definition of Done

## Environment
- GPU 식별
- NVIDIA 추론 확인
- Ollama API 확인

## Runtime
- localhost 실행
- 최소 3개 모델 검증

## CLI
- Chat
- Streaming
- Model switch
- Mode switch
- Stats

## Benchmark
- 모든 Category 실행 가능
- 원시 JSONL 저장
- 자동 집계 가능
- 점수 재계산 가능

## Agent
- Repository 읽기
- 수정
- Test
- 오류 복구
- Permission 적용

## Privacy
- 기본 Local-only
- Cloud 기능 비활성
- Offline test

## Review
- `review_bundle/` 생성
- Codex recommendation과 raw data 분리
- 외부 검토자가 점수를 재계산할 수 있음

---

# 27. 최종 목표

프로젝트 종료 시 다음 질문에 수치로 답할 수 있어야 한다.

1. 이 PC에서 가장 좋은 전체 모델은 무엇인가?
2. Coding 최고 모델은 무엇인가?
3. Agent 최고 모델은 무엇인가?
4. Security Research 최고 모델은 무엇인가?
5. 허가된 보안 연구 질문을 가장 덜 과잉 거절하는 모델은 무엇인가?
6. 저제약 파생 모델의 성능 손실은 얼마인가?
7. 가장 안정적인 Context 길이는 얼마인가?
8. 모델별 실제 VRAM/RAM 사용량은 얼마인가?
9. 모델별 실제 TTFT/token/s는 얼마인가?
10. Codex 추천과 외부 독립 평가가 같은 결론을 내리는가?
