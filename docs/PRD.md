# [Project Name] PRD (Product Requirements Document)

## 1. 프로젝트 개요 (Overview)

- **목적:** 와이프가 수사경찰인데, 사건 해결하려고 할 때 매번 법제처 국가법령센터, 사법정보공개포털 등에서 매번 일일이 조회하고 찾아보면서 에너지 낭비가 심함 → 이를 한 곳에 데이터 스크래핑을 해서 그걸 NotebookLM에 넣어두고 RAG system 활용해서 쉽게 활용해서 쓸 수 있도록

## 2. 사용자 페르소나 및 유저 스토리 (User Personas & Stories)

- **주요 사용자:** 와이프(수사경찰), 단독
- **유저 스토리:** 관계 사이트들에서 관계 법령들, 판례들을 풀 스크래핑해서, 그걸 나만의 DB로 만들어 NotebookLM에 넣고 나만의 비서같은 챗봇을 만들기를 원한다. 그래야 일일이 충돌하는 논리 등을 찾아보며 골머리 썩지 않고 일을 더 빠르게 진행할 수 있기 때문이다.

## 3. 핵심 기능 (Key Features - Scope)

- **MVP(최소 기능 제품) 범위:** 반드시 포함되어야 할 핵심 기능 목록.
    - 소스들 범위 (https://www.law.go.kr/LSW//admRulInfoP.do?admRulSeq=2100000272092&chrClsCd=010201#AJAX, https://www.law.go.kr/LSW/lsInfoP.do?lsId=013976#AJAX, https://www.law.go.kr/LSW/lsInfoP.do?lsId=001671&ancYnChk=0#0000, https://www.law.go.kr/lsSc.do?query=%ED%98%95%EB%B2%95#AJAX, https://portal.scourt.go.kr/pgp/index.on?m=PGP1011M01&l=N&c=900 → 이거에서 ‘형사’ 만, https://www.law.go.kr/precSc.do) 전부 스크래핑
    - SQLite DB로 중간 저장 → MD/TXT로 변환 → NotebookLM용 번들 파일(~4MB 단위)로 분할 출력
- **제외 범위:**
    - 경찰 내부망 자료 연동 (외부 공개 자료 우선 구축 후 추후 검토)
    - 형사 외 다른 분야(민사, 행정 등) 법령/판례
    - 형사 관련 특별법(성폭력처벌법, 마약류관리법 등) - 향후 확장 고려
    - NotebookLM API 자동 업로드 (수동 업로드로 진행)
    - 법령 개정 이력 추적 (현행 법령만 수집)

## 4. 사용자 흐름 및 UI/UX 요구사항 (User Flow & UI/UX)

- **유저 저니(User Journey):** 사용자가 프로그램을 실행해서 목표를 달성하기까지의 단계별 흐름.
    - 해당 소스(사이트별) 스크래핑 버튼 누르면 → 알아서 법률 내용들 다 긁어옴 → dataset 빌드
- **UI 요구사항:** GUI preference (비-headless 선호), 화면 구성 요소 설명.
    - Python(uv) + Textual(TUI) 기반으로 개발. 소스 선택 체크박스, 스크래핑 시작/진행률, 데이터셋 빌드 버튼, 로그 출력으로 구성

## 5. 성공 지표 (Success Metrics)

- 프로그램이 의도대로 작동함을 어떻게 측정할 것인가? (예: 작업 성공률 100%)
    - 스크래핑 제대로 해 오는지 (무결성 검증 로직까지 탑재)
    - dataset 잘 형성하는지 (무결성 검증 로직까지 탑재)
    - NotebookLM에 넣고 잘 돌아가는지

## 6. 제약 사항 및 고려 사항 (Constraints)

- 기술적/비즈니스적 제약 조건 (예: 특정 사이트의 차단 정책 등).
    - 경찰 내부망의 자료는 못 가져옴 (외부에 공개된 자료들 먼저 다 구축하고 그 뒤에 생각키로)
    - 대법원 포털(portal.scourt.go.kr)은 JS 렌더링이 무겁고 세션/안티봇 제한이 있을 수 있음
    - law.go.kr은 AJAX 기반 동적 페이지로 Playwright 브라우저 자동화 필수