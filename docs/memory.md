# Memory Management Log

## 2026-03-07 ~ 2026-03-08 초기 (Archived Summary)
- **TUI & 인프라**: run.bat (최대화, 프로세스 정리 로직 포함), reset_data.bat 구축.
- **스크래핑 엔진**: 법제처 DOM 기반 Structural Extraction 엔진(V2)으로 전면 개편하여 수집 누락 해결. Playwright JS 주입을 통한 별표/서식 수집 속도 극단적 단축(0.1초).
- **데이터 전처리**: 법령 구조(항, 호, 목)에 따른 들여쓰기 및 텍스트 흐름 정규화. NotebookLM 최적화 포맷 적용.
- **아키텍처**: LawGoKrScraper 베이스 도입 및 Pydantic 기반 설정 모델링(Phase 1, 2).
- **품질 관리**: scripts/ 폴더 분류(check, debug 등), 유닛 테스트(pytest) 및 DB 품질 검증 체계 구축.
- **SSOT**: CRITICAL_LOGIC.md를 통해 본칙/부칙 분리 및 유니크 키 정책 등 핵심 로직 문서화 완료.

## 2026-03-08 Core Infrastructure Improvement Plan (Phase 0)
- **작업**: 전체 시스템 고도화를 위한 4단계 개선 로드맵 수립 및 문서화.
- **문서**: docs/IMPROVEMENT_PLAN.md 생성.
- **내용**: 1) 설정 관리 현대화, 2) 스크래퍼 중복 제거, 3) 테스트 자동화, 4) 운영 복원력(Resume) 강화.

## 2026-03-08 Phase 1: Config & Model Refactoring
- **작업**: Pydantic 기반 SourceConfig 모델 도입 및 설정 관리 체계 현대화.
- **변경**: SOURCES를 단순 딕셔너리에서 모델 객체 리스트로 전환하여 타입 안정성 확보.
- **개선**: Scraper Factory 로직을 Scraper Map 기반으로 단순화하여 확장성 개선.

## 2026-03-08 Phase 2: Scraper Abstraction
- **작업**: LawGoKrScraper 베이스 클래스 도입 및 중복 로직 통합 완료.
- **파일**: law_go_kr_base.py 생성, law_statute.py 및 law_admin_rule.py 리팩토링.
- **검증**: test_scrapers_v2.py를 통한 단위 기능 테스트 확인.

## 2026-03-08 Phase 3: Testing & Quality Guard
- **작업**: utils/text.py 유닛 테스트(pytest) 구축 및 normalize_whitespace 인덴트 보존 버그 수정.
- **추가**: tests/test_db_quality.py를 통해 DB 데이터 품질 자동 검증 체계 마련.
- **환경**: pytest-asyncio 추가 및 pyproject.toml 설정 완료.

## 2026-03-08 Phase 4: Resilience & Checkpoint
- **작업**: scrape_runs 테이블에 checkpoint 컬럼 도입 및 Resume 로직 구현.
- **상세**: 장애 시 마지막 성공 지점(0-based Index)부터 자동 재개 가능.
- **파일**: schema.py, repository.py, app.py, base.py, law_statute.py, law_admin_rule.py 수정.
- **현황**: 시스템 고도화 로드맵 모든 단계(Phase 1~4) 최종 완료.

## 2026-03-08 사법정보공개포털 형사 판례 스크래퍼 구현
- **목표**: portal.scourt.go.kr 에서 형사 판례만 수집하는 기능 추가.
- **핵심 발견 — WAF 차단**: 서버가 외부 직접 HTTP 요청(httpx 등)을 탐지하여 차단. 쿠키(JSESSIONID)를 획득해도 WAF 에러("사용에 불편을 드려서 죄송") 반환.
- **해결 — 브라우저 내 fetch()**: Playwright로 포털에 실제 접속한 뒤 page.evaluate()로 etch()를 호출. 세션 쿠키가 자동 포함되어 WAF 우회 성공.
- **파일 변경**:
  - src/law/config.py: scourt_criminal_precedent 소스 등록, API 상수(SCOURT_API_DELAY_SEC 등) 추가
  - src/law/scrapers/scourt_precedent.py: BaseScraper 상속 구조로 전면 재작성
  - pyproject.toml: httpx 의존성 추가 (uv add httpx)
- **SSOT 업데이트**: CRITICAL_LOGIC.md 섹션 12 신규 작성 (API 엔드포인트, 필드명, WAF 우회 패턴 상세 기록)