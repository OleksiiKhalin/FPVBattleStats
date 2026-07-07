from __future__ import annotations

from datetime import date

from sqlalchemy import select

from fpvbattle_core.db.models import DaySpecModel
from fpvbattle_core.repositories.base import Repository


class DaySpecRepository(Repository):
    def get_by_date_and_class(self, target_date: date, race_class: str) -> DaySpecModel | None:
        statement = select(DaySpecModel).where(
            DaySpecModel.date == target_date,
            DaySpecModel.race_class == race_class,
        )
        return self.session.execute(statement).scalar_one_or_none()

    def upsert(
        self,
        *,
        target_date: date,
        race_class: str,
        track: str,
        quad_of_the_day: str | None,
        season: str,
    ) -> DaySpecModel:
        day_spec = self.get_by_date_and_class(target_date, race_class)
        if day_spec is None:
            day_spec = DaySpecModel(
                date=target_date,
                race_class=race_class,
                track=track,
                quad_of_the_day=quad_of_the_day,
                season=season,
            )
            self.session.add(day_spec)
            self.session.flush()
            return day_spec

        day_spec.track = track
        day_spec.quad_of_the_day = quad_of_the_day
        day_spec.season = season
        self.session.flush()
        return day_spec
