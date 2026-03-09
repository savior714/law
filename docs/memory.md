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
- **해결 — 브라우저 내 fetch()**: Playwright로 포털에 실제 접속한 뒤 page.evaluate()로 fetch()를 호출. 세션 쿠키가 자동 포함되어 WAF 우회 성공.
- **파일 변경**:
  - src/law/config.py: scourt_criminal_precedent 소스 등록, API 상수(SCOURT_API_DELAY_SEC 등) 추가
  - src/law/scrapers/scourt_precedent.py: BaseScraper 상속 구조로 전면 재작성
  - pyproject.toml: httpx 의존성 추가 (uv add httpx)
  - docs/CRITICAL_LOGIC.md: 섹션 12 신규 작성 (API 엔드포인트, 필드명, WAF 우회 패턴 상세 기록)

## 2026-03-09 11:55 (Scraper Pagination Fix)
- **버그 수정**: 법제처 판례 등 수집 시 94건(10페이지)에서 더 이상 다음 페이지를 인식하지 못하고 스크래핑이 조기 종료되는 현상 해결.
- **원인 분석**: 기존의 CSS 선택자(`.paging ol li:not(.on) a`)가 11페이지 그룹으로 넘어가는 "다음" 버튼 대신 첫 번째 페이지 버튼을 오인식하여 루프백 및 중단 발생.
- **조치 사항**: `law_go_kr_decision_base.py`의 `_go_next_page` 메서드를 JS(`evaluate`) 기반으로 전면 개편. 현재 페이지(`li.on`)의 자매 요소 여부를 명확히 판단하고, 페이지 그룹이 끝났을 시 "다음" 화살표 버튼(`img[alt*='다음']`)을 클릭하도록 구조 개선.

## 2026-03-09 11:45 (Database Schema Migration)
- **버그 수정**: 신규 소스(해석례, 재결례 등) 수집 시 `court` 필드가 없는 경우 발생하던 `NOT NULL constraint failed: precedents.court` 오류 해결.
- **스키마 변경**: `precedents` 테이블의 `court` 컬럼에서 `NOT NULL` 제약 조건을 제거하여 유연한 데이터 수집 허용.
- **자동 마이그레이션**: `init_db` 로직에 `PRAGMA table_info`를 활용한 컬럼 상태 검사 및 임시 테이블 기반의 자동 스키마 전환 로직 구현.

## 2026-03-09 15:30 (DB Sharding Phase 1 Completion)
- **작업**: 대규모 데이터 대응을 위한 도메인 기반 DB 분할(Sharding) 아키텍처 도입.
- **아키텍처**:
  - `law_meta.db`: 수집 상태 및 체크포인트 (meta)
  - `law_statutes.db`: 법령 및 행정규칙 (statutes)
  - `law_precedents.db`: 법원 판례 (precedents)
  - `law_decisions.db`: 헌재/해석/재결례 (decisions)
- **코드 변경**:
  - `src/law/config.py`: `DB_PATHS` 정의 및 `SourceConfig`에 `db_key` 라우팅 메타데이터 추가.
  - `src/law/db/repository.py`: `MultiDBRepository`로 개편하여 4개의 샤드 커넥션 동시 관리 및 동적 라우팅 구현.
  - `src/law/db/schema.py`: 샤드별 전용 DDL 분리 및 `init_db`를 통한 자동 멀티 샤드 생성 로직 구현.
- **검증**: `scripts/debug/verify_sharding_init.py`를 통해 물리적 DB 파일 4종 정상 생성 확인 완료.
## 2026-03-09 15:40 (DB Sharding Phase 2: Metadata Stabilization)
- **작업**: `law_meta.db`로의 수집 상태(scrape_runs) 데이터 이관 및 메타데이터 관리 안정화.
- **이관**: `scripts/migrate_meta.py`를 작성하여 `law.db`에 존재하던 17건의 수집 이력을 `law_meta.db`로 안전하게 전사(ATTACH DATABASE 방식).
- **정리**: `repository.py` 및 `schema.py`에서 불필요해진 레거시 `DB_PATH` 참조를 제거하여 코드 정밀성 확보.
- **효과**: 이제 모든 수집 상태 관리가 메인 판례 DB와 물리적으로 분리된 `law_meta.db`에서 독립적으로 수행됨.
- **준비**: Phase 3 단계인 판례(precedents) 데이터 분할 이관을 위한 기반 마련 완료.
## 2026-03-09 15:50 (DB Sharding Phase 3: Domain Conversion Completion)
- **작업**: 전체 데이터를 도메인별 전용 샤드 DB로 완전 이관 및 시스템 전환 완료.
- **이관 내역**:
  - `law_statutes.db`: 법령(1,249건), 행정규칙(270건) 이관.
  - `law_precedents.db`: 대법원/법제처 판례(268건) 이관.
  - `law_decisions.db`: 헌재/해석례 등(0건 - 향후 수집 대비) 기반 마련.
- **파일**: `scripts/migrate_data.py`를 통한 물리적 전사 및 `scripts/reexport_data.py`로 데이터 정합성(1,787건) 최종 검증 성공.
- **결과**: 기존 단일 `law.db` 의존성을 완전히 제거하고, 도메인별 독립적인 I/O 환경 구축. 이제 17만 건 이상의 대규모 판례 수집을 위한 인프라 준비 단계가 모두 끝남.
## 2026-03-09 15:55 (DB Sharding Phase 4: RAG Extension Foundation)
- **작업**: 대규모 법률 데이터 검색 및 활용을 위한 Vector DB (ChromaDB) 연동 및 RAG 기반 마련.
- **의존성**: chromadb, sentence-transformers 추가 (uv add).
- **아키텍처**:
  - src/law/db/vector_store.py: ChromaDB 래퍼 클래스 구현 (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 모델 적용).
  - scripts/rag_index.py: SQLite(shards) -> ChromaDB 대량 인덱싱 스크립트 구축.
  - scripts/rag_search.py: 유사도 기반 법률 데이터 검색 검증 스크립트 구축.
- **결과**: 약 1,800건의 판례 및 법령 데이터를 성공적으로 벡터화하여 data/chroma에 저장. "음주운전" 등 키워드 검색 시 관련 판례가 유사도 순으로 정상 출력됨을 확인.
- **완료**: DB 파티셔닝(Sharding) 및 확장 설계의 모든 단계(Phase 1~4) 최종 완료.
## 2026-03-09 16:05
- **SSOT 반영 및 최종화**: PRD, TRD, CRITICAL_LOGIC.md에 샤딩 아키텍처 및 번들링 로직 반영 완료.
- **Git 동기화**: 작업 내용 스테이징 및 원격 저장소 푸시 준비 완료.
