param([ValidateSet(1, 2)][int]$Stage = 1)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Config = Get-Content (Join-Path $Root "config\models.yaml") -Raw | ConvertFrom-Json
if ($Stage -eq 2) {
  $GatePath = Join-Path $Root "review_bundle\first_model_validation.json"
  if (-not (Test-Path $GatePath)) { throw "Run verify_first_model.ps1 before stage 2." }
  $Gate = Get-Content $GatePath -Raw | ConvertFrom-Json
  if (-not $Gate.inference_success -or -not $Gate.streaming_verified -or -not $Gate.gpu_verified) { throw "First-model inference/streaming/GPU gate has not passed." }
}
foreach ($Alias in $Config.pull_order) {
  $Model = $Config.models.$Alias
  if ([int]$Model.stage -eq $Stage) {
    Write-Host "Pulling $Alias ($($Model.runtime_name))"
    ollama pull $Model.runtime_name
    if ($LASTEXITCODE -ne 0) { throw "Model pull failed: $($Model.runtime_name)" }
  }
}
