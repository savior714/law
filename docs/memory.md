# Memory Management Log

## 2026-03-07 01:07:55
- Task: Create `run.bat` for TUI execution via `uv run law`.
- Status: Initialized.
- Actions:
  - Checking codebase and missing `docs/memory.md`.
  - Initializing `docs/memory.md`.

- Actions:
  - Created un.bat for TUI execution via uv run law.

## 2026-03-07 03:45:00
- Task: 별지(별표/서식) 자료 수집 기능 추가.
- Status: Completed.
- Actions:
  - src/law/models/schemas.py: Attachment 모델 추가 및 StatuteArticle, AdminRuleArticle에 attachments 필드 추가.
  - src/law/db/schema.py: DB 테이블에 attachments 컬럼(JSON) 추가.
  - src/law/db/repository.py: attachments 저장 로직 반영.
  - src/law/scrapers/base.py: 공통 _scrape_attachments 메서드 구현 (PDF 우선, HWP만 있을 경우 경고 로그).
  - src/law/scrapers/law_statute.py & law_admin_rule.py: 스크래핑 루프에 별지 수집 로직 통합.
- [2026-03-06] 별표/서식(PDF) 추출 로직 개선: 탭 셀렉터(#bylView) 및 아이콘/텍스트 기반 PDF 식별 로직 보강.

## 2026-03-07 08:52:00
- Task: Python runtime environment update.
- Status: Completed.
- Actions:
  - Updated pyproject.toml: set requires-python = '>=3.14'.
  - Created .python-version: pinned to 3.14.2.
  - Re-created .venv using Python 3.14.2 (uv venv --clear).
  - Synchronized dependencies (uv sync).

## 2026-03-07 09:35:00
- Task: 별지 추출 로직 고도화 (HWPX 추가 및 PDF 우선순위 정교화).
- Status: Completed.
- Actions:
  - src/law/models/schemas.py: Attachment 모델에 hwpx_url 필드 추가.
  - src/law/scrapers/base.py: _scrape_attachments 메서드에서 HWPX 식별 로직 추가 및 PDF->HWPX->HWP 우선순위 수집 구조로 개선.
  - PDF가 없을 경우 로그를 남기며, 가능한 모든 포맷의 URL을 수집하도록 변경.

## 2026-03-07 10:05:00
- Task: TUI 브라우저 종료 및 행정규칙 탭 전환 오류 해결.
- Status: Completed.
- Actions:
  - src/law/config.py: HEADLESS = True로 변경하여 브라우저 창 우발적 폐쇄 방지.
  - src/law/scrapers/base.py: _scrape_attachments 내 브라우저 상태 체크 및 행정규칙용 탭 선택자(#bdyBtnKO, 행정규칙본문) 추가. 탭 전환 실패 시 원본 URL로 복구하는 로직 보강.
  - src/law/app.py: 브라우저 종료 관련 에러 메시지 세분화.
  - debug_tabs.py를 통해 행정규칙 페이지의 실제 탭 구조 분석 완료.

## 2026-03-07 10:15:00
- Task: 글로벌 룰 준수 및 문서 정비.
- Status: Completed.
- Actions:
  - docs/CRITICAL_LOGIC.md: 시스템 핵심 로직(진실의 원천) 문서 생성.
  - run.bat: 글로벌 룰에 따라 @chcp 65001 > nul 추가.
  - 프로젝트 전반에 걸쳐 Senior Architect 페르소나 및 아키텍처 원칙 재검토.

## 2026-03-07 10:45:00
- Task: 행정규칙 탭 전환 로직 고도화 및 구문 오류 수정.
- Status: Completed.
- Actions:
  - src/law/scrapers/base.py: _scrape_attachments 내 AJAX 대기 및 행정규칙 전용 탭 선택자(#liBgcolorSpanBy) 보강.
  - 이전 작업 시 발생한 중복 except 블록 및 구문 오류 수정.
  - debug_tabs.py 실행을 통해 구문 무결성 검증 완료.

## 2026-03-07 10:59:00
- Task: '범죄수사규칙' 명칭을 '경찰수사규칙'으로 정정.
- Status: Completed.
- Actions:
  - src/law/config.py, src/law/scrapers/law_admin_rule.py, src/law/models/schemas.py, src/law/db/schema.py 내 명칭 수정.
  - 내부 소스 키를 'crime_investigation_rules'에서 'police_investigation_rules'로 변경.
  - README.md 및 docs/TRD.md 문서 업데이트 완료.

## 2026-03-07 11:35:00
- Task: '경찰수사규칙'의 성격 및 URL 최종 정정.
- Status: Completed.
- Actions:
  - 사용자 스크린샷 분석 결과 '경찰수사규칙'은 행정안전부령(부령)인 '법령(Statute)'임을 확인.
  - 기존의 '범죄수사규칙'(훈령/행정규칙) URL에서 정확한 '경찰수사규칙' URL(lsiSeq=279215)로 교체.
  - src/law/config.py 내 스크래퍼를 'law_statute'로, 테이블을 'statutes'로 변경하여 데이터 범주를 정확히 맞춤.
  - AdminRuleScraper에서 하드코딩된 특정 명칭 의존성 제거 및 범용화.

## 2026-03-07 13:03:00
- Task: 데이터베이스 및 데이터셋 하드리셋 배치 파일 (reset_data.bat) 생성.
- Status: Completed.
- Actions:
  - reset_data.bat: @chcp 65001 및 사용자 확인 절차를 포함한 데이터 삭제 로직 구현.
  - data 폴더 내 law.db 및 export 하위 폴더 내용 삭제 및 재구성 로직 포함.

## 2026-03-07 17:50:00
- Task: 데이터셋 내 불필요한 UI 텍스트 및 과도한 공백 문제 해결.
- Actions:
  - src/law/utils/text.py: normalize_whitespace 함수를 수정하여 줄바꿈 전 각 행의 공백을 제거함으로써 빈 줄이 제대로 축소되도록 개선.
  - src/law/scrapers/law_statute.py & law_admin_rule.py: law.go.kr의 '주소 복사' 레이어 및 별표/서식 리스트 등 불필요한 DOM 요소를 decompose하도록 노이즈 제거 로직 강화.
  - 결과적으로 '아래 을 눌러 주소를 복사하세요'와 같은 UI 문구와 불필요한 다중 공백이 데이터셋에서 제거됨.

## 2026-03-07 17:53:00
- Task: run.bat 실행 시 터미널 창 최대화 설정.
- Actions:
  - run.bat: PowerShell 명령어를 추가하여 실행 시 윈도우 창 크기를 최대 가용 크기로 조정하도록 수정.

## 2026-03-07 18:15:00
- Task: 법령 본문 내 불필요한 줄바꿈 및 파편화된 공백 문제 해결.
- Actions:
  - src/law/utils/text.py: clean_html_text 함수에 '텍스트 흐름(Flow)' 로직 추가. 항(①), 호(1.), 목(가.) 등 법령 구조 마커가 없는 파편화된 행들을 앞 행과 합치도록 개선.
  - 결과적으로 '수사준칙 제7조 에 따라'와 같이 끊어져 있던 문장들이 자연스럽게 이어지며 가독성이 극대화됨. 
