@echo off
@chcp 65001 > nul

:: [Maximize Window Logic]
if not "%1" == "max" (
    start /MAX "" "%~f0" max
    exit /b
)

title LAW_TUI

echo ======================================================
echo  [LAW TUI] Law Scraper Running (Maximized)
echo ======================================================
echo.

uv run law

if %ERRORLEVEL% neq 0 (
    echo.
    echo [Error] App Exit Code: %ERRORLEVEL%
    pause
) else (
    echo.
    echo [Success] Done.
    timeout /t 3
)