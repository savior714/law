# Antigravity Runtime & Troubleshooting Guide

본 문서는 Antigravity 에이전트 환경에서 터미널 Hang(멈춤) 및 중단(KeyboardInterrupt) 현상을 방지하기 위한 실행 표준을 정의합니다.

## 1. 터미널 Hang 현상의 원인 분석

Antigravity의 **Auto Accept Extension** 및 자동화 엔진은 다음과 같은 조건에서 프로세스를 "정지 상태"로 오판하여 중단 신호를 보낼 수 있습니다.

1.  **Output Buffering (출력 버퍼링):** Python의 기본 출력은 버퍼링되어, 프로세스가 실행 중임에도 터미널에 텍스트가 즉시 출력되지 않을 때 에이전트는 이를 'Hang'으로 판단합니다.
2.  **Step Timeout (단계별 타임아웃):** 에이전트의 내부 정책에 따라 한 단계(Step)가 일정 시간(예: 30초) 이상 결과를 반환하지 않으면 강제 종료를 시도합니다.
3.  **CDP Mismatch & Pause:** 브라우저 연동 상태에서 UI 트리와 에이전트의 예상이 어긋날 경우 확장이 명령 전송을 일시 중단(Pause)할 수 있습니다.

## 2. 해결 방안 (Actionable Solutions)

### 2.1 실시간 출력 강제 (Stream-ing)
모든 명령어 실행 시 버퍼링을 우회하여 에이전트가 프로세스의 생존 신호(Liveliness)를 즉각 감지하게 합니다.
*   **pytest 실행 시:** 반드시 -s (stdout/stderr 캡처 안 함) 및 -v (상세 출력) 옵션을 사용합니다.
    `powershell
    uv run pytest -s -v tests/
    `
*   **일반 Python 스크립트:** 환경 변수 PYTHONUNBUFFERED=1을 설정하거나 실행 시 -u 옵션을 추가합니다.
    `powershell
    python -u scripts/my_script.py
    `

### 2.2 Antigravity 설정 최적화
에이전트 설정(Settings) 메뉴에서 다음 값을 조정하십시오.
*   **Max Execution Time / Step Timeout:** 기본 30s에서 **60s~120s**로 상향 조정 (대규모 스크래핑 및 테스트 대응).
*   **Pause on Mismatch:** 개발 단계에서는 **false**로 설정하여 UI 변화에 따른 명령 중단을 방지합니다.

### 2.3 프로세스 배경 실행 및 리다이렉션
에이전트의 실시간 모니터링 부담을 줄이기 위해 로그를 파일로 리다이렉트하거나 배경에서 실행합니다.
*   **로그 파일 추적:**
    `powershell
    uv run scripts/long_task.py > task.log 2>&1
    `

## 3. 요약 및 권장 명령 템플릿

| 상황 | 권장 명령어 형식 |
| :--- | :--- |
| **단위 테스트** | uv run pytest -s -v [경로] |
| **대량 수집** | python -u [스크립트] --verbose |
| **DB 마이그레이션** | PYTHONUNBUFFERED=1 uv run [스크립트] |

---
*최종 업데이트: 2026-03-11*