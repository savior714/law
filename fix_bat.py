import os

content = """@chcp 65001 > nul
@echo off
setlocal

echo ======================================================
echo [SYSTEM] 법률 스크래퍼 데이터 하드리셋 (Hard Reset)
echo ======================================================
echo.

echo ! 주의 !: 이 작업은 모든 데이터베이스 및 첨부파일을 삭제합니다.
echo.

set /p confirm="정말로 모든 데이터를 삭제하시겠습니까? (Y/N): "
if /i not "%confirm%"=="Y" goto :CANCEL

echo.
echo [1/2] 기존 데이터 삭제 중... (data 폴더)
if exist "data" (
    rd /s /q "data"
)
timeout /t 1 > nul
mkdir "data"
mkdir "data\\export"
echo [SUCCESS] 데이터 폴더가 물리적으로 초기화되었습니다.

echo.
echo [2/2] 필수 디렉토리 재구성 완료.
echo.

echo ======================================================
echo [COMPLETED] 하드리셋이 성공적으로 완료되었습니다.
echo ======================================================
goto :END

:CANCEL
echo.
echo [CANCEL] 작업을 취소하였습니다.

:END
pause
endlocal
"""

with open('reset_data.bat', 'w', encoding='utf-8', newline='') as f:
    f.write(content.replace('\n', '\r\n'))

print("Created reset_data.bat with UTF-8 no BOM and CRLF.")
