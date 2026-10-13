from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Decision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass(frozen=True)
class PermissionResult:
    decision: Decision
    reason: str


READ_ONLY_GIT = {"status", "diff", "log", "show", "rev-parse"}
SAFE_EXECUTABLES = {"python", "python3", "pytest", "ruff", "mypy", "npm", "pnpm", "cargo", "git"}
NETWORK_TOOLS = {"curl", "wget", "ssh", "scp", "nc", "ncat", "nmap"}
DESTRUCTIVE_TOKENS = {"rm", "rmdir", "del", "erase", "format", "mkfs", "shutdown", "reboot"}


class PermissionPolicy:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def path(self, candidate: str | Path, *, write: bool = False) -> PermissionResult:
        path = Path(candidate)
        resolved = (self.project_root / path).resolve() if not path.is_absolute() else path.resolve()
        try:
            resolved.relative_to(self.project_root)
        except ValueError:
            return PermissionResult(Decision.DENY, "path is outside the project root")
        return PermissionResult(Decision.ASK if write else Decision.ALLOW, "repository-scoped path")

    def command(self, command: str) -> PermissionResult:
        try:
            parts = shlex.split(command, posix=os.name != "nt")
        except ValueError as exc:
            return PermissionResult(Decision.DENY, f"invalid shell syntax: {exc}")
        if not parts:
            return PermissionResult(Decision.DENY, "empty command")
        executable = Path(parts[0]).stem.casefold()
        lowered = {part.casefold() for part in parts}
        for part in parts[1:]:
            candidate = part.split("=", 1)[-1] if "=" in part else part
            if Path(candidate).is_absolute() or candidate.startswith(("/", "\\")) or candidate.startswith(".."):
                path_result = self.path(candidate)
                if path_result.decision == Decision.DENY:
                    return path_result
        if executable in DESTRUCTIVE_TOKENS or lowered & {"--delete", "--force", "-rf", "/s", "/q"}:
            return PermissionResult(Decision.DENY, "destructive command")
        if executable in NETWORK_TOOLS:
            return PermissionResult(Decision.ASK, "network access requires approval")
        if executable not in SAFE_EXECUTABLES:
            return PermissionResult(Decision.ASK, "executable is not in the safe allowlist")
        if executable == "git":
            subcommand = parts[1].casefold() if len(parts) > 1 else ""
            if subcommand not in READ_ONLY_GIT:
                return PermissionResult(Decision.ASK, "mutating git command requires approval")
        if executable in {"python", "python3"}:
            if "-c" in lowered:
                return PermissionResult(Decision.ASK, "inline interpreter code requires approval")
            if "-m" in lowered:
                index = [part.casefold() for part in parts].index("-m")
                module = parts[index + 1].casefold() if len(parts) > index + 1 else ""
                if module not in {"unittest", "pytest", "compileall", "ruff", "mypy"}:
                    return PermissionResult(Decision.ASK, "Python module is not in the test/build allowlist")
        if executable in {"npm", "pnpm", "cargo"} and any(item in lowered for item in {"install", "add", "publish"}):
            return PermissionResult(Decision.ASK, "dependency or registry operation requires approval")
        return PermissionResult(Decision.ALLOW, "safe repository command")
