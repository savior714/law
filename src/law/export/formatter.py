"""Record formatting for NotebookLM-compatible text output."""

from __future__ import annotations

import re
from typing import Any


def format_statute(row: Any) -> str:
    """Format a statute row into a text block for a bundle file."""
    # Build clean hierarchy path (excluding the article itself which is in the title)
    hierarchy_parts = [p for p in [row["part"], row["chapter"], row["section"], row["subsection"]] if p]
    hierarchy = " > ".join(hierarchy_parts)

    law_name = f"[{row['law_name']}]"
    title = f"({row['article_title']})" if row['article_title'] else ""
    # Header: [Law Name] Hierarchy > Article Num (Title)
    prefix = f"{hierarchy} > " if hierarchy else ""
    header = f"{law_name} {prefix}{row['article_number']} {title}".strip()
    header = re.sub(r"\s+>\s+", " > ", header)

    # Metadata section for better AI context
    metadata = [f"- 법령명: {row['law_name']}"]
    if hierarchy:
        metadata.append(f"- 체계: {hierarchy}")
    metadata.append(f"- 조문: {row['article_number']} {title}")
    
    meta_block = "\n".join(metadata)

    return f"---\n## {header}\n\n{meta_block}\n\n{row['content']}\n"


def format_admin_rule(row: Any) -> str:
    """Format an admin rule row into a text block for a bundle file."""
    hierarchy_parts = [p for p in [row["part"], row["chapter"], row["section"]] if p]
    hierarchy = " > ".join(hierarchy_parts)

    rule_name = f"[{row['rule_name']}]"
    title = f"({row['article_title']})" if row['article_title'] else ""
    prefix = f"{hierarchy} > " if hierarchy else ""
    header = f"{rule_name} {prefix}{row['article_number']} {title}".strip()
    header = re.sub(r"\s+>\s+", " > ", header)

    # Metadata section for better AI context
    metadata = [f"- 규정이름: {row['rule_name']}"]
    if hierarchy:
        metadata.append(f"- 체계: {hierarchy}")
    metadata.append(f"- 조문: {row['article_number']} {title}")
    
    meta_block = "\n".join(metadata)

    return f"---\n## {header}\n\n{meta_block}\n\n{row['content']}\n"


def format_precedent(row: Any) -> str:
    """Format a precedent row into a text block for a bundle file."""
    date_str = row["decision_date"] or "날짜 미상"
    case_name = (row["case_name"] or "").strip()

    # 공보(Official Gazette) 인용구가 마지막에 있는 경우 날짜와 결합하여 대괄호로 묶음
    # 예: "사건명 [공2026상,358]" -> "사건명 [공2026상,358 / 2025-12-24]"
    # 스크래퍼 버그로 인해 대괄호가 일부 소실된 경우(공2026상,358)도 대응
    citation_match = re.search(r"^(.*?)\s*\[?(공\d+[상하],\s*\d+)\]?$", case_name)
    
    if citation_match:
        base_name = citation_match.group(1).strip()
        citation = citation_match.group(2).strip()
        header = f"[{row['court']} {row['case_number']}] {base_name} [{citation} / {date_str}]"
    else:
        header = f"[{row['court']} {row['case_number']}] {case_name} / {date_str}".strip()

    header = re.sub(r"\s+", " ", header) # Excessive space cleanup

    sections: list[str] = []
    if row["holding"]:
        sections.append(f"### 판시사항\n{row['holding']}")
    if row["summary"]:
        sections.append(f"### 판결요지\n{row['summary']}")
    if row["referenced_statutes"]:
        sections.append(f"### 참조조문\n{row['referenced_statutes']}")
    if row["referenced_cases"]:
        sections.append(f"### 참조판례\n{row['referenced_cases']}")
    if row["full_text"]:
        sections.append(f"### 전문\n{row['full_text']}")

    body = "\n\n".join(sections) if sections else "(내용 없음)"

    return f"---\n## {header}\n\n{body}\n"
