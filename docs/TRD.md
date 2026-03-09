# Legal Data Scraper TRD (Technical Requirements Document)

## 1. 기술 스택 (Tech Stack)

### 1.1 런타임 및 패키지 관리

| 도구 | 용도 |
|---|---|
| Python 3.14 (64-bit) | 런타임 (최신 안정성 확보) |
| uv | 패키지 관리, 가상환경, 스크립트 실행 |

### 1.2 핵심 라이브러리

| 라이브러리 | 용도 |
|---|---|
| `playwright` | AJAX 기반 법률 사이트 브라우저 자동화 |
| `textual` | 터미널 UI (TUI) 프레임워크 |
| `sqlite3` (내장) | 중간 데이터 저장소 |
| `aiosqlite` | 비동기 SQLite 접근 (Textual 비동기 호환) |
| `beautifulsoup4` + `lxml` | Playwright로 캡처한 HTML 파싱 |
| `pydantic` | 스크래핑 데이터 검증 모델 |
| `rich` | 컬러 콘솔 로깅 (Textual 의존성) |

### 1.3 개발 도구

| 라이브러리 | 용도 |
|---|---|
| `pytest` | 테스트 |
| `ruff` | 린팅 + 포매팅 |

### 1.4 환경 모드

- **Playwright**: GUI 모드 기본 설정 (`headless=False`)
- **인코딩**: UTF-8 전역 준수

---

## 2. 시스템 아키텍처 (System Architecture)

### 2.1 폴더 구조

```
├── pyproject.toml
├── uv.lock
├── .python-version
├── run.bat                  # 터미널 전체화면/프로세스 정리 실행 파일
├── reset_data.bat           # 데이터 하드리셋 도구
├── docs/
│   ├── PRD.md
│   ├── TRD.md
│   ├── CRITICAL_LOGIC.md    # SSOT (물리적 진실의 원천)
│   └── memory.md            # 작업 이력 및 컨텍스트
├── scripts/                 # 유틸리티 및 디버깅 도구 격리
│   ├── check/               # 데이터 검증 (counts, schema, ids)
│   ├── debug/               # HTML 덤프 및 탭 분석
│   ├── find/                # 특정 조문/URL 조회
│   ├── test/                # 단위/통합 테스트 스크립트
│   ├── fix/                 # 환경 복구 도구
│   └── research/            # DOM 구조 분석 R&D
├── src/
│   └── law/
│       ├── app.py           # TUI 엔트리포인트 (SIGBREAK 핸들링)
<truncated 22 lines>
│           └── text.py      # 한글 텍스트 흐름(Flow) 및 들여쓰기 최적화
├── data/
│   ├── law_meta.db          # 수집 상태 및 체크포인트 (Meta Shard)
│   ├── law_statutes.db      # 법령 및 행정규칙 (Statute Shard)
│   ├── law_precedents.db    # 형사 판례 (Precedent Shard)
│   ├── law_decisions.db     # 결정례/해석례 (Decision Shard)
│   └── export/              # BUNDLE_MAX_BYTES 단위 분할 출력
└── tests/                   # pytest 기반 공식 테스트 코드
```

### 2.2 데이터 흐름

```
[Textual TUI (app.py)]
    │
    ├── [소스 선택] ──► [Scraper 모듈]
    │                       │
    │                       ├── law_statute.py ──┐
    │                       ├── law_admin_rule.py│
    │                       ├── law_decision_ext.py ├──► Playwright Browser
    │                       └── scourt_precedent.py   (GUI 모드)
    │                              │
    │                              ▼
    │                    [Pydantic 검증]
    │                              │
    │                              ▼
    │                    [SQLite Repository]
    │                       (data/law.db)
    │                              │
    ├── ["데이터셋 빌드" 실행] ────┘
    │                              │
    │                              ▼
    │                    [Export Builder]
    │                              │
    │                              ▼
    │                    data/export/*.txt
    │                    (NotebookLM 번들)
    │
    └── [진행상황, 로그, 상태 표시]
```

### 2.3 파이프라인 단계

