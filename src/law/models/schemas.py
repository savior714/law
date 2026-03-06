"""Pydantic data models for scraped legal records."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator


class Attachment(BaseModel):
    """Metadata for a linked file attachment (별표/서식)."""

    name: str
    pdf_url: str | None = None
    hwp_url: str | None = None
    has_pdf_priority: bool = False


class StatuteArticle(BaseModel):
    """A single article from a statute (형법, 형사소송법, 경찰관직무집행법)."""

    source_key: str
    law_name: str
    part: str | None = None
    chapter: str | None = None
    section: str | None = None
    subsection: str | None = None
    article_number: str
    article_title: str | None = None
    content: str
    attachments: list[Attachment] = []

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v


class AdminRuleArticle(BaseModel):
    """A single article from an administrative rule (범죄수사규칙)."""

    source_key: str = "crime_investigation_rules"
    rule_name: str
    part: str | None = None
    chapter: str | None = None
    section: str | None = None
    article_number: str
    article_title: str | None = None
    content: str
    attachments: list[Attachment] = []

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v


class Precedent(BaseModel):
    """A court precedent (판례) from law.go.kr or scourt portal."""

    source_key: str
    case_number: str
    case_name: str | None = None
    court: str
    decision_date: date | None = None
    case_type: str = "형사"
    holding: str | None = None
    summary: str | None = None
    full_text: str | None = None
    referenced_statutes: list[str] = []
    referenced_cases: list[str] = []

    @field_validator("case_number")
    @classmethod
    def case_number_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("case_number must not be empty")
        return v
