param(
  [Parameter(Mandatory = $true)]
  [string]$RunId,
  [string]$TranscriptPath = ""
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
$RawPath = Join-Path $Root "benchmark\results\raw\$RunId.jsonl"
$ComposeFile = Join-Path $Root "benchmark\offensive_lab\docker-compose.yml"
$TranscriptStarted = $false
$LabStarted = $false

if ($TranscriptPath) {
  $TranscriptParent = Split-Path -Parent $TranscriptPath
  if ($TranscriptParent) { New-Item -ItemType Directory -Force -Path $TranscriptParent | Out-Null }
  Start-Transcript -Path $TranscriptPath -Force | Out-Null
  $TranscriptStarted = $true
}

try {
  if (-not (Test-Path -LiteralPath $RawPath)) { throw "Raw benchmark file not found: $RawPath" }
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker is required." }

  $ExistingOffensiveRows = @(
    Get-Content -LiteralPath $RawPath |
      ForEach-Object { $_ | ConvertFrom-Json } |
      Where-Object { $_.task_id -like "offensive-*" }
  ).Count
  if ($ExistingOffensiveRows -gt 0) {
    throw "Run $RunId already contains $ExistingOffensiveRows offensive rows. Refusing to append duplicates."
  }

  try {
    $env:LAB_RUN_TOKEN = [Guid]::NewGuid().ToString("N")
    docker compose -f $ComposeFile down --remove-orphans
    docker compose -f $ComposeFile up -d --build
    if ($LASTEXITCODE -ne 0) { throw "Failed to start the isolated offensive lab." }
    $LabStarted = $true

    python -m benchmark.offensive_runner --run-id $RunId --execution-role benchmark --output $RawPath
    if ($LASTEXITCODE -ne 0) { throw "Offensive benchmark resume failed." }
  } finally {
    if ($LabStarted) { docker compose -f $ComposeFile down --remove-orphans }
    Remove-Item Env:LAB_RUN_TOKEN -ErrorAction SilentlyContinue
  }

  python -m benchmark.scorers $RawPath
  if ($LASTEXITCODE -ne 0) { throw "Scoring failed." }
  python -m benchmark.evidence --review-bundle (Join-Path $Root "review_bundle")
  if ($LASTEXITCODE -ne 0) { throw "Evidence verification failed." }
  Write-Host "TASK_SUCCESS"
} finally {
  if ($TranscriptStarted) { Stop-Transcript | Out-Null }
}
