# Local LLM Final Evaluation Report

> 이 파일은 Benchmark 완료 후 자동 채우는 템플릿이다.

## 1. Test Environment

- OS:
- CPU:
- GPU:
- VRAM:
- RAM:
- Driver:
- Ollama:
- Test Date:

## 2. Evaluated Models

| Model | Family | Params | Quant | Disk | Primary Role |
|---|---|---:|---|---:|---|
| | | | | | |

## 3. Evaluation Configuration

| Category | Weight |
|---|---:|
| Coding | 24 |
| Agent | 20 |
| Security | 18 |
| Reasoning | 12 |
| Chat/Korean | 8 |
| Hallucination Resistance | 8 |
| Restriction | 5 |
| Performance | 5 |

## 4. Overall Scores

| Rank | Model | Total | Hard Gate | Best Role |
|---:|---|---:|---|---|
| | | | | |

## 5. Category Scores

| Model | Chat | Coding | Reasoning | Security | Agent | Hallucination | Restriction | Performance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| | | | | | | | | |

## 6. Runtime Performance

| Model | VRAM Peak | RAM Peak | TTFT p50 | TTFT p95 | tok/s mean | Stable Context |
|---|---:|---:|---:|---:|---:|---:|
| | | | | | | |

## 7. Coding

- Best model:
- pass@1:
- final success:
- test pass:
- 주요 실패 유형:

## 8. Agent

- Best model:
- task completion:
- tool-call accuracy:
- recovery:
- permission violations:
- 주요 실패 유형:

## 9. Security

- Best model:
- correctness:
- hallucination:
- authorized over-refusal:
- CLI/tool accuracy:
- 주요 실패 유형:

## 10. Hallucination

- Lowest hallucination model:
- Critical hallucinations by model:
- 반복적으로 발견된 오류 유형:

## 10.1 Authorized Offensive Lab

| Model | Flag Capture | Tool Accuracy | Over-refusal | Permission Violations | Critical Hallucinations |
|---|---:|---:|---:|---:|---:|
| | | | | | |

## 11. Context Stability

| Model | 4K | 8K | 16K | 32K | 64K | Max Stable |
|---|---|---|---|---|---|---|
| | | | | | | |

## 12. Codex Recommendation

### Best Overall
- Model:
- Score:
- Reason:

### Role Assignment

```text
DEFAULT_CHAT_MODEL=
CODING_MODEL=
SECURITY_MODEL=
AGENT_MODEL=
FAST_MODEL=
BEST_OVERALL_MODEL=
```

## 13. Trade-offs

-
-
-

## 14. Rejected Candidates

| Model | Reason |
|---|---|
| | |

## 15. Independent Reviewer Notes

> Codex가 작성하지 않는다. 외부 검토용 빈 섹션으로 유지한다.

- Reviewer:
- Independent best overall:
- Differences from Codex recommendation:
- Reason:

## 16. Reproduction

```powershell
# 실제 재현 명령 기록
```

## 17. Known Limitations

-
