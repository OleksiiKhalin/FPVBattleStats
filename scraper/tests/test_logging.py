import logging
import shutil
import uuid
from datetime import date
from pathlib import Path

from scraper.app.domain import ParsedDayPayload
from scraper.app.logging import configure_logging
from scraper.app.services.persistence import ScrapePersistenceService


class _UnusedUnitOfWork:
    pass


def test_persist_day_warns_and_skips_when_results_are_empty(caplog) -> None:
    service = ScrapePersistenceService(_UnusedUnitOfWork())  # type: ignore[arg-type]
    payload = ParsedDayPayload(
        date=date(2026, 7, 2),
        race_class="open",
        season="2026-07",
        track="Unknown track",
        quad_of_the_day=None,
        results=[],
        season_leaderboard=[],
        source="html",
    )

    with caplog.at_level(logging.WARNING):
        persisted = service.persist_day(payload)

    assert persisted is False
    assert "No daily results parsed for open 2026-07-02" in caplog.text


def test_configure_logging_splits_output_files() -> None:
    log_dir = Path("data") / "test-logs" / str(uuid.uuid4())
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_logging(log_dir=log_dir)
        logger = logging.getLogger("scraper.tests.logging")

        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")

        info_log = (log_dir / "info.log").read_text(encoding="utf-8")
        warning_log = (log_dir / "warning.log").read_text(encoding="utf-8")
        error_log = (log_dir / "error.log").read_text(encoding="utf-8")

        assert "info message" in info_log
        assert "warning message" not in info_log
        assert "error message" not in info_log

        assert "warning message" in warning_log
        assert "error message" not in warning_log

        assert "error message" in error_log
    finally:
        logging.shutdown()
        shutil.rmtree(log_dir, ignore_errors=True)
