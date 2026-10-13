# Installation and phased execution

## Prerequisites

- Windows target: Python 3.11+, Git, NVIDIA driver, 약 500 GB 여유 공간
- Ollama는 `scripts/windows/install_runtime.ps1`로 설치하거나 공식 설치 프로그램을 사용합니다.
- 모든 API 요청은 `127.0.0.1:11434`로 제한합니다.

## Phase gate

1. `check_environment.ps1`가 `review_bundle/environment_snapshot.json`을 생성합니다.
2. `start_runtime.ps1`가 localhost API를 확인합니다.
3. `pull_models.ps1 -Stage 1`은 `qwen3:8b` 하나만 받습니다.
4. `verify_first_model.ps1`가 추론과 `ollama ps`의 GPU 표시를 검증합니다.
5. 이 gate가 성공한 뒤 `-Stage 2`로 비교 모델을 받습니다.
6. `run_benchmark.ps1 -Attempts 3`으로 공식 raw result와 review bundle을 만듭니다.

Stage 2 gate를 우회해 처음부터 모든 모델을 받는 흐름은 지원하지 않습니다.

## Troubleshooting

- API 실패: `ollama serve` 프로세스와 `Test-NetConnection 127.0.0.1 -Port 11434`를 확인합니다.
- GPU 미사용: 최신 NVIDIA driver, `nvidia-smi`, `ollama ps`의 PROCESSOR 열을 확인합니다.
- OOM: context를 낮추고 다른 모델을 추가로 받기 전에 첫 모델을 안정화합니다.
- PowerShell 정책: 현재 terminal에만 `Set-ExecutionPolicy -Scope Process Bypass`를 적용할 수 있습니다.
