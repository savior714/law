# Legal Data Scraper

수사경찰을 위한 한국 형사 법령/판례 스크래핑 및 NotebookLM RAG 데이터셋 빌더.

## 개요

법제처 국가법령센터(law.go.kr)와 사법정보공개포털(portal.scourt.go.kr)에서 형사 관련 법령과 판례를 자동 수집하고, NotebookLM에 바로 넣을 수 있는 텍스트 번들로 변환합니다.

## 수집 대상

| 소스 | 사이트 | 설명 |
|---|---|---|
| 형법 | law.go.kr | 형법 전문 (총칙/각칙) |
| 형사소송법 | law.go.kr | 형사소송법 전문 |
| 경찰관직무집행법 | law.go.kr | 경찰관직무집행법 전문 |
| 범죄수사규칙 | law.go.kr | 행정규칙 전문 |
| 판례검색 | law.go.kr | 형사 판례 (대법원) |
| 대법원 형사판례 | portal.scourt.go.kr | 사법정보공개포털 형사 판례 |

## 기술 스택

- **Language:** Python 3.12+ (uv)
- **Scraping:** Playwright (GUI 모드)
- **UI:** Textual (TUI)
- **DB:** SQLite (중간 저장) → MD/TXT 번들 출력

## 설치

```bash
# uv 설치 (아직 없다면)
pip install uv

# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium
```

## 실행

```bash
uv run law
```

## 파이프라인

```
1. Scrape  →  Playwright로 대상 사이트에서 법령/판례 수집
2. Store   →  Pydantic 검증 후 SQLite에 저장
3. Export  →  SQLite → NotebookLM용 BUNDLE txt 파일로 변환
```

## 프로젝트 구조

```
src/law/
├── app.py              # Textual TUI 진입점
├── config.py           # URL, 셀렉터, 경로 상수
├── db/                 # SQLite 스키마 및 CRUD
├── scrapers/           # 사이트별 스크래퍼
├── export/             # NotebookLM 번들 빌더
├── models/             # Pydantic 데이터 모델
└── utils/              # 무결성 검증, 텍스트 처리
```

## 출력물

`data/export/` 폴더에 생성:
- `00_MASTER_ATLAS.md` - 데이터셋 인덱스
- `BUNDLE_STATUTE_XX.txt` - 법령 번들
- `BUNDLE_ADMIN_RULE_XX.txt` - 행정규칙 번들
- `BUNDLE_PRECEDENT_XX.txt` - 판례 번들

각 번들은 ~4MB 이하로 분할되어 NotebookLM에 바로 업로드 가능합니다.
