"""Korean text cleaning utilities."""

from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    """Normalize line endings and collapse excessive blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip spaces from Each line to allow \n\n matching
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_html_text(text: str) -> str:
    """Clean text extracted from HTML while preserving legal notation and structure.

    This version flows fragmented lines (often caused by inline tags like <a> or <span>) 
    back into a single line unless a structural marker (항, 호, 목) is encountered.
    """
    if not text:
        return ""

    # Normalize line endings and collapse excessive spaces within lines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    
    # Identify lines that signify a new structural element in Korean law
    # - Paragraphs (항): ①, ②...
    # - Items (호): 1., 2...
    # - Points (목): 가., 나...
    # - Article references: 제10조...
    struct_marker = re.compile(
        r'^('
        r'[\u2460-\u2473]|'      # ① to ⑳
        r'\d+[.\)]|'             # 1. or 1)
        r'[가-하][.\)]|'         # 가. or 가)
        r'[*•·-]\s*|'            # Bullets
        r'제\d+조|'               # Article marker
        r'【|\[|＜|※|▲|■'         # Legal headers/special marks
        r')'
    )

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    flowed_lines = []
    for line in lines:
        if not flowed_lines:
            flowed_lines.append(line)
        else:
            # If line starts with a structural marker, start a new line
            if struct_marker.match(line):
                flowed_lines.append(line)
            else:
                # Join with previous line using a single space
                flowed_lines[-1] = f"{flowed_lines[-1]} {line}"

    # Final join and whitespace cleanup
    result = "\n".join(flowed_lines)
    result = re.sub(r" +", " ", result)
    return normalize_whitespace(result)
