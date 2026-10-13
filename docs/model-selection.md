# Model selection

후보 태그는 2026-10-13 Ollama registry에서 확인했으며 `config/models.yaml`에 출처 URL과 확인일을 기록했습니다.

| Alias | Runtime tag | Purpose | Pull stage |
|---|---|---|---:|
| general_base | `qwen3:8b` | general baseline and first GPU gate | 1 |
| low_restriction | `huihui_ai/qwen3-abliterated:8b` | paired over-refusal comparison | 2 |
| reasoning_security | `deepseek-r1:8b` | reasoning/security candidate | 2 |
| agent_candidate | `gpt-oss:20b` | tool/agent candidate | 2 |

레지스트리 존재가 해당 하드웨어에서의 적합성을 뜻하지는 않습니다. 16 GB VRAM 적합성, 실제 offload, context 안정성, 정확성과 agent 성공률은 Windows 결과로만 결정합니다. Abliterated 파생 모델은 원본과 동일 조건으로 비교하고 거절률이 낮다는 이유만으로 채택하지 않습니다.
