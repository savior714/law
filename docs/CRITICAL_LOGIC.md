# CRITICAL LOGIC (진실의 원천)

본 문서는 시스템의 가장 핵심적인 비즈니스 로직과 아일랜드(Island) 규칙을 정의합니다. 모든 코드 수정은 본 문서의 원칙을 준수해야 합니다.

## 1. 별지(별표/서식) 데이터 추출 및 우선순위

* **우선순위 원칙:** 동일한 서식에 대해 여러 포맷이 존재할 경우 **PDF > HWPX > HWP** 순으로 우선 수집한다.
* **수집 정책:**
  * PDF가 존재할 경우 `has_pdf_priority=True`로 마킹한다.
  * PDF가 없을 경우에도 HWPX/HWP URL을 모두 수집하되, 로그를 통해 누락 사실을 알린다.
  * 추출된 데이터는 `Attachment` 모델을 통해 정형화되며, 각 조문(Article)의 첫 번째 레코드에 바인딩된다.

## 2. law.go.kr 동적 페이지 및 탭 핸들링

* **탭 전환 메커니즘:** [별표/서식] 탭 클릭 후 데이터를 수집하고, 반드시 [본문] 탭으로 복귀해야 한다.
* **복귀 선택자 (Critical):**
  * 일반 법령: `#tabSms_1`, `#lsBdyView`
  * 행정규칙: `#bdyBtnKO`, `text='행정규칙본문'`
* **안정성 보장:** 탭 전환 실패 시 원본 URL로 `safe_navigate`를 수행하여 세션을 복구한다. 브라우저가 예기치 않게 종료된 경우(`is_closed`) 즉시 루프를 중단하고 에러를 보고한다.
* **직접 접근 원칙 (Stability):** 속도와 안정성을 위해 검색 결과 페이지를 통한 우회 대신, `lsiSeq` 또는 `lsId`가 포함된 **직접 조문 URL (`lsInfoP.do`)**을 SSOT로 관리한다.

## 3. 데이터 클리닝 및 노이즈 제거 (Noise Removal)

* **UI 요소 제거:** 법령 본문 추출 시, `law.go.kr`의 레이어 팝업이나 툴바 등 불필요한 DOM 요소를 명시적으로 제거해야 한다.
  * **대상:** `#lsByl` (별표/서식 리스트), `.p_layer_copy` (주소 복사), `.ls_sms_list`, `.pconfile`, `.note_list` 등.
* **공백 정규화:** `normalize_whitespace` 함수는 줄바꿈 전 각 행의 앞뒤 공백을 `strip` 처리하여, 스페이스만 포함된 빈 줄이 정확히 감지되고 축소되도록 보장해야 한다.
* **텍스트 흐름(Flow) 및 계층 보존 처리:**
  * `clean_html_text`는 인라인 태그로 인해 파편화된 행들을 하나의 문장으로 합치되, 법령 구조를 나타내는 마커가 있는 경우 줄을 바꾼다.
  * **판례 특화 Flowing:** 판례 본문 추출 시 `[1]`, `[2]` 등 번호 마커가 나타나면 이전 행이 연결어('항', '호' 등)로 끝나더라도 강제 줄바꿈을 유지하여 판결 요지의 구조를 보존한다.
  * **RAG 최적화 들여쓰기:** 구조적 가독성을 위해 다음의 들여쓰기를 삽입한다.
    * **조문 제목:** 들여쓰기 없음
    * **항(①, ②):** 0칸 (좌측 정렬)
    * **호(1., 2.):** **2칸 공백** 들여쓰기
    * **목(가., 나.):** **4칸 공백** 들여쓰기
  * **정보 누락 방지:** 조문 제목과 본문 사이에 줄바꿈(`\n`)을 강제하여 계층 분리를 명확히 한다.

## 4. 데이터 무결성 및 SSOT

* **증분 수집:** `content` 필드의 SHA-256 해시값(`content_hash`)을 생성하여 중복을 방지한다.
* **저장 원칙 (Surgical Update):** `source_key`, `article_number`, **`article_title`**의 조합을 유니크 키로 사용하여 `UPSERT` 처리한다. 이는 본칙과 부칙의 동일 번호 조문이 충돌하지 않도록 보장한다.
* **NotebookLM 최적화:** 출력물은 파일당 약 4MB(`BUNDLE_MAX_BYTES`) 단위로 분할하며, `MASTER_ATLAS.md`를 통해 전체 인덱스를 제공한다.