| 단계 | 설명 |
|---|---|
| **Stage 1 - Scrape** | Playwright가 대상 사이트 탐색, AJAX 대기, DOM 콘텐츠 추출. 각 스크래퍼가 Pydantic 모델 인스턴스를 반환 |
| **Stage 2 - Store** | Repository 레이어가 검증된 레코드를 SQLite에 저장. content_hash로 중복 감지. 스크래핑 메타데이터(타임스탬프, 소스 URL, 상태) 추적 |
| **Stage 3 - Export** | Builder가 SQLite에서 읽고, formatter로 각 레코드를 포매팅, ~4MB 크기 제한에 맞춰 BUNDLE 파일로 분할 생성, MASTER_ATLAS.md 인덱스 생성 |

---

## 3. 상세 기능 설계 (Feature Implementation Detail)

### 3.1 BaseScraper 추상 클래스 (`scrapers/base.py`)

```
class BaseScraper(ABC):
    Properties:
        name: str               # e.g., "criminal_act"
        source_url: str         # 기본 URL
        browser: Browser        # Playwright 브라우저 인스턴스
        page: Page              # Playwright 페이지

    Abstract methods:
        async def scrape() -> AsyncGenerator[ScrapedRecord, None]
        async def validate_page_loaded() -> bool

    Concrete methods:
        async def init_browser(headless=False) -> None
        async def safe_navigate(url, wait_selector) -> None   # 재시도 로직 포함
        async def get_page_content() -> str
        async def close() -> None
```

- `headless=False` 기본값 (PRD GUI 모드 요구사항)
- `safe_navigate()`는 `page.goto()` + 재시도 + 설정 가능한 타임아웃 래핑

### 3.2 법령 스크래퍼: `law_statute.py` (형법, 형사소송법, 경찰관직무집행법)

세 법령 모두 law.go.kr의 `lsInfoP.do` 페이지 템플릿을 공유한다.

**Playwright 시나리오:**

1. **페이지 접속**: `lsInfoP.do` 직접 접근 (SSOT)
2. **AJAX 대기 및 탭 보장**: `ensure_tab_active` 로직으로 [본문] 탭 상태 강제
3. **구조적 추출 (Structural Extraction)**: 
   - Javascript (`page.evaluate`) 기반의 DOM 순회 실행
   - 조문 헤더 패턴(`.ls_nms_list` 등) 식별 및 본문 블록 병합
   - 텍스트 기반 분할의 참조 문구 오작동(예: '법 제1조에 따라') 원천 차단
4. **본칙/부칙 분리**: `addenda` 섹션을 물리적으로 분할하여 중복 번호 충돌 방지
5. **별지 수집**: 단일 JS 실행으로 PDF/HWPX URL 고속 추출

**핵심 CSS 셀렉터:**
- 법령 본문: `#lsBdy`, `div[id="bodyContent"]`
- 트리 항목: `.lawcon .dep_in`
- 조문 텍스트: `#lsBdy` 내 `제\d+조` 패턴 포함 엘리먼트

**출력**: 조(Article) 단위 `StatuteArticle` 레코드

### 3.3 행정규칙 스크래퍼: `law_admin_rule.py` (경찰수사규칙)

law.go.kr의 `admRulInfoP.do` 템플릿 사용.

**Playwright 시나리오:**

1. **페이지 접속**: `https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000272092&chrClsCd=010201`
2. **AJAX 대기**: `bodyContent` div 로딩 대기 (AJAX `admRulLsInfoR.do` 호출)
3. **구조 추출**: 좌측 사이드바 조문 트리에서 구조 파싱
4. **본문 추출**: `bodyContent`에서 규칙 본문 텍스트 추출
5. **부칙/별표 파싱**: 부칙(supplementary provisions) 및 별표/서식(appendices) 포함 처리

**출력**: 조(Article) 단위 `AdminRuleArticle` 레코드

### 3.4 법령/판례/결정례 확장 스크래퍼: `law_decision_ext.py` (법제처)

law.go.kr의 `precSc.do`, `detcSc.do`, `expcSc.do`, `allDeccSc.do` 등을 통한 다각화 수집.
`LawGoKrDecisionBaseScraper`를 상속받아 공통 AJAX 패턴 및 상세 페이지 추출 로직을 공유한다.

