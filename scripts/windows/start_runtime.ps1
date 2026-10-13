param([int]$TimeoutSeconds = 30)
$ErrorActionPreference = "Stop"
$env:OLLAMA_HOST = "127.0.0.1:11434"
try {
  Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
  Write-Host "Ollama already responds on localhost."
  exit 0
} catch {}
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
$Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
  Start-Sleep -Milliseconds 500
  try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
    Write-Host "Ollama is ready at http://127.0.0.1:11434"
    exit 0
  } catch {}
} while ((Get-Date) -lt $Deadline)
throw "Ollama did not become ready within $TimeoutSeconds seconds"
