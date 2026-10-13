from __future__ import annotations

import platform
import subprocess
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareMetrics:
    vram_baseline_mb: float = 0.0
    vram_peak_mb: float = 0.0
    ram_peak_mb: float = 0.0
    gpu_utilization_peak: float = 0.0


def _nvidia() -> tuple[float, float] | None:
    try:
        output = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
            check=True, capture_output=True, text=True, timeout=5,
        ).stdout.splitlines()[0]
        memory, utilization = (float(value.strip()) for value in output.split(",")[:2])
        return memory, utilization
    except (FileNotFoundError, subprocess.SubprocessError, ValueError, IndexError):
        return None


def _ollama_ram_mb() -> float:
    if platform.system() != "Windows":
        return 0.0
    script = "(Get-Process ollama* -ErrorAction SilentlyContinue | Measure-Object WorkingSet64 -Sum).Sum / 1MB"
    try:
        output = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=True, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return float(output) if output else 0.0
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return 0.0


class HardwareSampler:
    def __init__(self, interval_seconds: float = 0.25) -> None:
        self.interval_seconds = interval_seconds
        first = _nvidia()
        self.baseline = first[0] if first else 0.0
        self.vram_peak = self.baseline
        self.gpu_peak = first[1] if first else 0.0
        self.ram_peak = _ollama_ram_mb()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            gpu = _nvidia()
            if gpu:
                self.vram_peak = max(self.vram_peak, gpu[0])
                self.gpu_peak = max(self.gpu_peak, gpu[1])
            self.ram_peak = max(self.ram_peak, _ollama_ram_mb())

    def __enter__(self) -> "HardwareSampler":
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        gpu = _nvidia()
        if gpu:
            self.vram_peak = max(self.vram_peak, gpu[0])
            self.gpu_peak = max(self.gpu_peak, gpu[1])
        self.ram_peak = max(self.ram_peak, _ollama_ram_mb())

    def result(self) -> HardwareMetrics:
        return HardwareMetrics(self.baseline, self.vram_peak, self.ram_peak, self.gpu_peak)
