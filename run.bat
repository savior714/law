@echo off
@chcp 65001 > nul

:: Maximize terminal window reliably using PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $ws.SendKeys('{F11}'); $h=(Get-Host).UI.RawUI; $m=$h.MaxWindowSize; $s=$h.WindowSize; $s.Width=$m.Width; $s.Height=$m.Height; $h.WindowSize=$s;" 2>nul

uv run law
