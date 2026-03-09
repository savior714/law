# 데이터 수집 확장 계획 (Phase 5: Diversification)

본 문서는 `law.go.kr` 플랫폼 내의 다양한 법적 판단 및 해석 자료를 추가 수집하기 위한 기술적 로드맵을 정의합니다.

## 1. 신규 수집 대상 (Target Sources)

사용자 요청에 따라 다음 4가지 핵심 도메인을 추가 수집 대상으로 선정합니다.

| 도메인 | 검색 엔드포인트 | 상세 뷰 유형 | 성격 |
| :--- | :--- | :--- | :--- |
| **판례 (Precedent)** | `precSc.do` | `precInfoP.do` | 법원의 구체적 사건 판단 |
| **헌재결정례 (Constitutional)** | `detcSc.do` | `detcInfoP.do` | 헌법재판소 결정 및 법리 해석 |
| **법제처 해석례 (Interpretation)** | `expcSc.do` | `expcInfoP.do` | 법질서 통일성을 위한 유권해석 |
| **행정심판재결례 (Admin Appeal)** | `allDeccSc.do` | `detcInfoP.do` 외 | 행정기관의 권리구제 판단 |

## 2. 기술적 구현 전략

### 2.1. `LawGoKrScraper` 베이스 확장
- 모든 신규 소스는 `law.go.kr` 기반이므로, 기존 `LawGoKrScraper` (src/law/scrapers/law_go_kr_base.py)의 `safe_navigate` 및 세션 관리 로직을 100% 재사용한다.
- **도메인별 특화 파싱 로직**:
  - 판례/헌재결정례는 `【판시사항】`, `【결정요지】` 등 대괄호 마커를 기준으로 문단을 분할하는 `CleanHtmlText` 로직을 공통 적용한다.
  - 행정심판 및 해석례는 법령 조문 형식이 아닌 일반 텍스트 문단 형식이므로, `Hierarchy` (편/장/절) 대신 `카테고리/주제` 기반의 헤더 규격화를 적용한다.

### 2.2. 데이터 스토리지 통합 (`precedents` 테이블)
- `precedents` 테이블을 범용 '법적 판단(Legal Decisions)' 저장소로 활용한다.
- `source_key`를 통해 각 소스(헌재, 행정심판 등)를 구분하여, NotebookLM 수출 시 필터링이 가능하도록 설계한다.

## 3. 단계별 실행 계획

### Phase 5.1: 소스 설정 및 스키마 검토
- `src/law/config.py`에 신규 `SourceConfig` 4종 등록.
- `src/law/models/schemas.py`의 `Precedent` 모델이 해석례/재결례의 필드(예: 질의요지, 회신내용)를 수용할 수 있는지 검토 후 필요 시 `Decision` 공통 모델로 추상화.

### Phase 5.2: 헌재 및 해석례 스크래퍼 익스텐션
- `LawGoKrScraper`를 상속받는 `ConstitutionalScraper`, `InterpretationScraper` 구현.
- `law.go.kr` 특유의 AJAX 로딩 및 탭 전환 대응 (기존 `CRITICAL_LOGIC.md` 섹션 2 참조).

### Phase 5.3: 대규모 수집 및 품질 검증
- `scripts/reexport_data.py`를 업데이트하여 신규 데이터가 포함된 통합 법률 지식 번들 생성.
- NotebookLM에서 위계(법령 > 판례 > 해석례)에 따른 답변 정확도 테스트.

## 4. 향후 고려사항
- **형사/행정 필터링**: 수사경찰 사용 목적에 맞춰, 전체 수집보다는 '형사', '수사' 키워드와 관련된 필터를 강화하여 데이터 밀도를 높인다.