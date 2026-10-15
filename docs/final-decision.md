# Final decision

Status: **No eligible model**

2026-10-14 Windows RTX 5070 Ti 환경에서 4개 후보를 모델·과제별 3회 실행했습니다. 실행 증거와 결과는 `review_bundle/`에 있으며 `python -m benchmark.evidence --review-bundle review_bundle`로 재계산할 수 있습니다.

`agent_candidate`가 weighted total 92.228로 가장 높았지만 permission violation hard gate를 통과하지 못했습니다. 나머지 후보도 각 hard gate를 통과하지 못했으므로 역할별·전체 추천은 비어 있습니다.

역할은 default chat, coding, security, agent, fast, best overall로 별도 계산하지만, 현재는 hard gate를 통과한 후보가 없어 모두 비어 있습니다. Hard gate 실패 모델은 weighted total이 높아도 best overall이 될 수 없습니다.
