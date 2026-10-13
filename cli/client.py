from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class GenerationStats:
    model: str
    prompt_tokens: int
    output_tokens: int
    ttft_ms: float
    generation_ms: float
    prompt_eval_ms: float
    tokens_per_second: float
    total_ms: float
    load_ms: float


@dataclass(frozen=True)
class ChatResult:
    text: str
    stats: GenerationStats


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout_seconds: float = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _json_request(self, path: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}", body, {"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

    def list_models(self) -> list[str]:
        return [item["name"] for item in self.list_model_details()]

    def list_model_details(self) -> list[dict]:
        return list(self._json_request("/api/tags").get("models", []))

    def process_status(self) -> list[dict]:
        return list(self._json_request("/api/ps").get("models", []))

    def chat(
        self,
        *,
        model: str,
        messages: Iterable[dict[str, str]],
        context_length: int,
        temperature: float,
        on_token: Callable[[str], None] | None = None,
    ) -> ChatResult:
        payload = {
            "model": model,
            "messages": list(messages),
            "stream": True,
            "options": {"num_ctx": context_length, "temperature": temperature},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        first_token_at: float | None = None
        chunks: list[str] = []
        final: dict = {}
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                for raw_line in response:
                    if not raw_line.strip():
                        continue
                    event = json.loads(raw_line)
                    if error := event.get("error"):
                        raise OllamaError(str(error))
                    content = event.get("message", {}).get("content", "")
                    if content:
                        if first_token_at is None:
                            first_token_at = time.perf_counter()
                        chunks.append(content)
                        if on_token:
                            on_token(content)
                    if event.get("done"):
                        final = event
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama streaming request failed: {exc}") from exc

        ended = time.perf_counter()
        output_tokens = int(final.get("eval_count", 0))
        eval_ns = int(final.get("eval_duration", 0))
        measured_generation_ms = eval_ns / 1_000_000 if eval_ns else (ended - (first_token_at or started)) * 1000
        tokens_per_second = output_tokens / (eval_ns / 1_000_000_000) if output_tokens and eval_ns else 0.0
        stats = GenerationStats(
            model=model,
            prompt_tokens=int(final.get("prompt_eval_count", 0)),
            output_tokens=output_tokens,
            ttft_ms=((first_token_at or ended) - started) * 1000,
            generation_ms=measured_generation_ms,
            prompt_eval_ms=int(final.get("prompt_eval_duration", 0)) / 1_000_000,
            tokens_per_second=tokens_per_second,
            total_ms=int(final.get("total_duration", 0)) / 1_000_000 or (ended - started) * 1000,
            load_ms=int(final.get("load_duration", 0)) / 1_000_000,
        )
        return ChatResult("".join(chunks), stats)
