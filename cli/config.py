from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def load_yaml_compatible(path: Path) -> dict[str, Any]:
    """Load the project's JSON-compatible YAML files without dependencies."""
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


@dataclass(frozen=True)
class RuntimeConfig:
    base_url: str
    timeout_seconds: float
    default_model: str
    default_mode: str
    default_context: int
    temperature: float
    save_responses: bool
    show_stats: bool

    @classmethod
    def load(cls, path: Path | None = None) -> "RuntimeConfig":
        data = load_yaml_compatible(path or ROOT / "config" / "runtime.yaml")
        endpoint = str(data["base_url"]).rstrip("/")
        parsed = urlparse(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Runtime base_url must be a local HTTP endpoint")
        return cls(
            base_url=endpoint,
            timeout_seconds=float(data.get("timeout_seconds", 180)),
            default_model=str(data["default_model"]),
            default_mode=str(data.get("default_mode", "chat")),
            default_context=int(data.get("default_context", 8192)),
            temperature=float(data.get("temperature", 0.2)),
            save_responses=bool(data.get("privacy", {}).get("save_responses", False)),
            show_stats=bool(data.get("show_stats", True)),
        )


def prompt_for(mode: str) -> str:
    allowed = {"chat": "default", "coding": "coding", "security": "security", "agent": "agent"}
    if mode not in allowed:
        raise ValueError(f"Unsupported mode: {mode}")
    return (ROOT / "config" / "prompts" / f"{allowed[mode]}.txt").read_text(encoding="utf-8").strip()
