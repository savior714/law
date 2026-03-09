@echo off
@chcp 65001 > nul

:: [1] PRE-CLEANUP (SSOT Section 8)
:: 새로운 인스턴스를 시작하기 전에 기존의 모든 LAW_TUI 인스턴스를 정리합니다.
:: 현재 창의 타이틀이 아직 LAW_TUI가 아니므로 자기 자신은 종료되지 않습니다.
taskkill /F /FI "WINDOWTITLE eq LAW_TUI*" /T > nul 2>&1

:: [2] Maximize Window logic
if not "%1" == "max" (
    start /MAX "" "%~f0" max
    exit /b
)

:: 고유 식별자 설정
title LAW_TUI

echo ======================================================
echo  [LAW TUI] Law Scraper Running (Maximized)
echo ======================================================
echo.
echo [SYSTEM] 이전 인스턴스 및 브라우저 프로세스 정리 완료.
echo [SYSTEM] 애플리케이션을 시작합니다...
echo.

:: [3] RUN APPLICATION
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