**Playwright 시나리오:**

1. **페이지 접속**: `https://www.law.go.kr/precSc.do`
2. **상세검색 오픈**: 상세검색 패널 열기
3. **필터 설정**:
   - 사건종류: "형사" 선택
   - 법원: "대법원" 선택
   - 정렬: 선고일자 내림차순
4. **검색 실행**: 결과 로딩 대기
5. **페이지네이션 루프**:
   - "총 N건"에서 전체 결과 수 읽기
   - 페이지당 결과 최대치(150건) 설정
   - 각 결과 행: 사건명, 선고일자, 사건번호 추출
   - 결과 클릭 → 상세 페이지에서 추출:
     - 판시사항, 판결요지, 참조조문, 참조판례, 전문
   - 결과 목록으로 복귀
   - 다음 페이지 이동
6. **속도 제한**: 상세 페이지 방문 간 `asyncio.sleep(1~2초)` 삽입

**출력**: 사건 단위 `Precedent` 레코드

### 3.5 대법원 판례 스크래퍼: `scourt_precedent.py` (사법정보공개포털)

`portal.scourt.go.kr` 대상.

**Playwright 시나리오:**

1. **페이지 접속**: `https://portal.scourt.go.kr/pgp/index.on?m=PGP1011M01&l=N&c=900`
2. **세션 처리**: 이용약관 동의 또는 세션 초기화 대기. 메인 검색 인터페이스 로딩 확인
3. **필터 설정**: `c=900` 카테고리 코드로 형사 사건 대상 확인. 필요시 형사 카테고리 필터 선택
4. **검색 실행**: 빈 쿼리로 전체 형사 판례 조회, 또는 결과가 너무 많으면 연도별 날짜 범위 분할
5. **페이지네이션 루프**:
   - 결과 목록 파싱
   - 각 결과: 클릭 → 상세 페이지 열기
   - 추출: 사건번호, 선고일자, 법원, 사건유형, 판결문 전문
   - 결과 목록 복귀 → 다음 페이지
6. **날짜 범위 분할 전략**: 포털 결과 제한(예: 최대 1000건) 시 연도/월 단위 분할 쿼리로 전체 데이터 확보

**출력**: 사건 단위 `Precedent` 레코드

### 3.6 Textual TUI (`app.py`)

**화면 레이아웃:**

```
┌─────────────────────────────────────────────────┐
│  Korean Legal Data Scraper           [Q]uit     │
├─────────────────────────────────────────────────┤
│                                                 │
│  [1] Scrape Sources                             │
│  ┌─────────────────────────────────────┐        │
│  │ ☐ 경찰수사규칙                      │        │
│  │ ☐ 경찰관직무집행법                  │        │
│  │ ☐ 형사소송법                        │        │
│  │ ☐ 형법                              │        │
│  │ ☐ 대법원 형사판례 (scourt)          │        │
│  │ ☐ 판례검색 (law.go.kr)             │        │
│  └─────────────────────────────────────┘        │
│  [Start Scraping]        [Select All]           │
│                                                 │
│  [2] Build Dataset                              │
│  [Build NotebookLM Export]                      │
│                                                 │
├─────────────────── LOG ─────────────────────────┤
│  14:23:01 | INFO | 스크래핑 시작...             │
│  14:23:05 | INFO | 형법: 372개 조문 수집        │
│  14:23:06 | OK   | 무결성 검증 ✓                │
│                                                 │
├────────────────── PROGRESS ─────────────────────┤
│  형사소송법  [████████████░░░░░░░░]  62%        │
│  Total: 245 / 493 articles                      │
└─────────────────────────────────────────────────┘
```

**Textual 컴포넌트:**
- `App` 서브클래스 + `ComposeResult`
- `Header`, `Footer`: 타이틀 및 키바인딩
- `SelectionList`: 소스 체크박스
- `Button`: 스크래핑 시작, 전체 선택, 데이터셋 빌드
- `RichLog`: 스크롤 가능한 로그 출력
- `ProgressBar`: 스크래핑 진행률
- `Worker` 패턴: 백그라운드 태스크로 스크래핑 실행, UI 반응성 유지

