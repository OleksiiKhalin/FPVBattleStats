from __future__ import annotations

from datetime import date
import logging

from sqlalchemy import func, select

from fpvbattle_core.db.models import DaySpecModel, ResultModel
from fpvbattle_core.services.unit_of_work import SqlAlchemyUnitOfWork

from ..domain import ParsedDayPayload


class ScrapePersistenceService:
    def __init__(self, unit_of_work: SqlAlchemyUnitOfWork) -> None:
        self.unit_of_work = unit_of_work
        self._logger = logging.getLogger(__name__)

    def persist_day(self, payload: ParsedDayPayload) -> bool:
        if not payload.results:
            self._logger.warning(
                "No daily results parsed for %s %s from %s; skipping persistence for this day.",
                payload.race_class,
                payload.date.isoformat(),
                payload.source,
            )
            return False
        with self.unit_of_work as uow:
            day_spec = uow.day_specs.upsert(
                target_date=payload.date,
                race_class=payload.race_class,
                track=payload.track,
                quad_of_the_day=payload.quad_of_the_day,
                season=payload.season,
            )

            uow.results.replace_for_day(day_spec_ref=day_spec.id)
            uow.season_leaderboard.replace_for_day(day_spec_ref=day_spec.id)

            for row in payload.results:
                pilot = uow.pilots.upsert(pilot=row.pilot, country=row.country)
                uow.results.upsert(
                    day_spec_ref=day_spec.id,
                    category=row.category,
                    pilot_ref=pilot.id,
                    quad=row.quad,
                    time=row.time,
                    points=row.points,
                    place=row.place,
                )

            for row in payload.season_leaderboard:
                pilot = uow.pilots.upsert(pilot=row.pilot, country=row.country)
                uow.season_leaderboard.upsert(
                    day_spec_ref=day_spec.id,
                    category=row.category,
                    pilot_ref=pilot.id,
                    points=row.points,
                    place=row.place,
                )

            self._logger.info(
                "Persisted %s %s from %s: results=%s season_rows=%s",
                payload.race_class,
                payload.date.isoformat(),
                payload.source,
                len(payload.results),
                len(payload.season_leaderboard),
            )
        return True

    def has_day(self, *, target_date: date, race_class: str) -> bool:
        with self.unit_of_work as uow:
            day_spec = uow.day_specs.get_by_date_and_class(target_date, race_class)
            if day_spec is None:
                return False
            result_count = uow.session.execute(
                select(func.count(ResultModel.id)).where(ResultModel.day_spec_ref == day_spec.id),
            ).scalar_one()
            if result_count == 0:
                self._logger.warning(
                    "Found incomplete day_spec without results for %s %s; treating it as missing so it can be re-synced.",
                    race_class,
                    target_date.isoformat(),
                )
                return False
            return True
