@echo off
@chcp 65001 > nul

:: Check if already maximized, if not, restart maximized
if "%1"=="max" goto :run
start /max cmd /c "%~f0" max
exit

:run
uv run law
