# Local LLM Lab

Windows RTX 5070 Ti 시스템에서 Ollama 기반 로컬 LLM을 동일 조건으로 검증하고, 원시 결과에서 역할별 추천을 재계산할 수 있게 하는 CLI와 평가 도구입니다. 개발은 macOS, 공식 모델 실행과 성능 측정은 Windows에서 수행합니다.

현재 상태는 **구현 및 Mac 단위 검증 단계**입니다. Windows 공식 benchmark가 끝나기 전에는 어떤 모델도 최종 추천으로 표시하지 않습니다.

세부 진행 상태는 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)에 기록합니다.

## 빠른 시작

### Mac 개발

```bash
./scripts/mac/bootstrap.sh
./scripts/mac/dev_check.sh
```

### Windows 실행

PowerShell에서 다음 순서를 지킵니다.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check_environment.ps1
.\scripts\windows\install_runtime.ps1
.\scripts\windows\start_runtime.ps1
.\scripts\windows\pull_models.ps1 -Stage 1
.\scripts\windows\verify_first_model.ps1
```

첫 모델의 추론과 GPU 사용이 확인된 뒤에만 나머지 후보를 받습니다.

```powershell
.\scripts\windows\pull_models.ps1 -Stage 2
python -m pip install -e .
llm --model general_base --mode chat
.\scripts\windows\run_benchmark.ps1 -Attempts 3
```

공식 benchmark에는 localhost 전용 Docker 실습 표적에서 수행하는 정찰, SQL Injection, IDOR 과제가 포함됩니다. Docker Desktop이 실행 중이어야 하며, 표적 컨테이너는 외부 네트워크가 차단되고 benchmark 종료 시 자동 제거됩니다.

## CLI

```text
llm
llm --model general_base --mode coding "Python으로 이 함수를 고쳐줘"
```

대화형 명령은 `/models`, `/model`, `/mode`, `/system`, `/context`, `/reset`, `/stats`, `/gpu`, `/help`, `/exit`입니다. 런타임 URL은 localhost만 허용하며 응답 원문은 기본적으로 저장하지 않습니다.

Repository 범위 coding agent는 쓰기를 명시적으로 허용해야 합니다.

```text
llm-agent --model agent_candidate --project-root . --allow-write "실패하는 테스트를 고치고 다시 실행해줘"
```

## 평가 산출물

공식 실행은 `review_bundle/`에 환경, 모델 manifest, 평가 설정, task catalog, raw JSONL, 집계 JSON/CSV, 별도 추천과 보고서를 만듭니다. `aggregate_scores.*`와 `raw_results.jsonl`에는 추천 문장을 넣지 않습니다.

구체적인 설치와 운영은 [installation](docs/installation.md), 점수 계산은 [benchmark methodology](docs/benchmark-methodology.md), 권한 정책은 [security](docs/security.md)를 참고하세요. 원본 요구사항은 [SPEC.md](SPEC.md)와 [EVALUATION_SCHEMA.md](EVALUATION_SCHEMA.md)입니다.

## 현재 제한

- 이 Mac에는 Ollama와 NVIDIA GPU가 없어 실제 추론 및 성능 수치를 확정하지 않습니다.
- 기본 task catalog는 파이프라인 검증용 smoke set입니다. 공식 비교 전 더 넓은 versioned task set을 추가해야 합니다.
- 커뮤니티 abliterated 모델은 연구용 후보이며, 라이선스·출력 안전성·정확성을 별도로 검토해야 합니다.
- 오펜시브 결과는 지정된 일회성 실습 표적에 대한 성공률일 뿐, 제3자 시스템에 대한 실행 권한을 부여하지 않습니다.
