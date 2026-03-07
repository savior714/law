@echo off
@chcp 65001 > nul

:: Maximize terminal window reliably using PowerShell (preserving title bar)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$h=(Get-Host).UI.RawUI; $m=$h.MaxWindowSize; $s=$h.WindowSize; $s.Width=$m.Width; $s.Height=$m.Height; $h.WindowSize=$s; (Get-Process -Id $auto_pid).MainWindowHandle; $ws=New-Object -ComObject WScript.Shell; $ws.AppActivate('Korean Legal Data Scraper');" 2>nul

uv run law