---

## 4. 데이터 모델링 (Data Modeling)

### 4.1 SQLite 스키마

```sql
-- 스크래핑 실행 추적 테이블
CREATE TABLE scrape_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL,
    started_at      TEXT NOT NULL,       -- ISO 8601
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',  -- running | completed | failed
    total_records   INTEGER DEFAULT 0,
    error_message   TEXT
);

-- 법령 테이블: 형법, 형사소송법, 경찰관직무집행법
CREATE TABLE statutes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL,
    law_name        TEXT NOT NULL,       -- e.g., '형법'
    part            TEXT,                -- 편
    chapter         TEXT,                -- 장
    section         TEXT,                -- 절
    subsection      TEXT,                -- 관
    article_number  TEXT NOT NULL,       -- e.g., '제1조'
    article_title   TEXT,                -- e.g., '(범죄의 성립과 처벌)'
    content         TEXT NOT NULL,
    content_hash    TEXT NOT NULL,       -- SHA-256
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    scrape_run_id   INTEGER REFERENCES scrape_runs(id)
);
CREATE UNIQUE INDEX idx_statutes_unique ON statutes(source_key, article_number);

-- 행정규칙 테이블: 경찰수사규칙
CREATE TABLE admin_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL DEFAULT 'crime_investigation_rules',
    rule_name       TEXT NOT NULL,
    part            TEXT,
    chapter         TEXT,
    section         TEXT,
    article_number  TEXT NOT NULL,
    article_title   TEXT,
    content         TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    scrape_run_id   INTEGER REFERENCES scrape_runs(id)
);
CREATE UNIQUE INDEX idx_admin_rules_unique ON admin_rules(source_key, article_number);

-- 판례 테이블: law.go.kr + scourt 포털
CREATE TABLE precedents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL,
    case_number     TEXT NOT NULL,       -- e.g., '2024도12345'
    case_name       TEXT,
    court           TEXT NOT NULL,       -- e.g., '대법원'
    decision_date   TEXT,                -- YYYY-MM-DD
    case_type       TEXT DEFAULT '형사',
    holding         TEXT,                -- 판시사항
    summary         TEXT,                -- 판결요지
    full_text       TEXT,                -- 전문
    referenced_statutes TEXT,            -- 참조조문
    referenced_cases    TEXT,            -- 참조판례
    content_hash    TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    scrape_run_id   INTEGER REFERENCES scrape_runs(id)
);
CREATE UNIQUE INDEX idx_precedents_unique ON precedents(source_key, case_number);

-- 무결성 검증 로그
CREATE TABLE integrity_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name      TEXT NOT NULL,
    record_id       INTEGER NOT NULL,
    checked_at      TEXT NOT NULL,
    hash_match      INTEGER NOT NULL,    -- 1 = OK, 0 = mismatch
    details         TEXT
);
```

### 4.2 Pydantic 모델 (`models/schemas.py`)

```python
class StatuteArticle(BaseModel):
    source_key: str
    law_name: str
    part: str | None = None
    chapter: str | None = None
    section: str | None = None
    subsection: str | None = None
    article_number: str
    article_title: str | None = None
    content: str                         # 정제된 평문 텍스트

class AdminRuleArticle(BaseModel):
    source_key: str = "crime_investigation_rules"
    rule_name: str
    part: str | None = None
    chapter: str | None = None
    section: str | None = None
    article_number: str
    article_title: str | None = None
    content: str

class Precedent(BaseModel):
    source_key: str
    case_number: str
    case_name: str | None = None
    court: str
    decision_date: date | None = None
    case_type: str = "형사"
    holding: str | None = None
    summary: str | None = None
    full_text: str | None = None
    referenced_statutes: list[str] = []
    referenced_cases: list[str] = []
```

### 4.3 소스 키 레지스트리 (`config.py`)

