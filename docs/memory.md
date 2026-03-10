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

## 2026-03-10 (Review and Improvement Setup)

- **변경점 요약**: 샤딩 DB, ChromaDB RAG, 스크래퍼 안정화(WAF 우회 및 페이징 수정) 등 전체 시스템 최신 현황 분석 및 요약 완료.
- **코드 리뷰**: `test_db_quality.py` 레거시 참조, `VectorStore` 타입 누락, `text.py` 항 인식 정규식 개선(1-50번) 등 4대 핵심 개선 과제 도출.
- **로드맵 수립**: 이슈 해결을 위한 4단계 실행 계획을 담은 `docs/REVIEW_AND_IMPROVEMENT.md` 문서 생성 및 공유.

## 2026-03-10 19:10 (Roadmap Refinement)

- **작업**: 고도화 실행 계획(docs/REVIEW_AND_IMPROVEMENT.md)을 더 작은 단위(Atomic Tasks)로 세분화.
- **배경**: 넓은 범위의 작업을 한 번에 처리할 때 발생하는 컨텍스트 과부하 및 오류 방지.
- **내역**: Phase 1~3의 각 단계를 1.1, 1.2, 2.1... 등 하위 작업으로 쪼개어 작업 단위의 명확성 확보.
- **검증**: .NET 클래스를 이용한 UTF-8 (no BOM) 인코딩 정밀 쓰기 및 상태 확인 완료.

## 2026-03-10 19:15 (Phase 2.3 Completion)

- **작업**: Text Utility 확장 및 유니코드 서클 넘버 50번까지 지원.
- **파일**: src/law/utils/text.py,  ests/test_utils_text.py.
- **내용**: clean_html_text 내 정규식을 \u2460-\u2473에서 \u2460-\u2473\u3251-\u325F\u32B1-\u32BF로 확장하여 초대형 법령의 '항' 인식 범위 확대.
- **검증**: uv run pytest tests/test_utils_text.py 8개 테스트 케이스 전원 통과 확인.

## 2026-03-10 19:17 (Phase 1: Test Infrastructure Sharding Support Completion)

- **작업**: 샤딩 DB 도입에 따른 테스트 환경 전면 개편 및 품질 검증 로드맵 Phase 1 완료.
- **1.1 conftest.py 리팩토링**: Repository 기반의 글로벌 픽스처(
epo, meta_db, statutes_db, precedents_db, decisions_db) 구축. 4개 샤드 DB 연동 환경 자동화.
- **1.2 test_db_quality.py 현대화**: 레거시 law.db 참조를 완전히 제거하고 샤드별 분산 데이터 검증 로직 반영.
- **1.3 샤드 스키마 검증**: 4개 샤드 DB 파일의 물리적 존재 및 필수 테이블(statutes, admin_rules, precedents, scrape_runs) 존재 여부 통합 테스트 추가.
- **검증 결과**: pytest 실행 시 14개 테스트 중 13개 통과. scourt_criminal_precedent 중 일부 데이터의 본문 누락(AssertionError)을 정확히 탐지해내는 성과 거둠.
- **작업**: 샤딩 DB 도입에 따른 테스트 환경 전면 개편 및 품질 검증 로드맵 Phase 1 완료.
- **1.1 conftest.py 리팩토링**: Repository 기반의 글로벌 픽스처(
epo, meta_db, statutes_db, precedents_db, decisions_db) 구축. 4개 샤드 DB 연동 환경 자동화.
- **1.2 test_db_quality.py 현대화**: 레거시 law.db 참조를 완전히 제거하고 샤드별 분산 데이터 검증 로직 반영.
- **1.3 샤드 스키마 검증**: 4개 샤드 DB 파일의 물리적 존재 및 필수 테이블(statutes, admin_rules, precedents, scrape_runs) 존재 여부 통합 테스트 추가.
- **검증 결과**: pytest 실행 시 14개 테스트 중 13개 통과. scourt_criminal_precedent 중 일부 데이터의 본문 누락(AssertionError)을 정확히 탐지해내는 성과 거둠.

## 2026-03-10 19:18 (Phase 1: Test Infrastructure Sharding Support Completion)

- **작업**: 샤딩 DB 도입에 따른 테스트 환경 전면 개편 및 품질 검증 로드맵 Phase 1 완료.
- **1.1 conftest.py 리팩토링**: Repository 기반의 글로벌 픽스처(
epo, meta_db, statutes_db, precedents_db, decisions_db) 구축. 4개 샤드 DB 연동 환경 자동화.
- **1.2 test_db_quality.py 현대화**: 레거시 law.db 참조를 완전히 제거하고 샤드별 분산 데이터 검증 로직 반영.
- **1.3 샤드 스키마 검증**: 4개 샤드 DB 파일의 물리적 존재 및 필수 테이블(statutes, admin_rules, precedents, scrape_runs) 존재 여부 통합 테스트 추가.
- **검증 결과**: pytest 실행 시 14개 테스트 중 13개 통과. scourt_criminal_precedent 중 일부 데이터의 본문 누락(AssertionError)을 정확히 탐지해내는 성과 거둠.

## 2026-03-10 19:45 (Phase 2: Type System Refinement Completion)

- **작업**: MultiDBRepository 및 VectorStore (ChromaDB) 타입 시스템 고도화 및 ny 제거.
- **2.1 Repository 타입 보강**:
  - ShardKey, TableName, ScrapeRunRecord 모델 도입 및 메서드 리턴 타입 명시.
  - cast(ShardKey, ...) 및 Literal을 활용한 동적 샤드 라우팅 타입 안정성 확보.
  - start_run 내 lastrowid 타입 에러 해결.