## 5. 아키텍처 패턴 (3-Layer)

* **Definition:** `src/law/models/schemas.py` (Pydantic 모델)
* **Repository:** `src/law/db/repository.py` (SQLite 비동기 CRUD)
* **Service/Logic:** `src/law/scrapers/` (사이트별 추출 로직)

## 6. 본칙(Main) 및 부칙(Addenda) 분리 로직

* **충돌 방지 메커니즘:** 법령 및 행정규칙 수집 시, 본문 텍스트에서 **"부칙"** 키워드를 기준으로 섹션을 물리적으로 분할한다.
* **식별자 명명 규칙:**
  * **본칙 조문:** `제N조` 형식을 유지한다.
  * **부칙 조문:** **`[부칙] 제N조`** 형식으로 접두사를 강제 부여하여 본칙 데이터가 덮어씌워지는 것을 방지한다.
* **데이터 무결성:** 부칙 섹션 추출 시에도 본칙과 동일한 하이라키 및 클리닝 로직을 적용한다.

## 7. 도메인 스키마 및 수집 분리 원칙 (Domain Isolation Strategy)

* **Bounded Context 분리 (DDD):** 데이터의 생김새(형식)와 계층 구조가 완전히 다르므로, 단일 릴레이션이나 모델로 통합하지 않고 물리적/논리적으로 도메인을 격리(Isolation)한다.
* **LLM (RAG) 프롬프트 최적화:** AI가 조언 생성 시 답변의 법적 구속력(위계)을 구분할 수 있도록 다음과 같이 성격을 명시하여 수집하고 관리한다.
  * **법령 (Statute):** 대외적 구속력이 있는 국가의 최상위/기본 체계 법규 (예: 형법, 형사소송법, 경찰수사규칙, 검사와 사법경찰관의 상호협력과 일반적 수사준칙에 관한 규정)
    * **주의 (실무 지식 1):** **'경찰수사규칙'**은 명칭이 규칙이지만 실질은 제정 주체가 행정안전부인 **'행정안전부령(부령)'**입니다. 법률의 위임을 받아 대외적 법적 구속력을 갖는 엄연한 **법령(Statutes)**으로 분류해야 합니다. (`law.go.kr`에서도 최상위 법령 API인 `lsInfoP.do`로 서비스됨)
    * **주의 (실무 지식 2):** **'검사와 사법경찰관의 상호협력과 일반적 수사준칙에 관한 규정'**은 약칭 '수사준칙'으로 불리며, 명칭이 규정이지만 그 실질은 헌법상 법률의 하위인 **'대통령령'**입니다. 따라서 수사기관 전체(검사와 사법경찰관)를 기속하는 외부적이고 강력한 효력을 가지므로 반드시 **법령(Statutes)**으로 분류해야 합니다.
  * **행정규칙 (Admin Rule):** 경찰 등 행정조직 내부에서만 효력을 가지는 직무 처리 기준 규정 (예: 범죄수사규칙)
    * **주의 (실무 지식):** **'범죄수사규칙'**은 경찰청 내부의 **'훈령'**이므로 조직 밖의 국민이나 재판에 직접적 구속력이 없는 **행정규칙(Admin Rules)**에 해당합니다. (`law.go.kr`에서도 `admRulInfoP.do`로 분리 서비스됨)
  * **판례 (Precedent):** 법원의 구체적 사건에 대한 판단 및 법리 해석 기준

## 8. 프로세스 무결성 및 리소스 정리 (Process Management)

* **식별자 고정 (Unique ID):** 모든 실행 창(터미널)은 `LAW_TUI`라는 고유한 Window Title을 가져야 하며, 이를 통해 중복 실행 여부와 잔여 프로세스를 식별한다.
* **선행 정리 (Kill-before-Run):** `run.bat` 실행 시, 동일한 타이틀을 가진 기존 프로세스 트리 전체(`/T` 옵션)를 강제 종료하여 메모리 누수나 포트 충돌, DB 락 문제를 원천 차단한다.
* **비정상 종료 대응:** 터미널 창 폐쇄(Close 버튼) 시 발생하는 `SIGBREAK` 등의 시그널을 핸들링하여, 애플리케이션 수준에서 데이터베이스 연결 및 브라우저 세션을 최대한 안전하게 해제한다.
* **전체 트리 종료:** 단순히 부모 프로세스만 종료하지 않고, Playwright 브라우저 등 모든 자식 프로세스가 함께 종료되도록 프로세스 트리 단위의 관리를 수행한다.

