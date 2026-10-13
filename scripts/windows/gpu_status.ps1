$ErrorActionPreference = "Stop"
nvidia-smi --query-gpu=timestamp,name,driver_version,memory.total,memory.used,utilization.gpu --format=csv
ollama ps
