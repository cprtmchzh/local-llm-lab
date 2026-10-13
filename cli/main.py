from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict

from .client import OllamaClient, OllamaError
from .config import RuntimeConfig, prompt_for
from .model_manager import ModelManager


MODES = ("chat", "coding", "security", "agent")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="llm", description="Local-only Ollama chat CLI")
    result.add_argument("prompt", nargs="*", help="one-shot prompt; omit for interactive mode")
    result.add_argument("--model", help="model alias from config/models.yaml")
    result.add_argument("--mode", choices=MODES)
    result.add_argument("--context", type=int)
    result.add_argument("--temperature", type=float)
    result.add_argument("--no-stream", action="store_true", help="do not print chunks as they arrive")
    result.add_argument("--json", action="store_true", help="emit one-shot result as JSON")
    return result


def _gpu_status() -> str:
    command = ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu", "--format=csv,noheader"]
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True, timeout=10).stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return "nvidia-smi unavailable"


def _print_stats(stats: object) -> None:
    data = asdict(stats)  # type: ignore[arg-type]
    print(
        "\n[stats] "
        + " ".join(
            [
                f"model={data['model']}",
                f"prompt={data['prompt_tokens']}",
                f"output={data['output_tokens']}",
                f"ttft={data['ttft_ms']:.0f}ms",
                f"speed={data['tokens_per_second']:.2f}tok/s",
                f"duration={data['total_ms']:.0f}ms",
            ]
        )
    )


def run_once(args: argparse.Namespace, cfg: RuntimeConfig, manager: ModelManager) -> int:
    alias = args.model or cfg.default_model
    mode = args.mode or cfg.default_mode
    model = manager.get(alias)
    client = OllamaClient(cfg.base_url, cfg.timeout_seconds)
    text_stream = None if args.no_stream or args.json else lambda value: print(value, end="", flush=True)
    try:
        result = client.chat(
            model=model.runtime_name,
            messages=[
                {"role": "system", "content": prompt_for(mode)},
                {"role": "user", "content": " ".join(args.prompt)},
            ],
            context_length=args.context or cfg.default_context,
            temperature=cfg.temperature if args.temperature is None else args.temperature,
            on_token=text_stream,
        )
    except (OllamaError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"response": result.text, "stats": asdict(result.stats)}, ensure_ascii=False))
    else:
        if args.no_stream:
            print(result.text)
        if cfg.show_stats:
            _print_stats(result.stats)
    return 0


def interactive(args: argparse.Namespace, cfg: RuntimeConfig, manager: ModelManager) -> int:
    alias = args.model or cfg.default_model
    mode = args.mode or cfg.default_mode
    context = args.context or cfg.default_context
    system = prompt_for(mode)
    history: list[dict[str, str]] = []
    last_stats = None
    client = OllamaClient(cfg.base_url, cfg.timeout_seconds)
    print("Local LLM Lab. /help for commands.")
    while True:
        try:
            value = input(f"[{alias}/{mode}/{context}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not value:
            continue
        if value in {"/exit", "/quit"}:
            return 0
        if value == "/help":
            print("/models /model <alias> /mode <mode> /system [text] /context <n> /reset /stats /gpu /exit")
            continue
        if value == "/models":
            try:
                installed = set(client.list_models())
            except OllamaError as exc:
                print(f"error: {exc}")
                continue
            for name, item in manager.models.items():
                mark = "installed" if item.runtime_name in installed else "not-pulled"
                print(f"{name}: {item.runtime_name} ({mark})")
            continue
        if value.startswith("/model "):
            candidate = value.split(maxsplit=1)[1]
            try:
                manager.get(candidate)
                alias = candidate
            except KeyError as exc:
                print(exc)
            continue
        if value == "/model":
            print(f"{alias}: {manager.get(alias).runtime_name}")
            continue
        if value.startswith("/mode "):
            candidate = value.split(maxsplit=1)[1]
            if candidate not in MODES:
                print(f"choose: {', '.join(MODES)}")
            else:
                mode, system = candidate, prompt_for(candidate)
            continue
        if value == "/mode":
            print(mode)
            continue
        if value.startswith("/system "):
            system = value.split(maxsplit=1)[1]
            continue
        if value == "/system":
            print(system)
            continue
        if value.startswith("/context "):
            try:
                candidate = int(value.split(maxsplit=1)[1])
                if candidate < 512:
                    raise ValueError
                context = candidate
            except ValueError:
                print("context must be an integer >= 512")
            continue
        if value == "/context":
            print(context)
            continue
        if value == "/reset":
            history.clear()
            print("context reset")
            continue
        if value == "/stats":
            _print_stats(last_stats) if last_stats else print("no completed generation")
            continue
        if value == "/gpu":
            print(_gpu_status())
            continue
        if value.startswith("/"):
            print("unknown command; use /help")
            continue
        model = manager.get(alias)
        messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": value}]
        try:
            result = client.chat(
                model=model.runtime_name,
                messages=messages,
                context_length=context,
                temperature=cfg.temperature,
                on_token=lambda chunk: print(chunk, end="", flush=True),
            )
        except OllamaError as exc:
            print(f"error: {exc}")
            continue
        print()
        history.extend([{"role": "user", "content": value}, {"role": "assistant", "content": result.text}])
        last_stats = result.stats
        if cfg.show_stats:
            _print_stats(last_stats)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        cfg = RuntimeConfig.load()
        manager = ModelManager()
        return run_once(args, cfg, manager) if args.prompt else interactive(args, cfg, manager)
    except (OSError, ValueError, KeyError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