## 9. 구조적 추출 (Structural Extraction) 원칙

* **원칙:** 법령 데이터 추출 시 단순 `get_text()`와 정규식 분할에 의존하지 않고, 브라우저 DOM 구조를 직접 탐색하여 조문 블록을 식별한다.
* **이유:** 법령 텍스트 내에는 조문 헤더와 유사한 참조 문구(예: '법 제1조에 따라')가 빈번하게 등장하므로, 텍스트 기반 분할은 오작동 위험이 매우 높다.
* **구현:** `Javascript`를 통해 DOM 내의 `p`, `div` 등 블록 요소를 순회하며 헤더 패턴을 가진 요소를 대상으로 본문 내용을 병합하는 방식을 사용한다.

## 10. scripts 폴더 구조 및 관리 원칙 (Tooling Isolation)

*   **원칙:** 핵심 소스 코드(`src/`)와 프로젝트 설정 파일을 제외한 모든 유틸리티, 디버깅 도구, 임시 테스트 스크립트는 `scripts/` 폴더 아래에 논리적으로 격리한다.
*   **세부 구조:**
    *   **`scripts/check/`**: 데이터 및 상태 검증용 (DB 스키마, 조문 카운트 등)
    *   **`scripts/debug/`**: 디버깅 도구 및 Playwright HTML 덤프 파일
    *   **`scripts/find/`**: 특정 데이터 조회 및 URL 추출 유틸리티
    *   **`scripts/test/`**: 일회성 기능 테스트 및 프로토타입 스크립트
    *   **`scripts/fix/`**: 환경 설정 복구 및 데이터 정규화(reclean_data.py 등) 도구
    *   **`scripts/research/`**: DOM 구조 분석 및 R&D 목적의 스크립트
    *   **`scripts/export/`**: 데이터셋 번들 생성(reexport_data.py 등) 유틸리티
*   **실행 가이드:** 모든 스크립트는 프로젝트 루트에서 `uv run scripts/...` 명령을 통해 실행하여 상대 경로 무결성을 유지해야 한다.

## 11. 운영 복원력 및 체크포인트 (Resilience)

* **원칙**: 대규모 데이터 수집 시 브라우저 충돌, 네트워크 장애 등에 대응하기 위해 조문(Article) 단위의 진행 상태를 실시간으로 기록한다.
* **체크포인트 메커니즘**:
  - scrape_runs 테이블의 checkpoint 컬럼에 현재 처리 중인 조문의 **0-based Index**를 저장한다.
  - 각 조문이 DB에 성공적으로 UPSERT된 직후 체크포인트를 업데이트하여 데이터 유실을 최소화한다.
* **재개(Resume) 로직**:
  - 작업 시작 시 Repository.get_last_checkpoint를 통해 해당 소스의 마지막 미완료(status != 'completed') 기록을 확인한다.
  - 스크래퍼는 로드된 인덱스 이하의 조문은 추출 루프에서 건너뛰고(Skip) 이후 데이터부터 처리를 재개한다.
  - 모든 조문 수집이 성공적으로 완료되면 체크포인트를 completed로 마킹하여 중복 수집을 방지한다.
## 12. 사법정보공개포털(scourt.go.kr) 판례 수집 원칙

### 12-1. 아키텍처: WAF 우회를 위한 브라우저 내 fetch()

* **문제:** 포털은 외부 직접 HTTP 요청(httpx, requests 등)을 WAF(Web Application Firewall)로 탐지하여 차단한다. 에러 응답: {"timestamp": ..., "errors": {"errorMessage": "사용에 불편을 드려서 죄송..."} }.
* **해결 원칙 (Critical):** **Playwright 브라우저의 실제 UI 상호작용(클릭, 입력)을 주력으로 사용한다.**
  * 내부 API(fetch) 호출은 세션 및 CSRF 토큰 검증이 매우 까다로워(500 에러 빈번) 안정성이 낮다.
  * 따라서 좌측 메뉴 트리 클릭, 검색 버튼 클릭, 페이지네이션 버튼 클릭을 통해 데이터를 로드하고 DOM에서 직접 추출한다.
  * WebSquare5 초기화 및 안정적인 렌더링을 위해 **최소 15초(SCOURT_INIT_WAIT_SEC)** 대기 후 작업을 시작한다.
  * **데이터 로딩 동기화:** 총 건수(`.w2textbox` 내 숫자 포함 여부) 감지 및 결과 목록(`.gen_cntntsList_`) 존재 여부로 데이터 로드 완료를 판단한다. CSS `::before`로 삽입된 "총" 텍스트 대신 `innerText`의 숫자 패턴(\d+)을 SSOT로 활용한다.
