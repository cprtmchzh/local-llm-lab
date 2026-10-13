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
for ($Index = 1; $Index -le $Attempts; $Index++) {
  $Arguments = @("-m", "benchmark.runner", "--run-id", $RunId, "--execution-role", "benchmark", "--output", $RawPath)
  if ($SaveResponses) { $Arguments += "--save-responses" }
  python @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Benchmark attempt $Index failed to run." }
}
python -m benchmark.scorers $RawPath
if ($LASTEXITCODE -ne 0) { throw "Scoring failed." }
Write-Host "Review bundle: $Root\review_bundle"
