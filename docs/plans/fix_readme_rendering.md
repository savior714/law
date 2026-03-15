# 🗺️ Project Blueprint: README.md 렌더링 복구 및 정문화

> 생성 일시: 2026-03-15 13:00 | 상태: **작업 완료**

## 🎯 Architectural Goal

- GitHub 등 웹 환경에서 `README.md` 파일이 정상적으로 렌더링되지 않고 텍스트가 뭉쳐서 출력되는 현상을 해결.
- **SSOT**: `AI_GUIDELINES.md`에서 정의한 인코딩 표준(**UTF-8 no BOM**) 준수.

## 🛠️ Step-by-Step Execution Plan

### 📦 Task List

- [x] **Task 1: 파일 메타데이터 및 인코딩 정밀 진단**
  - **Tool**: `run_command` (PowerShell)
  - **Goal**: 파일의 실제 인코딩 상태와 숨겨진 특수 문자(Null byte, BOM 등) 존재 여부 확인.
  - **Command**: `Get-Content -Path "c:\develop\law\README.md" -Encoding Byte -TotalCount 10`

- [x] **Task 2: 인코딩 변환 및 라인 엔딩 정규화**
  - **Tool**: `run_command` (PowerShell)
  - **Goal**: 파일을 **UTF-8 no BOM**으로 다시 저장하고, 모든 라인 엔딩을 `LF` 또는 `CRLF`로 통일.
  - **Pseudocode**: `[System.IO.File]::WriteAllLines($Path, $Content, (New-Object System.Text.UTF8Encoding($false)))`

- [x] **Task 3: 마크다운 구조 검증 및 미세 조정**
  - **Tool**: `replace_file_content`
  - **Goal**: 헤더와 본문 사이의 공백 라인이 확실히 존재하는지 확인하고, GitHub 특화 문법 충돌 여부 점검.
  - **Dependency**: Task 2

## ⚠️ 기술적 제약 및 규칙 (SSOT)

- **Encoding**: 반드시 **UTF-8 no BOM**을 유지해야 함. (PowerShell 기본값인 BOM 포함 주의)
- **Line Endings**: Windows 환경이므로 `CRLF`를 기본으로 하되, 일관성을 유지함.
- **Safety**: 원본 내용 훼손 방지를 위해 작업 전 메모리에 백업 후 수행.

## ✅ Definition of Done

1. [ ] `README.md` 파일이 로컬 편집기 및 웹 렌더러에서 정상적으로 보임.
2. [ ] 파일 인코딩이 `UTF-8 (no BOM)`으로 확인됨.
3. [ ] 모든 마크다운 헤더가 단락으로 올바르게 분리됨.
