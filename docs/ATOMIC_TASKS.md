# Atomic Tasks (원자적 작업 리스트)

본 문서는 컨텍스트 과부하 방지를 위해 작업을 최소 단위로 분할하여 관리합니다. 완료된 항목은 [x]로 표시합니다.

## [Phase 3] Scraper & Type System Refactoring (완료)
- [x] 3.3: test_scourt_fix.py 브라우저 중단 해결
- [x] 3.4: 타입 시스템 정합성 최종 점검

## [Phase 4] Vector DB 파이프라인 고도화 (완료)
- [x] 4.1: Composite ID 도입 (rag_index.py)
- [x] 4.2: 인덱싱 성능 및 안정성 강화
- [x] 4.3: 인덱싱 정합성 검증


## [Phase 5] 통합 QA 및 데이터 확장 (완료)

- [x] 5.1: RAG 품질 검증 자동화 (tests/test_rag_quality.py 완료)
- [x] 5.2: 헌재결정례 수집 및 decisions 샤드 유입 검증 (완료)
- [x] 5.3: 법제처 해석례 스크래퍼 구현 및 수집 (완료)
- [x] 5.4: 행정심판재결례 스크래퍼 구현 및 수집 (완료)
- [x] 5.5: 수사/형사 중심 키워드 필터링 로직 적용 (is_relevant 필터 완료)
- [x] 5.6: 증분 인덱싱 스크립트 고도화 (Incremental Sync 완료)
- [x] 5.7: 전체 샤드 통합 검색 및 결과 가중치(Reranking) QA (성공)