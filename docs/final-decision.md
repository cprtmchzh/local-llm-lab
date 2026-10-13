# Final decision

Status: **Pending Windows benchmark**

Mac 개발 환경에서는 RTX 5070 Ti의 VRAM, TTFT, token/s, stable context, OOM 또는 최종 모델을 확정하지 않습니다. Windows에서 `scripts/windows/run_benchmark.ps1` 실행 후 생성된 `review_bundle/`을 독립 검토해야 합니다.

완료 시 다음 역할을 별도로 선택합니다: default chat, coding, security, agent, fast, best overall. Hard gate 실패 모델은 weighted total이 높아도 best overall이 될 수 없습니다.
