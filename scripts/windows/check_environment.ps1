param(
  [string]$OutputPath = ""
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $OutputPath) { $OutputPath = Join-Path $Root "review_bundle\environment_snapshot.json" }

function Try-Text([scriptblock]$Action) {
  try { return (& $Action | Out-String).Trim() } catch { return $null }
}

$OsInfo = Get-CimInstance Win32_OperatingSystem
$CpuInfo = Get-CimInstance Win32_Processor | Select-Object -First 1
$GpuInfo = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match "NVIDIA" } | Select-Object -First 1
$NvidiaCsv = Try-Text { nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits }
$GpuName = if ($GpuInfo) { $GpuInfo.Name } else { $null }
$VramMb = $null
$Driver = if ($GpuInfo) { $GpuInfo.DriverVersion } else { $null }
if ($NvidiaCsv) {
  $Parts = $NvidiaCsv.Split(",") | ForEach-Object { $_.Trim() }
  $GpuName = $Parts[0]
  $VramMb = [int]$Parts[1]
  $Driver = $Parts[2]
}
$PythonVersion = Try-Text { python --version }
$OllamaVersion = Try-Text { ollama --version }
$WslStatus = Try-Text { wsl --status }
$DockerStatus = Try-Text { docker version --format '{{.Server.Version}}' }
$Disk = Get-PSDrive -Name (Get-Location).Drive.Name
$PortOpen = $false
try { $PortOpen = (Test-NetConnection 127.0.0.1 -Port 11434 -WarningAction SilentlyContinue).TcpTestSucceeded } catch {}
$ListenAddresses = @()
try {
  $ListenAddresses = @(Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction Stop | Select-Object -ExpandProperty LocalAddress -Unique)
} catch {}
$LocalOnly = $ListenAddresses.Count -gt 0 -and @($ListenAddresses | Where-Object { $_ -notin @("127.0.0.1", "::1") }).Count -eq 0
$OfficialEligible = [bool]$NvidiaCsv -and [bool]$OllamaVersion -and $PortOpen -and $LocalOnly

$Snapshot = [ordered]@{
  timestamp = [DateTimeOffset]::UtcNow.ToString("o")
  execution_role = "benchmark"
  official_benchmark_eligible = $OfficialEligible
  os = "Windows"
  os_version = $OsInfo.Caption + " " + $OsInfo.Version
  cpu = $CpuInfo.Name
  ram_gb = [Math]::Round($OsInfo.TotalVisibleMemorySize / 1MB, 2)
  gpu = $GpuName
  vram_mb = $VramMb
  driver_version = $Driver
  nvidia_smi = [bool]$NvidiaCsv
  powershell_version = $PSVersionTable.PSVersion.ToString()
  python_version = $PythonVersion
  git_version = Try-Text { git --version }
  ollama_version = $OllamaVersion
  wsl_status = if ($WslStatus) { "available" } else { "unavailable" }
  docker_status = if ($DockerStatus) { "available: $DockerStatus" } else { "unavailable" }
  free_disk_gb = if ($Disk) { [Math]::Round($Disk.Free / 1GB, 2) } else { $null }
  ollama_port_11434_open = $PortOpen
  ollama_listen_addresses = $ListenAddresses
  local_only_verified = $LocalOnly
}
$Parent = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $Parent | Out-Null
$Snapshot | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 $OutputPath
$Snapshot | Format-List
Write-Host "Saved $OutputPath"
