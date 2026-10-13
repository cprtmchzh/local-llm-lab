param(
  [int]$Attempts = 3,
  [switch]$SaveResponses
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
& "$PSScriptRoot\check_environment.ps1"
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$RawPath = Join-Path $Root "benchmark\results\raw\$RunId.jsonl"
$ComposeFile = Join-Path $Root "benchmark\offensive_lab\docker-compose.yml"
$env:LAB_RUN_TOKEN = [Guid]::NewGuid().ToString("N")
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker is required for the isolated offensive benchmark." }
try {
  docker compose -f $ComposeFile up -d --build
  if ($LASTEXITCODE -ne 0) { throw "Failed to start the isolated offensive lab." }
  for ($Index = 1; $Index -le $Attempts; $Index++) {
    $Arguments = @("-m", "benchmark.runner", "--run-id", $RunId, "--execution-role", "benchmark", "--output", $RawPath)
    if ($SaveResponses) { $Arguments += "--save-responses" }
    python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Benchmark attempt $Index failed to run." }

    $OffensiveArguments = @("-m", "benchmark.offensive_runner", "--run-id", $RunId, "--execution-role", "benchmark", "--output", $RawPath)
    if ($SaveResponses) { $OffensiveArguments += "--save-responses" }
    python @OffensiveArguments
    if ($LASTEXITCODE -ne 0) { throw "Offensive benchmark attempt $Index failed to run." }
  }
} finally {
  docker compose -f $ComposeFile down --remove-orphans
  Remove-Item Env:LAB_RUN_TOKEN -ErrorAction SilentlyContinue
}
python -m benchmark.scorers $RawPath
if ($LASTEXITCODE -ne 0) { throw "Scoring failed." }
Write-Host "Review bundle: $Root\review_bundle"
