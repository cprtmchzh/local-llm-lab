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
$PreviousDockerConfig = [Environment]::GetEnvironmentVariable("DOCKER_CONFIG", "Process")
$PreviousDockerHost = [Environment]::GetEnvironmentVariable("DOCKER_HOST", "Process")
$DockerHost = (docker context inspect --format '{{.Endpoints.docker.Host}}' 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $DockerHost) { throw "Failed to resolve the active Docker endpoint." }
$TempDockerConfig = Join-Path ([IO.Path]::GetTempPath()) ("local-llm-lab-docker-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $TempDockerConfig | Out-Null
"{}" | Set-Content -Encoding ascii (Join-Path $TempDockerConfig "config.json")
$env:DOCKER_CONFIG = $TempDockerConfig
$env:DOCKER_HOST = $DockerHost
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
  if ($null -eq $PreviousDockerConfig) { Remove-Item Env:DOCKER_CONFIG -ErrorAction SilentlyContinue }
  else { $env:DOCKER_CONFIG = $PreviousDockerConfig }
  if ($null -eq $PreviousDockerHost) { Remove-Item Env:DOCKER_HOST -ErrorAction SilentlyContinue }
  else { $env:DOCKER_HOST = $PreviousDockerHost }
  Remove-Item -Recurse -Force $TempDockerConfig -ErrorAction SilentlyContinue
}
python -m benchmark.scorers $RawPath
if ($LASTEXITCODE -ne 0) { throw "Scoring failed." }
Write-Host "Review bundle: $Root\review_bundle"
