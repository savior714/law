"""Korean text cleaning utilities."""

from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    """Normalize line endings and collapse excessive blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Preserve leading indentation but strip trailing spaces
    text = "\n".join(line.rstrip() for line in text.split("\n"))
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
    # - Items (호): 1., 2... (strictly formatted)
    # - Points (목): 가., 나... (strictly formatted)
    # - Article start: 제10조(제목) -> Only if followed by parenthesized title
    # - Addendum marker: [부칙]
    struct_marker = re.compile(
        r'^('
        r'[\u2460-\u2473]|'                  # ① to ⑳
        r'\d+\.\s*|'                         # 1., 2.
        r'[가-하]\.\s*|'                     # 가., 나.
        r'[*•·-]\s+|'                        # Bullets (with space)
        r'제\d+조(?:의\d+)?\s*[\(（]|'        # Article header with title: 제1조(목적)
        r'제\d+관|'                           # Subsection header
        r'제\d+절|'                           # Section header
        r'제\d+장|'                           # Chapter header
        r'【|\[|＜|※|▲|■'                     # Legal headers/special marks
        r')'
    )

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    flowed_lines = []
    for line in lines:
        # Check if current line starts with a structural marker
        m = struct_marker.match(line)
        
        if not flowed_lines:
            flowed_lines.append(line)
        elif m:
            # Precedent markers like [1], [2] should be preserved as 
            # new blocks even if the previous line ends with a connector.
            prev_line = flowed_lines[-1].strip()
            is_article_header = "제" in m.group(1) and "(" in m.group(1)
            is_connector = re.search(r'(법|령|칙|항|호|목|절|장|편|관|등)$', prev_line)
            is_precedent_marker = bool(re.match(r'^\[\d+\]', m.group(1)))
            
            if is_connector and not is_article_header and not is_precedent_marker:
                flowed_lines[-1] = f"{prev_line} {line}"
            else:
                # New structural block
                marker = m.group(1).replace(" ", "")  # Tight match logic for indent check
                indent = ""
                if re.match(r"^[\u2460-\u2473]", marker):  # Paragraph (항: ①, ②)
                    indent = "" # Paragraphs usually not indented in our flow
                elif re.match(r"^\d+\.", marker):  # Item (호: 1., 2.)
                    indent = "  "
                elif re.match(r"^[가-하]\.", marker):  # Point (목: 가., 나.)
                    indent = "    "
                
                flowed_lines.append(indent + line)
        else:
            # Not a marker, flow into previous line
            prev_line = flowed_lines[-1].strip()
            flowed_lines[-1] = f"{prev_line} {line}"

    # Final join.
    result = "\n".join(flowed_lines)
    return normalize_whitespace(result)
