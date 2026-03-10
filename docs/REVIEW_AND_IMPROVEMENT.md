# 코드 리뷰 및 시스템 고도화 계획 (Review & Improvement Plan)

## 1. 최근 변경점 요약 (Recent Changes Summary)

본 프로젝트는 최근 대규모 데이터 수집 및 검색 성능 최적화를 위한 인프라 고도화 작업을 수행하였습니다.

- **DB 샤딩 (Sharding) 아키텍처 도입**: 단일 SQLite 구조에서 도메인 기반 4개 샤드(meta, statutes, precedents, decisions)로 분할하여 I/O 경합 해결 및 17만 건 이상의 판례 수집 기반 마련.
- **벡터 DB (ChromaDB) 연동**: sentence-transformers를 활용한 RAG(Retrieval-Augmented Generation) 시스템 구축. data/chroma에 법률 데이터 벡터화 완료.
- **스크래핑 엔진 안정화**: 
  - 사법정보공개포털(scourt.go.kr)의 강력한 WAF를 Playwright etch 주입 방식으로 우회 성공.
  - 법제처(law.go.kr) 판례 목록 페이징 루프(11페이지 그룹 이동 시 1페이지 회귀) 버그 수정.
- **설명형 설정 모델링**: Pydantic 기반 SourceConfig 도입으로 소스별 DB 라우팅 및 스크래퍼 맵핑 체계 현대화.

---

## 2. 코드 리뷰 결과 및 개선점 (Code Review Findings)

시니어 아키텍트 관점에서 발견된 시스템의 잠재적 위험 및 개선 과제입니다.

### 2.1 테스트 프레임워크 동기화 부재 (Critical)
- **현상**: 	ests/test_db_quality.py가 여전히 레거시 law.db 경로를 참조하고 있음.
- **영향**: 현재 진행 중인 샤딩 DB의 데이터 무결성을 자동 테스트로 검증할 수 없는 상태.

### 2.2 타입 무결성 전략 위배 (Type Safety)
- **현상**: VectorStore의 메서드와 MultiDBRepository의 일부 헬퍼 함수에서 명시적 타입 힌트가 누락되어 타입 추론에 의존함.
- **개선**: User Rule #9에 따라 ny 가능성을 원천 차단하고 명시적 인터페이스와 TypeGuard 도입 필요.

### 2.3 텍스트 처리 범위 확장
- **현상**: utils/text.py의 clean_html_text에서 한국 법령의 '항(Paragraph)' 식별 정규식이 ⑳(20번)까지만 대응함.
- **개선**: 서클 넘버 유니코드 범위를 50번까지 확장하여 초대형 법령 대응력 확보.

### 2.4 벡터 인덱스 전역 유니크 키 관리
- **현상**: ag_index.py에서 	able명을 포함하지 않고 ow_id만 사용 시 샤드 파일 간 ID 중복 가능성 잠재.
- **개선**: "{db_key}_{table}_{row_id or uid}" 형태의 복합 키 체계 도입.

---

## 3. 고도화 실행 로드맵 (Atomic Roadmap)

컨텍스트 과부하 방지를 위해 각 단계를 더 작게 쪼개어 순차적으로 실행합니다.

### [Phase 1] 테스트 인프라 샤딩 대응
- **1.1 conftest.py 리팩토링**: pytest 픽스처를 MultiDBRepository 기반으로 개편.
- **1.2 test_db_quality.py 경로 수정**: 레거시 law.db 참조를 제거하고 샤드별 경로 연동.
- **1.3 샤드 스키마 검증**: 4개 샤드 DB의 DDL 및 테이블 존재 여부 통합 테스트 케이스 추가.

### [Phase 2] 타입 시스템 및 유틸리티 정예화
- **2.1 Repository 타입 보강**: MultiDBRepository 내부 헬퍼 함수의 리턴 타입 및 매개변수 명시.
- **2.2 VectorStore 타입 보강**: ChromaDB 관련 메서드에 엄격한 타입 힌트 및 User Rule #9 적용.
- [Done] **2.3 Text Utility 확장**: `text.py`의 항(Paragraph) 인식 정규식을 유니코드 50번까지 확장 및 유닛 테스트 업데이트.

### [Phase 3] Vector DB 파이프라인 고도화
- **3.1 복합 키(Composite ID) 도입**: ag_index.py에 "{db_key}_{table}_{row_id}" 생성 로직 반영.
- **3.2 인덱싱 성능 튜닝**: 배치 사이즈 조정 및 에러 핸들링 강화로 대규모 인덱싱 안정성 확보.
- **3.3 인덱싱 정합성 검증**: SQLite 원본과 Vector DB 간의 레코드 개수 및 ID 중복 체크 스크립트 작성.

### [Phase 4] 통합 검증 및 마무리
- **4.1 전체 파이프라인 QA**: 수집 -> DB 저장 -> 벡터 인덱싱 -> 검색의 전 과정 검증.
- **4.2 메모리 동기화**: docs/memory.md 및 docs/CRITICAL_LOGIC.md 최종 업데이트.