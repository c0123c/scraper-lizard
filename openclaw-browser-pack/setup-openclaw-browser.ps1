$ErrorActionPreference = "Stop"

function Ensure-Directory {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
  }
}

function Merge-Hashtable {
  param(
    [hashtable]$Target,
    [hashtable]$Source
  )

  foreach ($key in $Source.Keys) {
    $value = $Source[$key]
    if ($value -is [hashtable]) {
      if (-not $Target.ContainsKey($key) -or $Target[$key] -isnot [hashtable]) {
        $Target[$key] = @{}
      }
      Merge-Hashtable -Target $Target[$key] -Source $value
    } else {
      $Target[$key] = $value
    }
  }
}

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$extensionSource = Join-Path $packageRoot "extension"
$openclawHome = Join-Path $env:USERPROFILE ".openclaw"
$extensionTarget = Join-Path $openclawHome "browser\\chrome-extension"
$configPath = Join-Path $openclawHome "openclaw.json"

if (-not (Get-Command clawdbot -ErrorAction SilentlyContinue)) {
  Write-Host "未找到 clawdbot 命令。请先在这台电脑上安装 OpenClaw / clawdbot。" -ForegroundColor Yellow
  exit 1
}

Ensure-Directory -Path $openclawHome
Ensure-Directory -Path (Split-Path -Parent $extensionTarget)

if (Test-Path -LiteralPath $extensionTarget) {
  Remove-Item -LiteralPath $extensionTarget -Recurse -Force
}

Copy-Item -LiteralPath $extensionSource -Destination $extensionTarget -Recurse -Force

if (Test-Path -LiteralPath $configPath) {
  $configObject = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json -AsHashtable
} else {
  $configObject = @{}
}

$patch = @{
  browser = @{
    profiles = @{
      "my-chrome" = @{
        driver = "extension"
        cdpUrl = "http://127.0.0.1:18792"
        color = "#00AA00"
      }
    }
  }
}

Merge-Hashtable -Target $configObject -Source $patch

$configObject | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $configPath -Encoding UTF8

Write-Host ""
Write-Host "OpenClaw 浏览器包已配置完成。" -ForegroundColor Green
Write-Host "扩展目录: $extensionTarget"
Write-Host "配置文件: $configPath"
Write-Host ""
Write-Host "接下来还需要 1 次人工操作：" -ForegroundColor Cyan
Write-Host "1. 打开 chrome://extensions"
Write-Host "2. 开启“开发者模式”"
Write-Host "3. 点击“加载已解压的扩展程序”"
Write-Host "4. 选择: $extensionTarget"
Write-Host ""
Write-Host "然后运行同目录下的 start-openclaw-browser.cmd 即可启动本地 browser relay。"
