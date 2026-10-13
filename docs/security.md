# Security and privacy

답변 정책과 host 명령 권한은 분리합니다. 저거절 모델도 host 전체 shell 권한을 얻지 않습니다.

`agent.permissions.PermissionPolicy`의 기본 동작은 다음과 같습니다.

| Operation | Default |
|---|---|
| project read | allow |
| project write | ask |
| tests/build/lint | allow |
| git status/diff/log/show | allow |
| network | ask |
| dependency installation | ask |
| project-external path | deny |
| destructive command | deny |
| admin privilege | deny |

Ollama URL은 loopback HTTP만 허용합니다. Cloud model 사용은 기본 false이고 response text logging도 기본 false입니다. Docker helper는 network를 끄고 read-only root filesystem 및 repository-only mount를 사용합니다.

이 policy layer는 OS 보안 경계의 대체물이 아닙니다. 실제 agent 실행에는 WSL2 또는 Docker 격리를 권장하며 SSH key, browser profile, credential store와 개인 문서는 mount하지 않습니다.

공식 오펜시브 benchmark는 별도의 Docker 표적만 사용합니다. 표적에는 host volume, Docker socket, credential 또는 외부 network가 제공되지 않습니다. 모델 tool은 임의 URL을 받지 않고 `127.0.0.1:18080`으로 강제되며 GET/POST와 소수의 training header만 허용합니다.
