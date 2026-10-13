from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .permissions import Decision, PermissionPolicy


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Run a command through the repository permission policy")
    result.add_argument("--project-root", type=Path, default=Path.cwd())
    result.add_argument("--approve-ask", action="store_true", help="explicitly approve commands classified as ask")
    result.add_argument("--timeout", type=float, default=300)
    result.add_argument("command", nargs=argparse.REMAINDER, help="command after --")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not args.command:
        parser().error("a command is required after --")
    if args.command[0] == "--":
        args.command = args.command[1:]
    command = " ".join(args.command)
    root = args.project_root.resolve()
    policy = PermissionPolicy(root)
    decision = policy.command(command)
    audit = {"command": command, "decision": decision.decision.value, "reason": decision.reason, "project_root": str(root)}
    print(json.dumps(audit, ensure_ascii=False))
    if decision.decision == Decision.DENY:
        return 126
    if decision.decision == Decision.ASK and not args.approve_ask:
        return 125
    completed = subprocess.run(args.command, cwd=root, timeout=args.timeout, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
