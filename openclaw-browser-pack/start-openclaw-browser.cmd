@echo off
echo Starting OpenClaw browser relay...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$cfg = Get-Content -Raw $env:USERPROFILE\.openclaw\openclaw.json | ConvertFrom-Json; Write-Host ''; Write-Host 'Port: 18792'; Write-Host ('Gateway token: ' + $cfg.gateway.auth.token); Write-Host ''"
start "OpenClaw Browser Relay" powershell -NoExit -Command "clawdbot browser extension install"
pause
