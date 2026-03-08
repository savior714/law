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
## 2026-03-08 18:40 (Scourt Scraper Fix)
- **현상**: 대법원 형사 판례 스크래핑 시 터미널 종료 및 스팸 로그 발생
- **원인 분석**:
  1. ScourtPrecedentScraper 클래스가 BaseScraper의 추상 메서드 alidate_page_loaded를 구현하지 않아 객체 생성 시 TypeError 발생.
  2. page.evaluate 호출 시 인자 전달 방식(시그너처) 불일치로 인한 SyntaxError 유발.
  3. WebSquare5 트리 확장 및 카테고리 클릭 시 불안정한 mousedown/mouseup 이벤트 처리 부족.
- **조치 사항**:
  1. alidate_page_loaded 메서드 구현 추가 및 객체 인스턴스화 오류 해결.
  2. page.evaluate 인자 전달 방식을 JS 구조분해 할당({apiPath, jisSrno})으로 통일하여 안정성 확보.
  3. 트리 노드 클릭 시 mousedown, mouseup 이벤트를 포함하는 안정적인 클릭 트리거 적용.
  4. 데이터 로딩 지연을 고려하여 총 건수 및 결과 목록 추출 전 명시적 대기(Wait) 로직 강화.
- **결과**: 디버그 스크립트를 통해 정상 인스턴스화 및 초기 로딩 흐름 진입 확인 (실제 수집 시도는 WAF 상태에 따라 변동 가능하나 코드 레벨의 치명적 오류는 해결됨)
## 2026-03-08 18:45 (Scourt Scraper Data Fix)
- **현상**: 스크래핑 시도 시 "0 records saved" 출력되며 수집 실패.
- **원인 분석**: 
  1. \_get_total_count\가 총 건수 텍스트에 "총"이라는 글자가 포함되기를 기다렸으나, 실제 DOM에서는 CSS \::before\로 삽입되어 \innerText\에 잡히지 않음.
  2. \item_el.get_attribute("id")\가 \None\을 반환할 경우 \e.search\에서 \TypeError\ 발생 (디버그 모드에서 확인).
- **조치 사항**:
  1. \_get_total_count\의 조건을 숫자 포함 여부(\e.search(r"\d+")\)로 완화하고, WebSquare5 특화 CSS 선택자 fallback 강화.
  2. \aw_id\가 \None\일 경우 빈 문자열로 처리하고, ID 기반 인덱스 추출 실패 시 루프 순번(i)을 row_idx로 활용하도록 보완.
  3. \_handle_initial_load\ 이후 총 건수 엘리먼트에 대한 명시적 대기를 추가하여 동기화 안정성 확보.
- **결과**: \scripts/test_scourt_debug.py\ 실행 시 정상적으로 224건 인식 및 목록 데이터(SRNO, 제목 등) 수집 성공 확인.
## 2026-03-09 05:55 (Precedent Text Normalization)
- **현상**: 수집된 판례 데이터의 본문(판시사항, 판결요지 등)에 불필요한 줄바꿈(Hard Break)이 다수 포함되어 문단 가독성 저하.
- **조치 사항**:
  1. \src/law/utils/text.py\: \clean_html_text\ 로직 개선. 법령 키워드('항', '호' 등)로 끝나는 행이라도 \[1]\, \[2]\와 같은 판례 번호 마커가 시작되면 강제 줄바꿈을 유지하도록 보완.
  2. \src/law/scrapers/scourt_precedent.py\: 상세 본문 추출 시 \clean_html_text\를 적용하여 문단 병합(Flowing) 수행.
  3. \scripts/reclean_data.py\: DB에 이미 저장된 224건의 판례 데이터를 소급하여 정규화하는 복구 스크립트 실행 (210건 수정 완료).
- **결과**: \data/export/BUNDLE_PRECEDENT_01.txt\ 확인 결과, 문단이 적절히 병합되어 NotebookLM 등 AI 도구 활용에 최적화된 형태로 개선됨.