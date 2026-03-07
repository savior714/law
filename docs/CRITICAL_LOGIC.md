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

## 3. 데이터 클리닝 및 노이즈 제거 (Noise Removal)

* **UI 요소 제거:** 법령 본문 추출 시, `law.go.kr`의 레이어 팝업이나 툴바 등 불필요한 DOM 요소를 명시적으로 제거해야 한다.
  * **대상:** `#lsByl` (별표/서식 리스트), `.p_layer_copy` (주소 복사), `.ls_sms_list`, `.pconfile`, `.note_list` 등.
* **공백 정규화:** `normalize_whitespace` 함수는 줄바꿈 전 각 행의 앞뒤 공백을 `strip` 처리하여, 스페이스만 포함된 빈 줄이 정확히 감지되고 축소되도록 보장해야 한다.
* **텍스트 흐름(Flow) 및 계층 보존 처리:**
  * `clean_html_text`는 인라인 태그로 인해 파편화된 행들을 하나의 문장으로 합치되, 법령 구조를 나타내는 마커가 있는 경우 줄을 바꾼다.
  * **RAG 최적화 들여쓰기:** 구조적 가독성을 위해 다음의 들여쓰기를 삽입한다.
    * **조문 제목:** 들여쓰기 없음
    * **항(①, ②):** 0칸 (좌측 정렬)
    * **호(1., 2.):** **2칸 공백** 들여쓰기
    * **목(가., 나.):** **4칸 공백** 들여쓰기
  * **정보 누락 방지:** 조문 제목과 본문 사이에 줄바꿈(`\n`)을 강제하여 계층 분리를 명확히 한다.

## 4. 데이터 무결성 및 SSOT

* **증분 수집:** `content` 필드의 SHA-256 해시값(`content_hash`)을 생성하여 중복을 방지한다.
* **저장 원칙:** `source_key`와 `article_number` (또는 `case_number`)를 유니크 키로 사용하여 `UPSERT` 처리한다.
* **NotebookLM 최적화:** 출력물은 파일당 약 4MB(`BUNDLE_MAX_BYTES`) 단위로 분할하며, `MASTER_ATLAS.md`를 통해 전체 인덱스를 제공한다.

## 5. 아키텍처 패턴 (3-Layer)

* **Definition:** `src/law/models/schemas.py` (Pydantic 모델)
* **Repository:** `src/law/db/repository.py` (SQLite 비동기 CRUD)
* **Service/Logic:** `src/law/scrapers/` (사이트별 추출 로직)
