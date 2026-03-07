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
    """Clean text extracted from HTML while preserving legal notation.

    Keeps circled numbers (①②③), section marks (§), and other legal symbols.
    """
    # collapse multiple spaces (but not newlines)
    text = re.sub(r"[^\S\n]+", " ", text)
    return normalize_whitespace(text)