| source_key | 이름 | URL | 스크래퍼 | 테이블 |
|---|---|---|---|---|
| `police_investigation_rules` | 경찰수사규칙 | law.go.kr/admRulInfoP.do?admRulSeq=2100000272092 | law_admin_rule | admin_rules |
| `police_duties_act` | 경찰관직무집행법 | law.go.kr/lsInfoP.do?lsId=013976 | law_statute | statutes |
| `criminal_procedure_act` | 형사소송법 | law.go.kr/lsInfoP.do?lsId=001671 | law_statute | statutes |
| `criminal_act` | 형법 | law.go.kr/lsSc.do?query=형법 | law_statute | statutes |
| `scourt_criminal_precedent` | 대법원 형사판례 | portal.scourt.go.kr/pgp/index.on | scourt_precedent | precedents |
| `law_go_kr_precedent` | 판례검색 | law.go.kr/precSc.do | law_precedent | precedents |

---

## 5. 에러 처리 및 예외 케이스 (Error Handling & Edge Cases)

### 5.1 네트워크 이슈

| 상황 | 대응 전략 |
|---|---|
| 페이지 로드 타임아웃 | 3회 재시도 + 지수 백오프 (5초, 15초, 45초). 경고 로그 출력 |
| 연결 리셋 | 브라우저 종료 → 재초기화 → 마지막 체크포인트부터 재개 |
| 부분 페이지 로드 | AJAX 콘텐츠 로딩 검증: `page.wait_for_selector(selector, timeout=30000)` |
| DNS 실패 | 명확한 에러 메시지로 중단, TUI 로그에 표시 |

### 5.2 셀렉터 변경 (사이트 개편 대응)

- **중앙 관리**: 모든 CSS 셀렉터를 `config.py`에 상수로 정의, 스크래퍼 로직에 분산시키지 않음
- **폴백 셀렉터**: 핵심 엘리먼트에 대해 1차/2차 셀렉터 정의 (예: `#lsBdy` → `div.law_body`)
- **셀렉터 검증**: 첫 페이지 로드 시 `validate_page_loaded()`로 기대 엘리먼트 존재 확인. 실패 시 `SelectorNotFoundError` 발생

### 5.3 안티봇 / 속도 제한

| 사이트 | 전략 |
|---|---|
| law.go.kr | 페이지 이동 간 `asyncio.sleep(1.0)` 삽입. GUI 모드로 일반 사용자와 동일한 브라우저 환경 |
| portal.scourt.go.kr | `asyncio.sleep(2.0)` 삽입. 세션 만료 모니터링 및 재초기화. 차단 감지 시 TUI에 수동 개입 프롬프트 표시 |

- CAPTCHA/차단 페이지 감지 시 스크래핑 일시 중지 + 사용자 알림

### 5.4 페이지네이션

- 페이지 크기 최대치(150건) 설정
- 현재 페이지 번호 및 총 페이지 수 추적
- `scrape_runs` 테이블에 진행 상태 저장 → 중단된 스크래핑 재개 가능
- `page.evaluate()`로 사이트 내장 페이지네이션 JS 함수 호출
- scourt 포털 결과 제한 시 연도/월 단위 날짜 범위 분할 쿼리

### 5.5 데이터 무결성

- **해시 검증**: 모든 레코드의 `content` 필드에 SHA-256 해시를 스크래핑 시점에 생성하여 `content_hash`에 저장
- **후 검증**: 스크래핑 완료 후 해당 run의 전체 레코드 재해시 및 비교. `integrity_log`에 결과 기록
- **중복 감지**: INSERT 전 `(source_key, article_number)` 또는 `(source_key, case_number)` 존재 확인. 해시 일치 시 스킵, 불일치 시 UPDATE + 변경 로그
- **빈 콘텐츠 방지**: Pydantic 검증기로 빈 `content` 필드 거부

### 5.6 한글 텍스트 처리

- **인코딩**: Playwright는 유니코드 문자열 반환. SQLite는 UTF-8 기본. 수동 인코딩 변환 불필요
- **공백 정규화**: 과도한 공백 제거, `\r\n` → `\n`, 연속 빈 줄 축약
- **HTML 엔티티**: BeautifulSoup `get_text()`로 `&nbsp;`, `&amp;` 등 처리
- **법률 특수 문자**: 원 숫자(①②③), 섹션 마크(§) 등 법률 표기 보존

### 5.7 재개 가능성 (Resumability)

