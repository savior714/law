# Memory Management Log

## 2026-03-07 ~ 2026-03-08 초기 (Archived Summary)
- **TUI & 인프라**: un.bat (최대화, 프로세스 정리 로직 포함), eset_data.bat 구축.
- **스크래핑 엔진**: 법제처 DOM 기반 Structural Extraction 엔진(V2)으로 전면 개편하여 수집 누락 해결. Playwright JS 주입을 통한 별표/서식 수집 속도 극단적 단축(0.1초).
- **데이터 전처리**: 법령 구조(항, 호, 목)에 따른 들여쓰기 및 텍스트 흐름 정규화. NotebookLM 최적화 포맷 적용.
- **아키텍처**: LawGoKrScraper 베이스 도입 및 Pydantic 기반 설정 모델링(Phase 1, 2).
- **품질 관리**: scripts/ 폴더 분류(check, debug 등), 유닛 테스트(pytest) 및 DB 품질 검증 체계 구축.
- **SSOT**: CRITICAL_LOGIC.md를 통해 본칙/부칙 분리 및 유니크 키 정책 등 핵심 로직 문서화 완료.

## 2026-03-08 Core Infrastructure Improvement Plan (Phase 0)
- **작업**: 전체 시스템 고도화를 위한 4단계 개선 로드맵 수립 및 문서화.
- **문서**: docs/IMPROVEMENT_PLAN.md 생성.
- **내용**: 1) 설정 관리 현대화, 2) 스크래퍼 중복 제거, 3) 테스트 자동화, 4) 운영 복원력(Resume) 강화.
- **상태**: 1단계(Config & Model Refactoring) 착수 대기 중.

## 2026-03-08 Phase 1: Config & Model Refactoring
- **작업**: Pydantic 기반 SourceConfig 모델 도입 및 설정 관리 체계 현대화.
- **변경**: SOURCES를 단순 딕셔너리에서 모델 객체 리스트로 전환하여 타입 안정성 확보.
- **개선**: Scraper Factory 로직을 Scraper Map 기반으로 단순화하여 확장성 개선.
- **현황**: Phase 1 완료. Phase 2(Scraper Abstraction) 착수 준비.

## 2026-03-08 11:45:00
- **작업**: Phase 2 (Scraper Abstraction) 완료.
- **상세**: LawGoKrScraper 베이스 클래스를 도입하여 StatuteScraper와 AdminRuleScraper의 중복 로직(JS 추출, 계층 파싱, 로딩 대기 루틴)을 통합.
- **파일**: law_go_kr_base.py 생성, law_statute.py 및 law_admin_rule.py 리팩토링.
- **검증**: test_scrapers_v2.py를 통한 단위 기능 테스트 확인.
- **인코딩**: 모든 파일 .NET 클래스 기반 UTF-8(no BOM) 적용 확인.

## 2026-03-08 12:10:00
- **작업**: Phase 3 (Testing & Quality Guard) 완료.
- **상세**: utils/text.py에 대한 유닛 테스트(pytest) 구축 및 normalize_whitespace 인덴트 보존 버그 수정. tests/test_db_quality.py를 통해 DB 데이터 품질 자동 검증 체계 마련.
- **환경**: pytest-asyncio 추가 및 pyproject.toml 설정 완료.
- **현황**: Phase 1, 2, 3 완료. 차후 Phase 4(Resilience) 진행 예정.

## 2026-03-08 11:55:00
- **Task**: PowerShell C:\Users\savio\OneDrive\문서\WindowsPowerShell\Microsoft.PowerShell_profile.ps1 보안 강화 및 docs/memory.md 최적화 정리.
- **Actions**:
  - C:\Users\savio\OneDrive\문서\WindowsPowerShell\Microsoft.PowerShell_profile.ps1: Add-Content, Set-Content, Out-File을 차단하는 보안 함수 추가.
  - docs/memory.md: 200줄 초과에 따른 압축 요약 수행 (317줄 -> 50줄 이내).
  - CLAUDE.md: 요약 압축 규칙을 강제화하도록 문구 강화.
- **CCTV**: [System.IO.File]::ReadAllText를 통해 인코딩 및 내용 수정 상태 검증 완료.
- **Status**: 완료.
## 2026-03-08 11:55:00
- **작업**: Phase 4 (Resilience & Checkpoint) 완료.
- **상세**: scrape_runs 테이블에 checkpoint 컬럼 도입 및 pp.py, StatuteScraper, AdminRuleScraper에 Resume(이어서 수집) 로직 구현. 장애 시 마지막 성공 지점(Index)부터 자동 재개 가능.
- **파일**: schema.py, repository.py, app.py, base.py, law_statute.py, law_admin_rule.py 수정.
- **현황**: 시스템 고도화 로드맵 모든 단계(Phase 1~4) 최종 완료.