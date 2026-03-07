"""Textual TUI application entry point."""

from __future__ import annotations

import asyncio
import logging

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, ProgressBar, RichLog, SelectionList, Static

from law.config import SOURCES
from law.db.repository import Repository
from law.db.schema import init_db
from law.export.builder import build_dataset
from law.scrapers.law_admin_rule import AdminRuleScraper
from law.scrapers.law_precedent import LawPrecedentScraper
from law.scrapers.law_statute import StatuteScraper
from law.scrapers.scourt_precedent import ScourtPrecedentScraper

logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "law_statute": StatuteScraper,
    "law_admin_rule": AdminRuleScraper,
    "law_precedent": LawPrecedentScraper,
    "scourt_precedent": ScourtPrecedentScraper,
}


class LawScraperApp(App):
    """Korean Legal Data Scraper TUI."""

    TITLE = "Korean Legal Data Scraper"
    CSS = """
    #source_list { height: 10; margin: 1 2; }
    #action_bar { layout: horizontal; height: 3; margin: 0 2; }
    #action_bar Button { margin: 0 1; }
    #log { height: 1fr; margin: 1 2; border: solid green; }
    #progress_area { height: 3; margin: 0 2; }
    #status { margin: 0 2; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(" [1] Scrape Sources", id="label_scrape")
        yield SelectionList[str](
            *[(info["name"], key) for key, info in SOURCES.items()],
            id="source_list",
        )
        yield Vertical(
            Button("Start Scraping", id="btn_scrape", variant="primary"),
            Button("Select All", id="btn_select_all"),
            Button("Build Dataset", id="btn_build", variant="success"),
            id="action_bar",
        )
        yield Static("", id="status")
        yield ProgressBar(id="progress", total=100, show_eta=False)
        yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._log("App started. Select sources and press [b]Start Scraping[/b].")

    def _log(self, message: str) -> None:
        log_widget = self.query_one("#log", RichLog)
        log_widget.write(message)

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    def _set_progress(self, value: float) -> None:
        self.query_one("#progress", ProgressBar).update(progress=value)

    # ── Button handlers ────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_scrape":
            self._start_scraping()
        elif event.button.id == "btn_select_all":
            selection = self.query_one("#source_list", SelectionList)
            selection.select_all()
        elif event.button.id == "btn_build":
            self._start_build()

    # ── Scraping worker ────────────────────────────────────────────────

    @work(thread=False)
    async def _start_scraping(self) -> None:
        selection = self.query_one("#source_list", SelectionList)
        selected_keys = list(selection.selected)

        if not selected_keys:
            self._log("[red]No sources selected.[/red]")
            return

        self._log("[dim]Connecting to database...[/dim]")
        await init_db()
        repo = Repository()
        await repo.connect()

        try:
            total_sources = len(selected_keys)

            for idx, source_key in enumerate(selected_keys):
                src = SOURCES[source_key]
                self._log(f"\n[bold blue]>>> Scraping: {src['name']}[/bold blue]")
                self._set_status(f"Scraping {src['name']} ({idx + 1}/{total_sources})")
                self._set_progress((idx / total_sources) * 100)

                run_id = await repo.start_run(source_key)
                scraper = self._create_scraper(source_key)
                if scraper is None:
                    self._log(f"[red]Unknown scraper for {source_key}[/red]")
                    continue

                count = 0
                error_msg = None

                try:
                    self._log(f"  [cyan]Preparing browser for {src['name']}...[/cyan]")
                    await scraper.init_browser()
                    
                    self._log(f"  [cyan]Navigating & Extraction started...[/cyan]")
                    async for record in scraper.scrape():
                        if src["table"] == "statutes":
                            await repo.upsert_statute(record, src["url"], run_id)
                        elif src["table"] == "admin_rules":
                            await repo.upsert_admin_rule(record, src["url"], run_id)
                        elif src["table"] == "precedents":
                            await repo.upsert_precedent(record, src["url"], run_id)
                        count += 1

                        if count % 10 == 0:
                            self._log(f"  ... {count} records")

                except Exception as e:
                    error_msg = str(e)
                    if "Target page, context or browser has been closed" in error_msg:
                        self._log("[red]Error: Browser disconnected or closed unexpectedly.[/red]")
                    else:
                        self._log(f"[red]Error: {error_msg}[/red]")
                    logger.exception("Scraping error for %s", source_key)
                finally:
                    await scraper.close()
                    await repo.finish_run(run_id, total=count, error=error_msg)

                self._log(f"[green]{src['name']}: {count} records saved[/green]")

            self._set_progress(100)
            self._set_status("Scraping complete")
            self._log("\n[bold green]All scraping tasks finished.[/bold green]")

        finally:
            await repo.close()

    def _create_scraper(self, source_key: str):
        src = SOURCES[source_key]
        scraper_type = src["scraper"]

        if scraper_type == "law_statute":
            return StatuteScraper(source_key)
        elif scraper_type == "law_admin_rule":
            return AdminRuleScraper(source_key)
        elif scraper_type == "law_precedent":
            return LawPrecedentScraper()
        elif scraper_type == "scourt_precedent":
            return ScourtPrecedentScraper()
        return None

    # ── Build worker ───────────────────────────────────────────────────

    @work(thread=False)
    async def _start_build(self) -> None:
        self._log("\n[bold blue]>>> Building NotebookLM dataset...[/bold blue]")
        self._set_status("Building dataset...")
        self._set_progress(0)

        await init_db()
        repo = Repository()
        await repo.connect()

        try:
            counts = await build_dataset(repo)
            total = sum(counts.values())
            self._set_progress(100)
            self._set_status("Dataset build complete")
            self._log(f"[green]Dataset built: {total} total records[/green]")
            for table, n in counts.items():
                self._log(f"  {table}: {n} records")
            self._log(f"[green]Output: data/export/[/green]")
        except Exception as e:
            self._log(f"[red]Build error: {e}[/red]")
            logger.exception("Build error")
        finally:
            await repo.close()


def main() -> None:
    # Ensure logs directory exists
    from pathlib import Path
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        filename=log_dir / "app.log",
        filemode="a",
        encoding="utf-8",
    )
    app = LawScraperApp()
    app.run()


if __name__ == "__main__":
    main()
