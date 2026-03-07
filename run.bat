@echo off
@chcp 65001 > nul

:: Maximize terminal window using PowerShell
powershell -NoProfile -Command "& { . ($profile | Split-Path)\Microsoft.PowerShell_profile.ps1; $w = Get-Host; $w.UI.RawUI.BufferSize = New-Object System.Management.Automation.Host.Size(200,3000); $w.UI.RawUI.WindowSize = New-Object System.Management.Automation.Host.Size(200,60); (Get-Process -Id $PID).MainWindowHandle; } > $null"
:: Alternative method for standard CMD/Powershell window
powershell -NoProfile -Command "(Get-Host).UI.RawUI.WindowSize = New-Object System.Management.Automation.Host.Size((Get-Host).UI.RawUI.MaxWindowSize.Width, (Get-Host).UI.RawUI.MaxWindowSize.Height)" 2>nul

uv run law
