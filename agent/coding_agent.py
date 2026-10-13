from __future__ import annotations

import argparse
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cli.config import RuntimeConfig, prompt_for
from cli.model_manager import ModelManager

from .permissions import Decision, PermissionPolicy
from .workspace import Workspace


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List repository files",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 repository file",
            "parameters": {
                "type": "object",
                "required": ["path"],
                "properties": {"path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a complete UTF-8 repository file",
            "parameters": {
                "type": "object",
                "required": ["path", "content"],
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a safe test/build command without a shell",
            "parameters": {
                "type": "object",
                "required": ["argv"],
                "properties": {
                    "argv": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
]


def _call_ollama(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama agent request failed: {exc}") from exc
    if value.get("error"):
        raise RuntimeError(str(value["error"]))
    return value


def _execute_tool(workspace: Workspace, policy: PermissionPolicy, name: str, arguments: dict[str, Any]) -> str:
    try:
        if name == "list_files":
            return json.dumps(workspace.list_files(str(arguments.get("pattern", "**/*"))), ensure_ascii=False)
        if name == "read_file":
            return workspace.read_file(str(arguments["path"]))
        if name == "write_file":
            workspace.write_file(str(arguments["path"]), str(arguments["content"]))
            return "written"
        if name == "run_command":
            argv = [str(value) for value in arguments["argv"]]
            decision = policy.command(" ".join(argv))
            if decision.decision != Decision.ALLOW:
                return f"permission_{decision.decision.value}: {decision.reason}"
            completed = subprocess.run(argv, cwd=workspace.root, capture_output=True, text=True, timeout=300, check=False)
            return json.dumps({"exit_code": completed.returncode, "stdout": completed.stdout[-20000:], "stderr": completed.stderr[-20000:]}, ensure_ascii=False)
        return f"unknown_tool: {name}"
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        return f"tool_error: {exc}"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Repository-scoped Ollama coding agent")
    value.add_argument("task")
    value.add_argument("--model", default="agent_candidate")
    value.add_argument("--project-root", type=Path, default=Path.cwd())
    value.add_argument("--allow-write", action="store_true")
    value.add_argument("--max-steps", type=int, default=12)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    cfg = RuntimeConfig.load()
    model = ModelManager().get(args.model)
    workspace = Workspace(args.project_root, allow_write=args.allow_write)
    policy = PermissionPolicy(workspace.root)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": prompt_for("agent")},
        {"role": "user", "content": args.task},
    ]
    for _step in range(args.max_steps):
        response = _call_ollama(
            f"{cfg.base_url}/api/chat",
            {"model": model.runtime_name, "messages": messages, "tools": TOOLS, "stream": False, "options": {"num_ctx": cfg.default_context, "temperature": cfg.temperature}},
            cfg.timeout_seconds,
        )
        message = response.get("message", {})
        messages.append(message)
        calls = message.get("tool_calls", [])
        if not calls:
            print(message.get("content", ""))
            return 0
        for call in calls:
            function = call.get("function", {})
            name = str(function.get("name", ""))
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            output = _execute_tool(workspace, policy, name, arguments)
            messages.append({"role": "tool", "tool_name": name, "content": output})
    print("Agent stopped at max_steps without a final response")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
