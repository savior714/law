"""사법정보공개포털(portal.scourt.go.kr) 형사 판례 스크래퍼.

브라우저 DOM 분석(2026-03-08)을 통해 확인된 내부 XHR API를 Playwright 브라우저 내에서
JavaScript evaluate를 통해 직접 호출하는 방식을 사용합니다.

[핵심 설계 결정]
서버가 WAF(봇 차단)를 운영하여 외부 직접 HTTP 요청(httpx 등)을 차단합니다.
따라서 Playwright가 실제 브라우저로 포털에 접속한 뒤, 브라우저 컨텍스트 내에서
fetch()를 통해 API를 호출합니다 (JSESSIONID 등 세션 쿠키가 자동으로 포함됨).

[요약된 API 정보] (브라우저 인터셉트 확인, 2026-03-08)
목록 API: POST /pgp/pgp1011/selectJdcpctSrchRsltLst.on
  - jdcpctCdcsCd: "02" = 형사
  - 응답: data.dlt_jdcpctRslt 배열
  - 필드: jisCntntsSrno, csNoLstCtt(사건번호), cortNm(법원),
          prnjdgYmd(선고일YYYYMMDD), csNmLstCtt(사건명), jdcpctSumrCtt(요약)

상세 API: POST /pgp/pgp1011/selectJdcpctCtxt.on
  - 응답: data.dma_jdcpctCtxt.orgdocXmlCtt (HTML 전문)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import date

from bs4 import BeautifulSoup

from law.config import (
    SCOURT_API_DELAY_SEC,
    SCOURT_API_PAGE_SIZE,
    SCOURT_CRIMINAL_CASE_CODE,
    SCOURT_DELAY_SEC,
    SCOURT_DETAIL_DELAY_SEC,
    SCOURT_INIT_WAIT_SEC,
    SOURCES,
)
from law.models.schemas import Precedent
from law.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

SOURCE_KEY = "scourt_criminal_precedent"

_BASE_URL = "https://portal.scourt.go.kr"
_LIST_API_PATH = "/pgp/pgp1011/selectJdcpctSrchRsltLst.on"
_DETAIL_API_PATH = "/pgp/pgp1011/selectJdcpctCtxt.on"

# ── 2차 방어 필터 — 형사 판례 여부 검증 ──────────────────────────────────
_CRIMINAL_CASE_CODES = {
    "고합", "고단", "고정", "고약",   # 형사 1심
    "노", "느",                        # 형사 항소
    "도",                              # 형사 상고
    "감", "초", "전합",                # 기타 형사
}


def _is_criminal(case_type: str, case_no: str) -> bool:
    """형사 사건 여부를 2차 검증한다."""
    if "형사" in case_type:
        return True
    return any(code in case_no for code in _CRIMINAL_CASE_CODES)


def _parse_date(text: str | None) -> date | None:
    """YYYYMMDD / YYYY.MM.DD / YYYY-MM-DD 패턴 파싱."""
    if not text:
        return None
    # YYYYMMDD 형식
    if len(text) == 8 and text.isdigit():
        try:
            return date(int(text[:4]), int(text[4:6]), int(text[6:]))
        except ValueError:
            return None
    # YYYY.MM.DD 또는 YYYY-MM-DD 형식
    m = re.search(r"(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _extract_section_html(html: str, marker: str) -> str | None:
    """판례 본문 HTML에서 【판시사항】, 【판결요지】 등 섹션을 추출한다."""
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    full = soup.get_text("\n")
    pattern = rf"【{re.escape(marker)}】(.*?)(?=【[^】]+】|$)"
    m = re.search(pattern, full, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


# ── Browser fetch 헬퍼 (Playwright 컨텍스트 내부) ───────────────────────
_LIST_FETCH_JS = """
async (apiPath, payload) => {
    const resp = await fetch(apiPath, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json;charset=UTF-8',
            'Accept': 'application/json, text/plain, */*',
            'sc-pgmid': 'PGP1011M01',
            'submissionid': 'mf_mainFrame_sbm_selectJdcpctSrchLst',
        },
        body: JSON.stringify(payload),
        credentials: 'include',
    });
    const data = await resp.json();
    return { status: resp.status, data: data };
}
"""

_DETAIL_FETCH_JS = """
async (apiPath, payload) => {
    const resp = await fetch(apiPath, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json;charset=UTF-8',
            'Accept': 'application/json, text/plain, */*',
            'sc-pgmid': 'PGP1011M04',
            'submissionid': 'mf_wfm_pgpDtlMain_sbm_selectJdcpctCtxt',
        },
        body: JSON.stringify(payload),
        credentials: 'include',
    });
    const data = await resp.json();
    return { status: resp.status, data: data };
}
"""


class ScourtPrecedentScraper(BaseScraper):
    """사법정보공개포털 형사 판례 스크래퍼.

    Playwright 브라우저로 포털에 접속한 뒤, 브라우저 컨텍스트 내에서
    JavaScript fetch()를 통해 내부 API를 호출합니다.
    이 방식은 JSESSIONID 등 세션 쿠키를 자동으로 포함하므로 WAF를 우회합니다.
    """

    def __init__(self) -> None:
        super().__init__()
        src = SOURCES[SOURCE_KEY]
        self.name = SOURCE_KEY
        self.source_url = src.url

    async def validate_page_loaded(self) -> bool:
        """WebSquare5 프레임이 초기화되었는지 확인한다."""
        el = await self.page.query_selector("#mf_mainFrame")
        return el is not None

    async def _handle_initial_load(self) -> None:
        """포털 접속 및 WebSquare5 JS 완전 초기화 대기."""
        await self.safe_navigate(self.source_url)
        logger.info(
            "%s: WebSquare5 초기화 대기 %ds...",
            self.name, SCOURT_INIT_WAIT_SEC
        )
        await asyncio.sleep(SCOURT_INIT_WAIT_SEC)
        # 초기화 확인
        loaded = await self.validate_page_loaded()
        if not loaded:
            logger.warning("%s: #mf_mainFrame 미발견 — 추가 5초 대기", self.name)
            await asyncio.sleep(5)

    # ── 목록 API (브라우저 내 fetch) ──────────────────────────────────────

    async def _fetch_list_via_browser(self, page_no: int) -> tuple[list[dict], int]:
        """
        포털 세션을 이용하여 목록 API를 호출한다.
        Playwright page.evaluate()를 통해 브라우저 컨텍스트 내에서
        fetch()를 실행하므로 JSESSIONID가 자동 포함됩니다.
        """
        payload = {
            "dma_searchParam": {
                "srchwd": "형사",               # 필수 (빈 문자열 시 서버 경고)
                "jdcpctCdcsCd": SCOURT_CRIMINAL_CASE_CODE,  # "02" = 형사
                "pageNo": str(page_no),
                "pageSize": str(SCOURT_API_PAGE_SIZE),
                "sort": (
                    "jis_jdcpc_instn_dvs_cd_s asc, "
                    "$relevance desc, "
                    "prnjdg_ymd_o desc, "
                    "jdcpct_gr_cd_s asc"
                ),
                "jdcpctGrCd": "111|112|130|141|180|182|232|235|201",
                "category": "jdcpct",
                "isKwdSearch": "N",
            }
        }

        for attempt in range(1, 4):
            try:
                result = await self.page.evaluate(
                    _LIST_FETCH_JS,
                    [_LIST_API_PATH, payload]  # 배열로 전달
                )
                if result.get("status") != 200:
                    logger.warning(
                        "%s: 목록 API status=%d (page=%d)",
                        self.name, result.get("status"), page_no
                    )
                    raise ValueError(f"API status {result.get('status')}")

                data = result.get("data", {})
                inner = data.get("data", data)
                items = inner.get("dlt_jdcpctRslt", [])
                total = int(
                    inner.get("totalCount", 0)
                    or data.get("totalCount", 0)
                    or (items[0].get("totalCnt", 0) if items else 0)
                )
                logger.debug(
                    "%s: 목록 page=%d → %d건 (전체 %d건)",
                    self.name, page_no, len(items), total
                )
                return items, total

            except Exception as exc:
                wait = 3 * attempt
                logger.warning(
                    "%s: 목록 fetch 실패 (시도 %d/3, page=%d): %s — %ds 후 재시도",
                    self.name, attempt, page_no, exc, wait
                )
                if attempt < 3:
                    await asyncio.sleep(wait)

        return [], 0

    # ── 상세 API (브라우저 내 fetch) ──────────────────────────────────────

    async def _fetch_detail_via_browser(self, jis_srno: str) -> dict | None:
        """
        포털 세션을 이용하여 판례 전문 API를 호출한다.
        반환: dma_jdcpctCtxt 딕셔너리 (orgdocXmlCtt 포함)
        """
        payload = {
            "dma_searchParam": {
                "jisCntntsSrno": jis_srno,
                "srchwd": "형사",
                "systmNm": "PGP",
            }
        }

        for attempt in range(1, 4):
            try:
                result = await self.page.evaluate(
                    _DETAIL_FETCH_JS,
                    [_DETAIL_API_PATH, payload]
                )
                if result.get("status") != 200:
                    raise ValueError(f"API status {result.get('status')}")

                data = result.get("data", {})
                inner = data.get("data", data)
                detail = inner.get("dma_jdcpctCtxt", {})
                return detail

            except Exception as exc:
                wait = 3 * attempt
                logger.warning(
                    "%s: 상세 fetch 실패 (시도 %d/3, srno=%s): %s — %ds 후",
                    self.name, attempt, jis_srno, exc, wait
                )
                if attempt < 3:
                    await asyncio.sleep(wait)

        return None

    # ── 메인 scrape() ─────────────────────────────────────────────────────

    async def scrape(self) -> AsyncGenerator[Precedent, None]:
        """
        전체 형사 판례를 페이지 순환하며 Precedent 객체를 yield한다.

        체크포인트 resume 지원:
          - resume_checkpoint가 설정되면 해당 인덱스(0-based) 이후부터 재개.
        """
        await self._handle_initial_load()

        # resume 시작 인덱스 계산
        skip_count = 0
        if self.resume_checkpoint and self.resume_checkpoint.isdigit():
            skip_count = int(self.resume_checkpoint) + 1
            logger.info(
                "%s: 체크포인트에서 재개 — %d번째 항목부터 시작",
                self.name, skip_count
            )

        # 1페이지로 전체 건수 확인
        first_items, total = await self._fetch_list_via_browser(page_no=1)
        if total == 0 and not first_items:
            logger.error("%s: 목록 조회 실패 또는 결과 없음", self.name)
            return

        total_pages = max(1, -(-total // SCOURT_API_PAGE_SIZE))
        logger.info(
            "%s: 총 %d건 / %d페이지 (형사 판례)",
            self.name, total, total_pages
        )

        global_idx = 0

        for page in range(1, total_pages + 1):
            if page == 1:
                items = first_items
            else:
                await asyncio.sleep(SCOURT_API_DELAY_SEC)
                items, _ = await self._fetch_list_via_browser(page_no=page)

            if not items:
                logger.warning(
                    "%s: 페이지 %d/%d — 결과 없음, 건너뜀",
                    self.name, page, total_pages
                )
                continue

            logger.info(
                "%s: 페이지 %d/%d 처리 중 (%d건)",
                self.name, page, total_pages, len(items)
            )

            for item in items:
                if global_idx < skip_count:
                    global_idx += 1
                    continue

                prec = await self._build_precedent(item)
                if prec:
                    yield prec

                global_idx += 1
                await asyncio.sleep(SCOURT_DETAIL_DELAY_SEC)

        logger.info("%s: 수집 완료 — 총 %d항목 처리", self.name, global_idx)

    # ── Precedent 빌드 ────────────────────────────────────────────────────

    async def _build_precedent(self, item: dict) -> Precedent | None:
        """
        목록 항목의 jisCntntsSrno로 상세 API를 호출하여 Precedent를 생성한다.

        목록 API 응답 필드명 (브라우저 인터셉트 확인, 2026-03-08):
          - jisCntntsSrno: 판례 고유번호 (상세 API 키)
          - csNoLstCtt:    사건번호
          - csNmLstCtt:    사건명
          - cortNm:        법원명
          - prnjdgYmd:     선고일자 (YYYYMMDD)
          - jdcpctCdcsCdNm: 사건종류명 (예: "형사")
          - jdcpctSumrCtt: 판결 요약 (목록 미리보기)
        """
        jis_srno = str(item.get("jisCntntsSrno", "")).strip()
        case_no = (item.get("csNoLstCtt") or item.get("caseNo", "")).strip()
        case_name = (item.get("csNmLstCtt") or item.get("jdcpctTitl", "")).strip()
        court = (item.get("cortNm") or item.get("courtNm", "대법원")).strip()
        case_type = item.get("jdcpctCdcsCdNm", "형사").strip()
        raw_date = item.get("prnjdgYmd") or item.get("jdmntDt", "")

        if not jis_srno:
            logger.warning("%s: jisCntntsSrno 없음 — 건너뜀", self.name)
            return None

        # 2차 방어 필터
        if not _is_criminal(case_type, case_no):
            logger.debug(
                "%s: 비형사 건 제외 (종류=%s, 번호=%s)",
                self.name, case_type, case_no
            )
            return None

        # 상세 본문 조회
        detail = await self._fetch_detail_via_browser(jis_srno)

        if not detail:
            logger.warning(
                "%s: 상세 조회 실패, 목록 요약으로 부분 저장 (srno=%s)",
                self.name, jis_srno
            )
            # jdcpctSumrCtt를 요약 대신 사용
            summary_html = item.get("jdcpctSumrCtt", "")
            summary = BeautifulSoup(summary_html, "lxml").get_text() if summary_html else None

            return Precedent(
                source_key=SOURCE_KEY,
                case_number=case_no or f"SRNO_{jis_srno}",
                case_name=case_name or None,
                court=court,
                decision_date=_parse_date(raw_date),
                case_type=case_type,
                summary=summary,
            )

        # 상세 HTML에서 판결 구조 추출
        html_body = detail.get("orgdocXmlCtt", "")

        holding = _extract_section_html(html_body, "판시사항")
        summary = _extract_section_html(html_body, "판결요지")
        full_text = (
            _extract_section_html(html_body, "전 문")
            or _extract_section_html(html_body, "이       유")
            or _extract_section_html(html_body, "이유")
        )
        ref_statutes_raw = _extract_section_html(html_body, "참조조문") or ""
        ref_cases_raw = _extract_section_html(html_body, "참조판례") or ""

        ref_statutes = [s.strip() for s in re.split(r"[,\n]", ref_statutes_raw) if s.strip()]
        ref_cases = [s.strip() for s in re.split(r"[,\n]", ref_cases_raw) if s.strip()]

        final_case_no = case_no or f"SRNO_{jis_srno}"

        try:
            return Precedent(
                source_key=SOURCE_KEY,
                case_number=final_case_no,
                case_name=case_name or None,
                court=court,
                decision_date=_parse_date(raw_date),
                case_type=case_type,
                holding=holding,
                summary=summary,
                full_text=full_text,
                referenced_statutes=ref_statutes,
                referenced_cases=ref_cases,
            )
        except Exception as exc:
            logger.warning(
                "%s: Precedent 생성 실패 (srno=%s): %s", self.name, jis_srno, exc
            )
            return None