- 각 스크래핑 실행을 `scrape_runs` 테이블에서 추적
- 판례 스크래퍼: 마지막 성공 페이지 번호 또는 사건번호 저장
- 재시작 시 DB에서 마지막 성공 레코드 조회 후 그 지점부터 재개

---

## 6. 필수 임포트 및 환경 설정 (Essential Imports & Config)

### 6.1 pyproject.toml

```toml
[project]
name = "law"
version = "0.1.0"
description = "Korean legal data scraper for NotebookLM RAG"
requires-python = ">=3.12"
dependencies = [
    "playwright>=1.49",
    "textual>=1.0",
    "aiosqlite>=0.20",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "pydantic>=2.10",
    "rich>=13.0",
]

[project.scripts]
law = "law.app:main"

[tool.ruff]
line-length = 120

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.8",
]
```

### 6.2 초기 설정 명령

```bash
cd c:\develop\law
uv init
uv add playwright textual aiosqlite beautifulsoup4 lxml pydantic rich
uv add --dev pytest ruff
uv run playwright install chromium
```

### 6.3 config.py 핵심 상수

```python
# 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "law.db"
EXPORT_DIR = DATA_DIR / "export"

# 스크래핑 설정
DEFAULT_TIMEOUT_MS = 30_000
NAVIGATION_DELAY_SEC = 1.0
SCOURT_DELAY_SEC = 2.0
MAX_RETRIES = 3
HEADLESS = False

# 내보내기 설정
BUNDLE_MAX_BYTES = 4_000_000  # ~4MB per bundle
```

### 6.4 NotebookLM 번들 출력 포맷

**MASTER_ATLAS.md** (인덱스 파일):
```markdown
# [MASTER ATLAS] Korean Criminal Law Dataset

| 번들 ID | 레코드 수 | 파일 범위 |
|---|---|---|
| STATUTE | {n}건 | BUNDLE_STATUTE_01.txt ~ _XX.txt |
| ADMIN_RULE | {n}건 | BUNDLE_ADMIN_RULE_01.txt |
| PRECEDENT | {n}건 | BUNDLE_PRECEDENT_01.txt ~ _XX.txt |
```

**BUNDLE_STATUTE_XX.txt** (법령 레코드 포맷):
```
---
## [형법] 제1편 총칙 > 제1장 형법의 적용범위 > 제1조 (범죄의 성립과 처벌)

① 범죄의 성립과 처벌은 행위 시의 법률에 의한다.
② 범죄 후 법률의 변경에 의하여 ...
---
```

**BUNDLE_PRECEDENT_XX.txt** (판례 레코드 포맷):
```
---
## [대법원 2024도12345] 사기죄 / 2024-06-15

### 판시사항
...

### 판결요지
...

### 참조조문
형법 제347조, 형사소송법 제325조

### 전문
...
---
```

---

## 구현 순서 (Implementation Sequence)

| Phase | 내용 |
|---|---|
| **Phase 1** | 프로젝트 스켈레톤: `uv init`, 폴더 구조, `config.py`, SQLite 스키마, Pydantic 모델 |
| **Phase 2** | 법령 스크래퍼: `base.py` → `law_statute.py` + `law_admin_rule.py` (단일 페이지, 페이지네이션 없음) |
| **Phase 3** | 판례 스크래퍼: `law_precedent.py` + `scourt_precedent.py` (페이지네이션, 필터링, 상세 페이지) |
| **Phase 4** | 내보내기: `builder.py` + `formatter.py` (SQLite → NotebookLM 번들) |
| **Phase 5** | TUI: Textual 앱으로 스크래퍼 + 내보내기 연결 |
| **Phase 6** | 무결성 검증, 재개 기능, 에러 처리 고도화, 테스트 |

---

## 제외 범위 (이번 버전 미구현)

- 경찰 내부망 자료 연동
- 형사 외 다른 분야(민사, 행정 등) 법령/판례
- 형사 관련 특별법(성폭력처벌법, 마약류관리법 등) - 향후 확장 고려
- NotebookLM API 자동 업로드 (수동 업로드로 진행)
- 법령 개정 이력 추적 (현행 법령만 수집)
- 다국어 지원
