"""Central configuration: URLs, CSS selectors, constants, paths."""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "law.db"
EXPORT_DIR = DATA_DIR / "export"

# ── Scraping defaults ──────────────────────────────────────────────────────
DEFAULT_TIMEOUT_MS = 30_000
NAVIGATION_DELAY_SEC = 1.0
SCOURT_DELAY_SEC = 2.0
MAX_RETRIES = 3
HEADLESS = True  # Hidden browser for stability

# ── Export ─────────────────────────────────────────────────────────────────
BUNDLE_MAX_BYTES = 4_000_000  # ~4 MB per bundle file

BUNDLE_PREFIX_MAP = {
    "statutes": "BUNDLE_STATUTE",
    "admin_rules": "BUNDLE_ADMIN_RULE",
    "precedents": "BUNDLE_PRECEDENT",
}

# ── Source Configuration Model ───────────────────────────────────────────
class SourceConfig(BaseModel):
    """Configuration for a single legal data source."""
    name: str              # User-friendly name
    url: str               # Target URL (direct access where possible)
    scraper: str           # Scraper type key (e.g., "law_statute")
    table: str             # Database table name
    enabled: bool = True   # UI visibility

# ── Source registry ────────────────────────────────────────────────────────
SOURCES: dict[str, SourceConfig] = {
    "police_investigation_rules": SourceConfig(
        name="경찰수사규칙",
        url="https://www.law.go.kr/LSW/lsInfoP.do?lsId=013976",
        scraper="law_statute",
        table="statutes",
    ),
    "crime_investigation_rules": SourceConfig(
        name="범죄수사규칙",
        url="https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000272092",
        scraper="law_admin_rule",
        table="admin_rules",
    ),
    "criminal_procedure_act": SourceConfig(
        name="형사소송법",
        url="https://www.law.go.kr/LSW/lsInfoP.do?lsId=001671",
        scraper="law_statute",
        table="statutes",
    ),
    "investigation_standards": SourceConfig(
        name="검사와 사법경찰관의 상호협력과 일반적 수사준칙에 관한 규정(수사준칙)",
        url="https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=255305",
        scraper="law_statute",
        table="statutes",
    ),
    "criminal_act": SourceConfig(
        name="형법",
        url="https://law.go.kr/LSW/lsInfoP.do?lsId=001692&ancYnChk=0#0000",
        scraper="law_statute",
        table="statutes",
    ),
    "scourt_criminal_precedent": SourceConfig(
        name="대법원 사법정보공개포털 형사판례",
        url="https://portal.scourt.go.kr/pgp/index.on?m=PGP1011M01&l=N&c=900",
        scraper="scourt_precedent",
        table="precedents",
    ),
    "law_go_kr_precedent": SourceConfig(
        name="법제처 국가법령정보센터 판례",
        url="https://www.law.go.kr/precSc.do?menuId=7&subMenuId=47&tabMenuId=213&query=",
        scraper="law_go_kr_precedent",
        table="precedents",
    ),
    "law_go_kr_constitutional": SourceConfig(
        name="헌법재판소 결정례",
        url="https://www.law.go.kr/detcSc.do?menuId=7&subMenuId=49&tabMenuId=225&query=",
        scraper="law_go_kr_constitutional",
        table="precedents",
    ),
    "law_go_kr_interpretation": SourceConfig(
        name="법제처 해석례",
        url="https://www.law.go.kr/expcSc.do?menuId=7&subMenuId=51&tabMenuId=237&query=",
        scraper="law_go_kr_interpretation",
        table="precedents",
    ),
    "law_go_kr_admin_appeal": SourceConfig(
        name="행정심판 재결례",
        url="https://www.law.go.kr/allDeccSc.do?menuId=7&subMenuId=53&tabMenuId=249&query=",
        scraper="law_go_kr_admin_appeal",
        table="precedents",
    ),
}

# ── CSS Selectors: law.go.kr ──────────────────────────────────────────────
SELECTORS_LAW = {
    # Statute pages (lsInfoP.do)
    "law_body": "#lsBdy",
    "body_content": "#bodyContent",
    "left_tree": "#leftContent",
    "article_tree_item": ".dep_in",
    # Precedent search (precSc.do)
    "search_result_item": "[id^='list']",
    "total_count": ".srch_total",
    "pagination_next": ".paging .next",
    # Admin rule pages (admRulInfoP.do)
    "admin_body_content": "#bodyContent",
}

# ── CSS Selectors: scourt portal (WebSquare5 framework) ───────────────────
# IDs confirmed via live DOM inspection (2026-03-07)
SELECTORS_SCOURT = {
    "search_input": "#mf_mainFrame_ibx_srchwd",
    "search_button": "#mf_mainFrame_btn_srch",
    "result_list": "#mf_mainFrame_gen_cntntsList",
    "result_item": "[id*='gen_cntntsList'][id*='anc_title']",
    "pagination": None,  # WebSquare5 pagination — handled via JS click
}

# ── 사법정보공개포털 API 상수 ──────────────────────────────────────────────
# 형사 사건종류코드 (jdcpctCdcsCd): "02" = 형사
SCOURT_CRIMINAL_CASE_CODE = "02"
# 한 페이지당 조회 건수 (최대 100)
SCOURT_API_PAGE_SIZE = 100
# API 요청 간 딜레이 (서버 부하 방지, 초)
SCOURT_API_DELAY_SEC = 0.5
# 상세 본문 조회 딜레이 (초)
SCOURT_DETAIL_DELAY_SEC = 0.3
# WebSquare5 requires ~15s for full JS initialization (브라우저 fallback용, 미사용)
SCOURT_INIT_WAIT_SEC = 15
