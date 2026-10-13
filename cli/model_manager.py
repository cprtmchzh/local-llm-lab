from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ROOT, load_yaml_compatible


@dataclass(frozen=True)
class Model:
    alias: str
    runtime_name: str
    family: str
    parameter_class: str
    quantization: str
    roles: tuple[str, ...]
    metadata: dict[str, Any]


class ModelManager:
    def __init__(self, path: Path | None = None) -> None:
        data = load_yaml_compatible(path or ROOT / "config" / "models.yaml")
        raw_models = data.get("models", {})
        self.models: dict[str, Model] = {
            alias: Model(
                alias=alias,
                runtime_name=str(item["runtime_name"]),
                family=str(item.get("family", "unknown")),
                parameter_class=str(item.get("parameter_class", "unknown")),
                quantization=str(item.get("quantization", "unknown")),
                roles=tuple(item.get("roles", [])),
                metadata=dict(item),
            )
            for alias, item in raw_models.items()
        }

    def get(self, alias: str) -> Model:
        try:
            return self.models[alias]
        except KeyError as exc:
            choices = ", ".join(sorted(self.models))
            raise KeyError(f"Unknown model alias {alias!r}; choose one of: {choices}") from exc

    def as_manifest(self) -> list[dict[str, Any]]:
        return [{"model_id": alias, **model.metadata} for alias, model in self.models.items()]