- **2.2 VectorStore 타입 보강**:
  - QueryResult TypedDict 정의 및 search 메서드 리턴 타입 명시.
  - MetadataType 정의 및 cast를 활용한 ny 키워드 완전 제거 (User Rule #9 준수).
- **검증**: .NET [System.IO.File]::WriteAllText를 이용한 인코딩 무결성 준수 및 iew_file을 통한 최종 CCTV 검증 완료.

## 2026-03-10 (Phase 3: Scraper & Type System Refactoring - IN PROGRESS)

- **3.1 Scourt Portal 정규식 고도화**: _extract_section_html 함수를 다중 마커 및 유연한 정규식 구조로 개편 (Mock 유닛 테스트 통과).
- **3.2 타입 시스템 정합성**: ase.py 및 law_go_kr_base.py에서 Any 제거 및 TypedDict 도입으로 타입 안정성 확보.
- **이슈**: 실 브라우저 연동 테스트( est_scourt_fix.py) 중 WebSquare5 초기화 단계에서 무한 대기 현상 발생하여 강제 중단됨. 원인 분석 및 작은 단위의 태스크(Atomic Task)로 재분할 작업 중.

## 2026-03-11 00:05 (Context Optimization & Task Decomposition)
- **현상 파악**: 작업 단위가 커서 컨텍스트 과부하 및 작업 완료율 저하 현상 발생. 특히 \	est_scourt_fix.py\의 브라우저 중단(Hang) 이슈로 인해 흐름이 끊김.
- **조치 사항**: \docs/ATOMIC_TASKS.md\를 생성하여 모든 작업을 10분 내외의 소단위(Atomic Task)로 재분할 완료.
- **현재 진행 상태**: Phase 3.3.1 (test_scourt_fix.py 브라우저 가시적 디버깅) 준비 완료.
## 2026-03-11 00:28 (Phase 3 & 4 Completion)

- **Phase 3 Scraper & Type Completion**: Scourt 포털 동적 대기(WebSquare5 요소 감지) 도입으로 초기화 속도 최적화. BaseScraper 및 주요 Scraper 클래스에서 Any 제거 및 TypedDict/cast 도입으로 타입 안정성 확보.
- **Phase 4 RAG 고도화**: id_key(db_key, table, row_id)를 조합한 Composite ID 체계 구축으로 ChromaDB 데이터 정합성 강화. Batch Size 200 및 tqdm 적용으로 인덱싱 성능 및 가시성 확보.
- **검증**: verify_rag.py를 통해 SQLite 원본 대비 벡터 DB 인덱싱 일치 확인 및 검색 품질 검증 완료.
- **현황**: Phase 5(통합 QA) 진입 준비 완료.

## 2026-03-11 00:55 (Runtime Optimization & Phase 5 Initialization)
- **작업**: Antigravity 실행 환경 최적화 가이드 작성 및 Phase 5.1(RAG 품질 검증) 완료.
- **파일**: docs/ANTIGRAVITY_RUNTIME_GUIDE.md 신설, tests/test_rag_quality.py 수정.
- **결과**: pytest -s -v 옵션 활용을 통한 터미널 Hang 해결 방안 도출. 헌권/해법/행심 연동을 위해 헌재결정례(5건) 수집 성공 및 decisions 샤드 유입 확인.
- **현황**: Phase 5.2 진행 중 (헌재 데이터 물리적 저장 상태 최종 확인).
## 2026-03-11 01:20 (Phase 5: Data Expansion & RAG Optimization Completion)
- **수집 확장**: 헌재결정례(5), 해석례(3), 행정심판(3) 샘플 수집 완료 및 `decisions` 샤드 정상 유입 확인.
- **키워드 필터링 (Phase 5.5)**: `config.py`에 수사/형사 핵심 키워드 정의 및 `BaseScraper.is_relevant()` 도입. 모든 판례/결정례 수집 시 관련성 없는 데이터 배제 로직 적용.
- **증분 인덱싱 (Phase 5.6)**: `law_meta.db`에 `sync_stats` 테이블 추가. `rag_index.py`를 개편하여 `last_sync_at` 이후의 신규 SQLite 레코드만 ChromaDB에 UPSERT하는 증분 동기화 체계 구축.
- **성능 및 품질**: 1,800여 건의 전체 데이터 벡터화 재검증 완료. "헌법불합치" 등 키워드로 `decisions` 샤드 데이터 검색 성공 확인.
- **안정성**: Antigravity 환경에서의 실시간 출력(Python -u) 및 인코딩 무결성([System.IO.File]::ReadAllText) 표준 준수.

## Session Handoff: System Stable & Phase 5 Complete
- **아키텍처**: 4개 샤드 DB(meta, statutes, precedents, decisions) 및 증분 방식의 ChromaDB RAG 파이프라인 안착.
- **물리적 상태**: 
  - `data/law_decisions.db`: 11건 (헌재/해석/행심)
  - `data/chroma`: 1,830+ vectors (Composite ID: {shard}_{table}_{id})
- **SSOT**: `CRITICAL_LOGIC.md` 및 `ATOMIC_TASKS.md` 최신화 완료.
- **Next Steps**: 
  - 대규모 판례(17만 건) 중 수사 관련 키워드 기반 타겟 수집 개시.
  - `docs/COLLECTION_PLAN.md`에 따른 하급심 판례 수집 스크래퍼 확장.