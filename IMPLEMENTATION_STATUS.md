# Implementation Status

Checked on 2026-10-13 (Asia/Seoul).

| Phase | Implementation | Verified here | Remaining on Windows target |
|---|---|---|---|
| 1. Environment | Mac and Windows snapshot tools | Mac snapshot generated | Run Windows snapshot and confirm target hardware |
| 2. Runtime | install/start/local binding scripts | Static and Python checks | Install/start Ollama; verify localhost-only listener |
| 3. First model | Stage-1 pull and inference/stream/GPU gate | Gate logic tested indirectly | Pull only `qwen3:8b`; run GPU gate |
| 4. CLI | Chat, streaming, model/mode/context/stats/GPU/reset | Unit-tested and compiled | Live Ollama smoke test |
| 5. Models | Four role candidates with registry sources and staged pulls | Config/schema validated | Pull stage 2 only after stage 1 passes |
| 6. Prompts | Default/coding/security/agent profiles | Loaded by tests | Qualitative review with models |
| 7. Performance | TTFT, prompt/generation/load time, tok/s, VRAM/RAM/GPU sampling, 4K–64K probes | Logic compiled and scored with fixtures | Collect RTX 5070 Ti measurements |
| 8. Evaluation | All weighted categories, isolated offensive lab, raw JSONL, hard gates, CSV/JSON/report | End-to-end fixture and lab unit tests | Run three attempts per model/task |
| 9. Agent | Local Ollama tool loop, repository path boundary, explicit writes, safe command policy | Permission/workspace tests | Live model tool-call and WSL2/Docker validation |
| 10. Recommendation | Role formulas and independent review bundle | Development result remains pending by test | Official gate must pass before recommendation |

Current official decision: **pending Windows benchmark**. No performance number or model winner has been inferred from the Mac development machine.
