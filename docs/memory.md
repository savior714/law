# Memory Management Log

## 2026-03-07 01:07:55
- Task: Create `run.bat` for TUI execution via `uv run law`.
- Status: Initialized.
- Actions:
  - Checking codebase and missing `docs/memory.md`.
  - Initializing `docs/memory.md`.

- Actions:
  - Created un.bat for TUI execution via uv run law.

## 2026-03-07 03:45:00
- Task: 별지(별표/서식) 자료 수집 기능 추가.
- Status: Completed.
- Actions:
  - src/law/models/schemas.py: Attachment 모델 추가 및 StatuteArticle, AdminRuleArticle에 attachments 필드 추가.
  - src/law/db/schema.py: DB 테이블에 attachments 컬럼(JSON) 추가.
  - src/law/db/repository.py: attachments 저장 로직 반영.
  - src/law/scrapers/base.py: 공통 _scrape_attachments 메서드 구현 (PDF 우선, HWP만 있을 경우 경고 로그).
  - src/law/scrapers/law_statute.py & law_admin_rule.py: 스크래핑 루프에 별지 수집 로직 통합.
