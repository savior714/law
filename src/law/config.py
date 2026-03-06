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
HEADLESS = False  # GUI mode by default

# ── Export ─────────────────────────────────────────────────────────────────
BUNDLE_MAX_BYTES = 4_000_000  # ~4 MB per bundle file

BUNDLE_PREFIX_MAP = {
    "statutes": "BUNDLE_STATUTE",
    "admin_rules": "BUNDLE_ADMIN_RULE",
    "precedents": "BUNDLE_PRECEDENT",
}

# ── Source registry ────────────────────────────────────────────────────────
SOURCES: dict[str, dict] = {
    "crime_investigation_rules": {
        "name": "범죄수사규칙",
        "url": "https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000272092&chrClsCd=010201",
        "scraper": "law_admin_rule",
        "table": "admin_rules",
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
        "url": "https://www.law.go.kr/precSc.do",
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

# ── CSS Selectors: scourt portal ──────────────────────────────────────────
SELECTORS_SCOURT = {
    "search_input": "#search_txt",
    "search_button": "#btn_search",
    "result_list": ".result_list",
    "result_item": ".result_list li",
    "pagination": ".pagination",
}
