from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fpvbattle_core.db.session import create_db_engine, create_session_factory, init_db
from fpvbattle_core.services.unit_of_work import SqlAlchemyUnitOfWork

from ..core.config import settings
from ..parsers.battle_page import parse_battle_page, parse_dashboard_json
from .http_client import BattleHttpClient
from .persistence import ScrapePersistenceService


class BattleScraperService:
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        engine = create_db_engine(settings.database_url)
        init_db(engine)
        session_factory = create_session_factory(engine)
        self._persistence = ScrapePersistenceService(SqlAlchemyUnitOfWork(session_factory))
        self._http = BattleHttpClient(
            timeout_seconds=settings.request_timeout_seconds,
            request_delay_seconds=settings.request_delay_seconds,
            request_jitter_seconds=settings.request_jitter_seconds,
            request_max_retries=settings.request_max_retries,
            request_backoff_seconds=settings.request_backoff_seconds,
        )

    def close(self) -> None:
        self._http.close()

    def sync_day(self, *, target_date: date, race_class: str) -> None:
        self._logger.info("Syncing %s day %s", race_class, target_date.isoformat())
        payload = self._fetch_day_payload(target_date=target_date, race_class=race_class)
        self._logger.info(
            "Parsed %s day %s from %s: results=%s season_rows=%s track=%s",
            race_class,
            target_date.isoformat(),
            payload.source,
            len(payload.results),
            len(payload.season_leaderboard),
            payload.track,
        )
        persisted = self._persistence.persist_day(payload)
        if not persisted:
            self._logger.warning("Skipped %s %s because no daily results were available.", race_class, target_date.isoformat())

    def sync_current_window(self) -> None:
        now = datetime.now(timezone.utc)
        target_date = now.date()
        if now.hour == 0 and now.minute < 10:
            target_date = (now - timedelta(days=1)).date()

        for race_class in ("open", "whoop"):
            self.sync_day(target_date=target_date, race_class=race_class)

    def sync_historical(self, *, end_date: date | None = None, skip_existing: bool = True) -> None:
        final_date = end_date or datetime.now(timezone.utc).date()
        current = settings.historical_start_date
        self._logger.info(
            "Starting historical sync from %s to %s (skip_existing=%s)",
            current.isoformat(),
            final_date.isoformat(),
            skip_existing,
        )
        while current <= final_date:
            for race_class in ("open", "whoop"):
                if skip_existing and self._persistence.has_day(target_date=current, race_class=race_class):
                    self._logger.info("Skipping existing %s day %s", race_class, current.isoformat())
                    continue
                self.sync_day(target_date=current, race_class=race_class)
            current += timedelta(days=1)
        self._logger.info("Historical sync finished")

    def _fetch_day_payload(self, *, target_date: date, race_class: str):
        dashboard_url = self._build_dashboard_api_url(target_date=target_date, race_class=race_class)
        try:
            response = self._http.fetch(dashboard_url)
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type or response.text.lstrip().startswith("{"):
                payload = parse_dashboard_json(
                    payload=json.loads(response.text),
                    target_date=target_date,
                    race_class=race_class,
                )
                if payload.results:
                    return payload
                self._logger.warning("Dashboard API returned no results for %s", dashboard_url)
        except Exception as exc:
            self._logger.warning("Dashboard API attempt failed for %s: %s", dashboard_url, exc)

        page_url = self._build_page_url(target_date=target_date, race_class=race_class)
        try:
            html = self._http.fetch_html(page_url)
            payload = parse_battle_page(html=html, target_date=target_date, race_class=race_class)
            if not payload.results and settings.dump_failed_pages:
                self._dump_failed_page(page_url=page_url, target_date=target_date, race_class=race_class, content=html)
            return payload
        except Exception:
            if settings.dump_failed_pages:
                self._dump_failed_page(page_url=page_url, target_date=target_date, race_class=race_class, content="")
            raise

    def _build_page_url(self, *, target_date: date, race_class: str) -> str:
        base_url = settings.whoop_base_url if race_class == "whoop" else settings.open_base_url
        return f"{base_url}?date={target_date.isoformat()}"

    def _build_dashboard_api_url(self, *, target_date: date, race_class: str) -> str:
        cup_id = "whoop-class" if race_class == "whoop" else "open-class"
        return f"{settings.api_base_url}/api/dashboard?cupId={cup_id}&date={target_date.isoformat()}"

    def _dump_failed_page(self, *, page_url: str, target_date: date, race_class: str, content: str) -> None:
        failed_dir = Path(__file__).resolve().parents[3] / "data" / "failed-pages"
        failed_dir.mkdir(parents=True, exist_ok=True)
        file_path = failed_dir / f"{race_class}-{target_date.isoformat()}.html"
        file_path.write_text(content, encoding="utf-8")
        self._logger.warning("Saved failed scrape payload for %s to %s", page_url, file_path)
