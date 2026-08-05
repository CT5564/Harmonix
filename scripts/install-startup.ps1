# Registers Harmonix to start at Windows logon via Task Scheduler.
# Run: powershell -ExecutionPolicy Bypass -File scripts\install-startup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Main = Join-Path $Root "harmonix\main.py"

if (-not (Test-Path $Py)) {
    Write-Host "venv not found. Run scripts\setup.bat first." -ForegroundColor Red
    exit 1
}

$Action = New-ScheduledTaskAction `
    -Execute $Py `
    -Argument "-m harmonix.main" `
    -WorkingDirectory $Root

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

Register-ScheduledTask `
    -TaskName "Harmonix" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Harmonix 2.0 - always-on personal AI assistant" `
    -Force

Write-Host "Harmonix registered to start at logon." -ForegroundColor Green
