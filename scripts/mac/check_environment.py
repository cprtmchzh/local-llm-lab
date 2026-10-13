from __future__ import annotations

import json
import platform
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def command(args: list[str]) -> str | None:
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


def port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def hardware() -> tuple[str, float | None]:
    text = command(["system_profiler", "SPHardwareDataType"]) or ""
    values: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.strip().split(":", 1)
            if key in {"Chip", "Memory"}:
                values[key] = value.strip()
    memory = values.get("Memory", "")
    ram_gb = float(memory.split()[0]) if memory.endswith(" GB") else None
    return values.get("Chip", platform.processor() or platform.machine()), ram_gb


def main() -> None:
    cpu, ram_gb = hardware()
    disk = shutil.disk_usage(ROOT)
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "execution_role": "development",
        "official_benchmark_eligible": False,
        "os": platform.system(),
        "os_version": platform.mac_ver()[0],
        "cpu": cpu,
        "ram_gb": ram_gb,
        "gpu": "not measured; Windows NVIDIA target required",
        "vram_mb": None,
        "driver_version": None,
        "python_version": platform.python_version(),
        "git_version": command(["git", "--version"]),
        "ollama_version": command(["ollama", "--version"]),
        "wsl_status": "not_applicable",
        "docker_status": command(["docker", "--version"]) or "not_installed",
        "free_disk_gb": round(disk.free / 1024**3, 2),
        "ollama_port_11434_open": port_open("127.0.0.1", 11434),
        "local_only_verified": False,
        "notes": ["Mac development snapshot; never use these performance values for final model selection."],
    }
    destinations = [
        ROOT / "benchmark" / "results" / "mac-dev" / "environment_snapshot.json",
        ROOT / "review_bundle" / "environment_snapshot.json",
    ]
    for path in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
