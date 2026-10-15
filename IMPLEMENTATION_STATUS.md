# Implementation Status

Checked on 2026-10-15 (Asia/Seoul).

| Phase | Implementation | Verified evidence | Remaining work |
|---|---|---|---|
| 1. Environment | Mac and Windows snapshot tools | Windows 11, Ryzen 7 7800X3D, RTX 5070 Ti, driver 591.86 snapshot published | Re-run snapshot after material hardware/driver changes |
| 2. Runtime | install/start/local binding scripts | Ollama 0.40.3 and localhost-only listener recorded | Keep runtime versions pinned per benchmark |
| 3. First model | Stage-1 pull and inference/stream/GPU gate | Stage gate completed before the four-model run | Automate persistent GPU stability settings after reboot |
| 4. CLI | Chat, streaming, model/mode/context/stats/GPU/reset | Unit tests and Windows live model execution completed | Expand end-to-end CLI fixtures |
| 5. Models | Four role candidates with registry sources and staged pulls | Four runtime names, digests, sizes and measurements published | Re-run when a model digest changes |
| 6. Prompts | Default/coding/security/agent profiles | All profiles executed by the official task catalog | Add curated qualitative review |
| 7. Performance | TTFT, prompt/generation/load time, tok/s, VRAM/RAM/GPU sampling, 4K–64K probes | RTX 5070 Ti measurements collected; no model met the stable-context quality rule | Diagnose failed needle retrieval and long generations |
| 8. Evaluation | Weighted categories, isolated offensive lab, raw JSONL, hard gates, CSV/JSON/report | 180 rows, 60 model/task pairs, 3 attempts each; aggregate replay matches | Future runs must retain response bodies for full audit |
| 9. Agent | Local tool loop, path boundary, explicit writes, safe command policy | Permission/workspace tests and isolated HTTP tool tasks completed | Add a live repository-editing acceptance scenario |
| 10. Recommendation | Role formulas and independent review bundle | Official result is `no_eligible_model`; all four candidates failed hard gates | Evaluate new candidates or adjust only predeclared gates in a new run |
| 11. Evidence CI | SHA-256 manifest, scorer replay, bundle comparison, Actions artifact | Local verifier reproduces aggregate, recommendation and report from raw JSONL | Confirm each pushed commit in GitHub Actions |

Current official decision: **no eligible model**. `agent_candidate` has the highest weighted score (92.228) but fails the permission-violation hard gate.

The published legacy run contains all 180 metric rows but no model response bodies. Its aggregate is reproducible; individual evaluator decisions are not fully auditable. Current official runners save response bodies automatically.
