$ErrorActionPreference = "Stop"

function Test-Frontend {
  try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 3
    return $resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500
  } catch {
    return $false
  }
}

function Test-Gateway {
  try {
    $out = & openclaw gateway status 2>&1 | Out-String
    return @{ ok = $true; text = $out.Trim() }
  } catch {
    return @{ ok = $false; text = $_.Exception.Message }
  }
}

Write-Host ""
Write-Host "=== Batch Lizard ===" -ForegroundColor Cyan
Write-Host ""

$frontendOk = Test-Frontend
$gateway = Test-Gateway

$frontendText = if ($frontendOk) { "RUNNING" } else { "NOT DETECTED" }
$gatewayText = if ($gateway.ok) { "RESPONDED" } else { "NOT DETECTED" }

Write-Host "OpenClaw status check:" -ForegroundColor Yellow
Write-Host "- Frontend http://127.0.0.1:5173 : $frontendText"
Write-Host "- Gateway backend             : $gatewayText"
if ($gateway.text) {
  Write-Host "  $($gateway.text)"
}
Write-Host ""

$defaultInput = Join-Path $PSScriptRoot "urls.txt"
$defaultOutput = "D:\openclaw\文案内容"
$defaultFormats = "html,json,pdf"

$inputPath = Read-Host "URL file path [default: $defaultInput]"
if ([string]::IsNullOrWhiteSpace($inputPath)) { $inputPath = $defaultInput }

$outputPath = Read-Host "Output folder [default: $defaultOutput]"
if ([string]::IsNullOrWhiteSpace($outputPath)) { $outputPath = $defaultOutput }

Write-Host ""
Write-Host "Formats: html,json,docx,pdf" -ForegroundColor Green
$formats = Read-Host "Formats comma-separated [default: $defaultFormats]"
if ([string]::IsNullOrWhiteSpace($formats)) { $formats = $defaultFormats }

Write-Host ""
Write-Host "Starting scrape..." -ForegroundColor Cyan
Write-Host "Input  : $inputPath"
Write-Host "Output : $outputPath"
Write-Host "Formats: $formats"
Write-Host ""

python (Join-Path $PSScriptRoot "batch_chasedream_scraper.py") --input $inputPath --output $outputPath --formats $formats

Write-Host ""
Write-Host "Done. Press any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
