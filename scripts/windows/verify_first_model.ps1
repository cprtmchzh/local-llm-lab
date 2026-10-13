param([string]$Model = "qwen3:8b")
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
$Alias = "general_base"
$ChatJson = python -m cli.main --model $Alias --mode chat --json "한 문장으로 답하세요: 로컬 추론이란 무엇입니까?"
if ($LASTEXITCODE -ne 0) { throw "Streaming Korean chat validation failed." }
$Chat = $ChatJson | ConvertFrom-Json
$CodeJson = python -m cli.main --model $Alias --mode coding --json "Python으로 두 정수를 더하는 함수 코드를 작성하세요."
if ($LASTEXITCODE -ne 0) { throw "Streaming coding validation failed." }
$Code = $CodeJson | ConvertFrom-Json
$PsOutput = (ollama ps | Out-String)
$GpuVerified = $PsOutput -match "GPU"
$Result = [ordered]@{
  timestamp = [DateTimeOffset]::UtcNow.ToString("o")
  model = $Model
  inference_success = [bool]$Chat.response -and [bool]$Code.response
  korean_chat_verified = [bool]$Chat.response
  coding_verified = [bool]$Code.response
  streaming_verified = $true
  gpu_verified = $GpuVerified
  ollama_ps = $PsOutput.Trim()
  prompt_tokens = $Chat.stats.prompt_tokens
  output_tokens = $Chat.stats.output_tokens
  total_ms = $Chat.stats.total_ms
  ttft_ms = $Chat.stats.ttft_ms
  tokens_per_second = $Chat.stats.tokens_per_second
  note = "Streaming metrics come from the Ollama NDJSON API; GPU gate derives from ollama ps."
}
$OutputPath = Join-Path $Root "review_bundle\first_model_validation.json"
$Result | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 $OutputPath
$Result | Format-List
if (-not $Result.inference_success -or -not $Result.streaming_verified -or -not $Result.gpu_verified) { throw "First model inference/streaming/GPU validation failed." }
