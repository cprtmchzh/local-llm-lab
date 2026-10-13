from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxConfig:
    project_root: Path
    backend: str = "host-policy"

    def validate(self) -> None:
        if not self.project_root.resolve().is_dir():
            raise ValueError("project root does not exist")
        if self.backend not in {"host-policy", "wsl2", "docker"}:
            raise ValueError(f"unsupported sandbox backend: {self.backend}")


def docker_command(project_root: Path, command: list[str], image: str = "python:3.12-slim") -> list[str]:
    root = project_root.resolve()
    return [
        "docker", "run", "--rm", "--network", "none", "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
        "-v", f"{root}:/workspace:rw", "-w", "/workspace", image, *command,
    ]
