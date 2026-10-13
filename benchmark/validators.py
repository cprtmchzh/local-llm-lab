from __future__ import annotations

import ast
import json
import re
from typing import Any


def _code_block(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def validate_clamp(text: str) -> tuple[float, str]:
    source = _code_block(text)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return 0.0, f"syntax error: {exc.msg}"
    forbidden = (ast.Import, ast.ImportFrom, ast.Attribute, ast.Lambda, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.ClassDef, ast.Global, ast.Nonlocal)
    if any(isinstance(node, forbidden) for node in ast.walk(tree)):
        return 0.0, "unsafe or out-of-scope syntax"
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "clamp"]
    if len(functions) != 1:
        return 0.0, "exactly one clamp function is required"
    for node in ast.walk(functions[0]):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in {"min", "max", "ValueError"}:
                return 0.0, "disallowed function call"
    namespace: dict[str, Any] = {}
    try:
        exec(compile(tree, "<candidate>", "exec"), {"__builtins__": {"min": min, "max": max, "ValueError": ValueError}}, namespace)
        clamp = namespace["clamp"]
        checks = [clamp(5, 0, 10) == 5, clamp(-2, 0, 10) == 0, clamp(20, 0, 10) == 10]
        try:
            clamp(0, 10, 0)
            checks.append(False)
        except ValueError:
            checks.append(True)
    except BaseException as exc:
        return 0.0, f"execution failed: {type(exc).__name__}: {exc}"
    score = 100.0 * sum(checks) / len(checks)
    return score, f"behavioral checks passed {sum(checks)}/{len(checks)}"


def validate_tool_json(text: str, expected: dict[str, Any]) -> tuple[float, str]:
    try:
        value = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        return 0.0, f"invalid JSON: {exc.msg}"
    if value == expected:
        return 100.0, "tool schema and arguments match"
    return 0.0, "tool JSON does not match the expected schema and arguments"
