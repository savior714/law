"""Central configuration: URLs, CSS selectors, constants, paths."""

from __future__ import annotations

from pathlib import Path

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

# ── Source registry ────────────────────────────────────────────────────────
SOURCES: dict[str, dict] = {
    "police_investigation_rules": {
        "name": "경찰수사규칙",
        "url": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=279215",
        "scraper": "law_statute",
        "table": "statutes",
    },
    "police_duties_act": {
        "name": "경찰관직무집행법",
        "url": "https://www.law.go.kr/LSW/lsInfoP.do?lsId=013976",
        "scraper": "law_statute",
        "table": "statutes",
    },
    "criminal_procedure_act": {
        "name": "형사소송법",
        "url": "https://www.law.go.kr/LSW/lsInfoP.do?lsId=001671&ancYnChk=0",
        "scraper": "law_statute",
        "table": "statutes",
    },
    "criminal_act": {
        "name": "형법",
        "url": "https://www.law.go.kr/lsSc.do?query=%ED%98%95%EB%B2%95",
        "scraper": "law_statute",
        "table": "statutes",
    },
    "scourt_criminal_precedent": {
        "name": "대법원 형사판례",
        "url": "https://portal.scourt.go.kr/pgp/index.on?m=PGP1011M01&l=N&c=900",
        "scraper": "scourt_precedent",
        "table": "precedents",
    },
    "law_go_kr_precedent": {
        "name": "판례검색",
        # menuId/subMenuId/tabMenuId params required for the search form to render correctly.
        # Searching with keyword "형사" filters to court precedents (precView links);
        # the default landing without search shows only tax precedents.
        "url": "https://www.law.go.kr/precSc.do?menuId=7&subMenuId=47&tabMenuId=213&eventGubun=",
        "scraper": "law_precedent",
        "table": "precedents",
    },
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

# WebSquare5 requires ~15s for full JS initialization before any interaction
SCOURT_INIT_WAIT_SEC = 15
