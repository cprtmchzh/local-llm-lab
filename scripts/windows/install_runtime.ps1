$ErrorActionPreference = "Stop"
if (Get-Command ollama -ErrorAction SilentlyContinue) {
  ollama --version
  exit 0
}
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  throw "winget is unavailable. Install Ollama manually from https://ollama.com/download/windows"
}
winget install --id Ollama.Ollama --exact --source winget
Write-Host "Ollama installed. Open a new terminal if the command is not yet on PATH."
