from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .permissions import Decision, PermissionPolicy


class Workspace:
    def __init__(self, root: Path, *, allow_write: bool = False) -> None:
        self.root = root.resolve()
        self.policy = PermissionPolicy(self.root)
        self.allow_write = allow_write

    def resolve(self, relative: str) -> Path:
        decision = self.policy.path(relative)
        if decision.decision == Decision.DENY:
            raise PermissionError(decision.reason)
        return (self.root / relative).resolve()

    def list_files(self, pattern: str = "**/*", limit: int = 500) -> list[str]:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise PermissionError("glob pattern must stay inside the project root")
        files = []
        for path in self.root.glob(pattern):
            if path.is_file() and ".git" not in path.parts:
                files.append(path.relative_to(self.root).as_posix())
                if len(files) >= limit:
                    break
        return sorted(files)

    def read_file(self, relative: str, max_bytes: int = 200_000) -> str:
        path = self.resolve(relative)
        data = path.read_bytes()
        if len(data) > max_bytes:
            raise ValueError(f"file exceeds {max_bytes} byte read limit")
        return data.decode("utf-8")

    def write_file(self, relative: str, content: str) -> None:
        if not self.allow_write:
            raise PermissionError("workspace writes require --allow-write")
        path = self.resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            os.replace(temporary, path)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
