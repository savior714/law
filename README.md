# Legal Data Scraper

수사경찰을 위한 한국 형사 법령/판례 스크래핑 및 NotebookLM RAG 데이터셋 빌더.

## 개요

법제처 국가법령센터(law.go.kr)와 사법정보공개포털(portal.scourt.go.kr)에서 형사 관련 법령과 판례를 자동 수집하고, **계층 구조(조, 항, 호, 목)를 보존한 채 NotebookLM RAG에 최적화된 텍스트 번들**로 변환합니다.

## 특징 및 개선 사항

- **가독성 최적화:** 법령 본문의 항(①), 호(1. - 2칸), 목(가. - 4칸) 계층에 따른 **자동 들여쓰기**를 적용하여 AI와 사용자 모두에게 명확한 구조를 제공합니다.
- **노이즈 제거:** 법제처의 UI 요소(주소 복사, 툴바 등)를 완벽히 제거한 순수 법령 텍스트만 추출합니다.
- **행정규칙 지원:** '경찰수사규칙'과 같은 행정규칙(admRulInfoP.do) 템플릿의 완벽한 수집을 지원합니다.

## 수집 대상

| 소스 | 사이트 | 설명 |
| :--- | :--- | :--- |
| 경찰수사규칙 | law.go.kr | 경찰관직무집행법 (lsId=013976) 기반 수사 규칙 |
| 범죄수사규칙 | law.go.kr | 범죄수사 절차 및 행정규칙 |
| 형사소송법 | law.go.kr | 형사소송 절차 전반 |
| 수사준칙 | law.go.kr | 검사와 사법경찰관의 상호협력과 일반적 수사준칙 |
| 형법 | law.go.kr | 형법 전문 (총칙/각칙) |

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

```text
1. Scrape  →  Playwright로 대상 사이트에서 법령/판례 수집
2. Store   →  Pydantic 검증 후 SQLite에 저장
3. Export  →  SQLite → NotebookLM용 BUNDLE txt 파일로 변환
```

## 프로젝트 구조

```text
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
