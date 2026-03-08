"""사법정보공개포털(portal.scourt.go.kr) 형사 판례 스크래퍼.

[아키텍처 변경 알림 — 2026-03-08]
포털의 강력한 WAF 및 세션 검증(500 에러)으로 인해, 순수 API 기반 수집에서
UI 상호작용 기반 하이브리드 수집 방식으로 전환하였습니다.

[핵심 로직]
1. Playwright로 포털 접속 후 '형사' 카테고리를 클릭하여 세션을 활성화합니다.
2. UI의 결과 목록(DOM)에서 각 항목의 고유 번호(jisCntntsSrno)를 추출합니다.
3. 활성화된 브라우저 세션 내에서 JavaScript fetch()를 호출하여 상세 본문만 API로 가져옵니다.
   (목록은 UI로, 상세는 API로 가져오는 하이브리드 방식)
4. UI의 페이지네이션 버튼('.w2pageList_col_next')을 클릭하여 다음 결과로 이동합니다.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from datetime import date

from bs4 import BeautifulSoup

from law.config import (
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

# ── Selectors (Verified 2026-03-08) ──────────────────────────────────────
_SEL_TREE_CASE_TYPE = "#mf_mainFrame_trv_jdcpctGrp_label_7"  # 사건종류
_SEL_TREE_CRIMINAL = "#mf_mainFrame_trv_jdcpctGrp_label_9"   # 형사
_SEL_TOTAL_COUNT = "#mf_mainFrame_spn_totalCount"
_SEL_LIST_ITEMS = "a[id*='gen_cntntsList_'][id$='btn_jisCsNoCsNm']"
_SEL_PAGING_NEXT = ".w2pageList_col_next"
_SEL_LOADING_LAYER = "#___processbar_res"

# ── Detail API Script (브라우저 컨텍스트용) ─────────────────────────────
_DETAIL_FETCH_JS = """
async (apiPath, jisSrno) => {
    const payload = {
        "dma_searchParam": {
            "jisCntntsSrno": jisSrno,
            "srchwd": "*",
            "csNoLstCtt": "",
            "cortNm": "",
            "adjdTypNm": "",
            "jdcpctBrncNo": "",
            "jdcpctGrCd": "A1|A2|C|D3|H|H2|W2|W5|J1",
            "chnchrYn": "N",
            "systmNm": "PGP"
        }
    };
    const resp = await fetch(apiPath, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json;charset=UTF-8',
            'sc-pgmid': 'PGP1011M04',
            'submissionid': 'mf_wfm_pgpDtlMain_sbm_selectJdcpctCtxt',
        },
        body: JSON.stringify(payload)
    });
    if (!resp.ok) return { status: resp.status, data: null };
    const data = await resp.json();
    return { status: resp.status, data: data };
}
"""


def _parse_date(text: str | None) -> date | None:
    """날짜 파싱 (YYYY.MM.DD 등)."""
    if not text:
        return None
    m = re.search(r"(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _extract_section_html(html: str, marker: str) -> str | None:
    """HTML 본문에서 특정 마커 섹션 추출."""
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    full = soup.get_text("\n")
    pattern = rf"【{re.escape(marker)}】(.*?)(?=【[^】]+】|$)"
    m = re.search(pattern, full, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


class ScourtPrecedentScraper(BaseScraper):
    """사법정보공개포털 형사 판례 스크래퍼 (UI + API 하이브리드)."""

    def __init__(self) -> None:
        super().__init__()
        src = SOURCES[SOURCE_KEY]
        self.name = SOURCE_KEY
        self.source_url = src.url

    async def _handle_initial_load(self) -> None:
        """포털 접속 및 '형사' 필터 활성화."""
        await self.safe_navigate(self.source_url)
        logger.info("%s: WebSquare5 초기화 대기 (%ds)...", self.name, SCOURT_INIT_WAIT_SEC)
        await asyncio.sleep(SCOURT_INIT_WAIT_SEC)

        # 1. 사건종류 그룹 확장 (필요 시)
        try:
            await self.page.click(_SEL_TREE_CASE_TYPE, timeout=5000)
            await asyncio.sleep(1)
        except Exception:
            pass

        # 2. '형사' 카테고리 클릭
        logger.info("%s: '형사' 카테고리 클릭 및 결과 로딩...", self.name)
        await self.page.click(_SEL_TREE_CRIMINAL)
        await self._wait_for_loading()

    async def _wait_for_loading(self, timeout_sec: int = 15) -> None:
        """WebSquare5 로딩 레이어가 사라질 때까지 대기."""
        # 로딩바가 나타날 때까지 아주 짧게 대기
        await asyncio.sleep(0.5)
        try:
            # 로딩바가 'none'이 될 때까지 대기
            await self.page.wait_for_selector(
                _SEL_LOADING_LAYER,
                state="hidden",
                timeout=timeout_sec * 1000
            )
        except Exception:
            logger.debug("%s: 로딩바 대기 타임아웃/생략", self.name)
        await asyncio.sleep(1)

    async def _get_total_count(self) -> int:
        """UI에서 총 건수를 추출한다."""
        text = await self.page.inner_text(_SEL_TOTAL_COUNT)
        clean = re.sub(r"[^\d]", "", text)
        return int(clean) if clean else 0

    async def scrape(self) -> AsyncGenerator[Precedent, None]:
        """UI와 API를 조합하여 형사 판례를 수집한다."""
        await self._handle_initial_load()

        total = await self._get_total_count()
        if total == 0:
            logger.error("%s: 검색 결과가 0건입니다. 초기화 실패 가능성.", self.name)
            return

        logger.info("%s: 총 %d건 수집 시작", self.name, total)

        skip_count = 0
        if self.resume_checkpoint and self.resume_checkpoint.isdigit():
            skip_count = int(self.resume_checkpoint) + 1
            logger.info("%s: 체크포인트(%d) 이후부터 재개", self.name, skip_count)

        global_idx = 0
        current_page = 1

        while global_idx < total:
            # 현재 페이지 항목들 추출
            items = await self.page.query_selector_all(_SEL_LIST_ITEMS)
            if not items:
                logger.warning("%s: 페이지 %d 로드 실패 — 종료", self.name, current_page)
                break

            logger.info("%s: 페이지 %d 처리 중 (%d건 발견)", self.name, current_page, len(items))

            for item_el in items:
                if global_idx < skip_count:
                    global_idx += 1
                    continue

                # 1. 항목 데이터 추출
                full_text = await item_el.inner_text()
                # ID에서 jisCntntsSrno 추출 (예: ...gen_cntntsList_0_btn_jisCsNoCsNm)
                raw_id = await item_el.get_attribute("id")
                # WebSquare 데이터 맵에서 실제 SRNO를 가져오는 게 더 안전함
                idx_match = re.search(r"gen_cntntsList_(\d+)_", raw_id)
                if not idx_match:
                    global_idx += 1
                    continue
                
                row_idx = idx_match.group(1)
                jis_srno = await self.page.evaluate(
                    f"mf_mainFrame_dlt_jdcpctRslt.getCellData({row_idx}, 'jisCntntsSrno')"
                )

                # 2. 상세 정보 API 호출 (브라우저 내 fetch)
                prec = await self._build_precedent(jis_srno, full_text)
                if prec:
                    yield prec

                global_idx += 1
                await asyncio.sleep(SCOURT_DETAIL_DELAY_SEC)

            # 3. 다음 페이지 이동
            next_btn = await self.page.query_selector(_SEL_PAGING_NEXT)
            if next_btn and await next_btn.is_visible() and global_idx < total:
                logger.info("%s: 다음 페이지로 이동...", self.name)
                await next_btn.click()
                current_page += 1
                await self._wait_for_loading()
            else:
                break

        logger.info("%s: 수집 완료 (총 %d건)", self.name, global_idx)

    async def _build_precedent(self, jis_srno: str, list_text: str) -> Precedent | None:
        """상세 API 호출 및 결과 파싱."""
        # 목록 텍스트 예시: "대법원 2025.12.11 선고 2023두39601 판결 [정보삭제요청처분취소]"
        # 정규식 개선: 공백 유연성 및 사건명 대괄호 미존재 대비
        court = "대법원"
        case_no = f"SRNO_{jis_srno}"
        raw_date = None
        case_name = None

        m = re.search(
            r"([^\s]+)\s+([\d.]+)\s+선고\s+([^\s]+)\s+판결(?:\s+\[?(.*?)\]?)?$",
            list_text.strip()
        )
        if m:
            court = m.group(1)
            raw_date = m.group(2)
            case_no = m.group(3)
            case_name = m.group(4) if m.group(4) else None
        else:
            # 보수적 파싱 실패 시 전체 텍스트 보존
            logger.debug("%s: 목록 텍스트 파싱 실패 — %s", self.name, list_text)
            case_name = list_text

        # 상세 API 호출
        result = await self.page.evaluate(
            _DETAIL_FETCH_JS,
            ["/pgp/pgp1011/selectJdcpctCtxt.on", jis_srno]
        )
        
        status = result.get("status")
        data = (result.get("data") or {}).get("data", {})
        detail = data.get("dma_jdcpctCtxt", {})
        html_body = detail.get("orgdocXmlCtt", "")

        if status != 200 or not html_body:
            # 실패 시 목록 정보만으로 생성
            return Precedent(
                source_key=SOURCE_KEY,
                case_number=case_no,
                case_name=case_name,
                court=court,
                decision_date=_parse_date(raw_date),
                case_type="형사",
            )

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

        return Precedent(
            source_key=SOURCE_KEY,
            case_number=case_no,
            case_name=case_name,
            court=court,
            decision_date=_parse_date(raw_date),
            case_type="형사",
            holding=holding,
            summary=summary,
            full_text=full_text,
            referenced_statutes=ref_statutes,
            referenced_cases=ref_cases,
        )