* **금지:** 포털 API를 외부에서 httpx 등으로 직접 호출하는 방식은 재작성하지 말 것.

### 12-2. 확인된 API 엔드포인트 및 파라미터 (브라우저 인터셉트, 2026-03-08)

#### 목록 조회 API
* **URL:** POST https://portal.scourt.go.kr/pgp/pgp1011/selectJdcpctSrchRsltLst.on
* **필수 헤더:**
  * sc-pgmid: PGP1011M01
  * submissionid: mf_mainFrame_sbm_selectJdcpctSrchLst
* **필수 페이로드:**
  `json
  {
    "dma_searchParam": {
      "srchwd": "형사",
      "jdcpctCdcsCd": "02",
      "pageNo": "1",
      "pageSize": "100",
      "sort": "jis_jdcpc_instn_dvs_cd_s asc,  desc, prnjdg_ymd_o desc, jdcpct_gr_cd_s asc",
      "jdcpctGrCd": "111|112|130|141|180|182|232|235|201",
      "category": "jdcpct",
      "isKwdSearch": "N"
    }
  }
  `
  * jdcpctCdcsCd: "02" = 형사 전용 필터 (핵심)
  * srchwd는 반드시 비어있지 않아야 한다 ("형사" 권장)
  * pageNo, pageSize는 **문자열 타입**으로 전달해야 한다
* **응답 구조:** { "data": { "dlt_jdcpctRslt": [...] } }
* **목록 수집 (UI Selection):**
  * 검색 결과 목록 버튼: `a[id*='gen_cntntsList_'][id$='btn_jisCsNoCsNm']`
  * 항목별 고유 번호(jisCntntsSrno): 위 버튼 ID 문자열 파싱 또는 `page.evaluate()`로 내부 데이터 객체 접근.
  * 사건번호/선고일/사건명: 해당 `<a>` 태그의 텍스트 콘텐츠 파싱.
* **페이지네이션 (Pagination):**
  * 다음 페이지 버튼: `.w2pageList_col_next`
  * WebSquare5 특성상 클릭 후 "조회중" 레이어가 사라질 때까지 대기 필수.

#### 상세 본문 조회 API
* **URL:** POST https://portal.scourt.go.kr/pgp/pgp1011/selectJdcpctCtxt.on
* **필수 헤더:**
  * sc-pgmid: PGP1011M04
  * submissionid: mf_wfm_pgpDtlMain_sbm_selectJdcpctCtxt
* **페이로드:**
  `json
  { "dma_searchParam": { "jisCntntsSrno": "판례고유번호", "srchwd": "형사", "systmNm": "PGP" } }
  `
* **응답 구조:** { "data": { "dma_jdcpctCtxt": { "orgdocXmlCtt": "HTML_전문" } } }
* **본문 섹션 파싱:** orgdocXmlCtt HTML 내에서 【판시사항】, 【판결요지】, 【전 문】, 【참조조문】, 【참조판례】 마커로 regexp 분할

### 12-3. 형사 판례 2차 방어 필터

* API 레벨에서 jdcpctCdcsCd: "02"로 형사 필터링되지만, 수집 후 아래 기준으로 재검증한다.
* **1차:** jdcpctCdcsCdNm 필드에 "형사" 포함 여부
* **2차 (사건번호 기반):** 사건번호에 형사 관련 부호 포함 여부
  * 1심: 고합, 고단, 고정, 고약
  * 항소: 노, 느
  * 상고: 도
  * 기타: 감, 초, 전합

### 12-4. Source 등록 정보

`python
# config.py SOURCES 딕셔너리
"scourt_criminal_precedent": SourceConfig(
    name="대법원 사법정보공개포털 형사판례",
    url="https://portal.scourt.go.kr/pgp/index.on?m=PGP1011M01&l=N&c=900",
    scraper="scourt_precedent",
    table="precedents",
)
`

* **scraper 타입:** "scourt_precedent" → ScourtPrecedentScraper (BaseScraper 상속)
* **저장 테이블:** precedents (기존 law_go_kr_precedent와 동일 테이블, source_key로 구분)
* **체크포인트 Resume:** 11조(CRITICAL_LOGIC.md)의 표준 체크포인트 메커니즘 적용