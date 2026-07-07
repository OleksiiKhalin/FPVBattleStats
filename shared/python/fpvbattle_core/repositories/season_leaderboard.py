from __future__ import annotations

from sqlalchemy import delete, select

from fpvbattle_core.db.models import SeasonLeaderboardModel
from fpvbattle_core.repositories.base import Repository


class SeasonLeaderboardRepository(Repository):
    def get_by_day_and_pilot(self, *, day_spec_ref: int, pilot_ref: int) -> SeasonLeaderboardModel | None:
        statement = select(SeasonLeaderboardModel).where(
            SeasonLeaderboardModel.day_spec_ref == day_spec_ref,
            SeasonLeaderboardModel.pilot_ref == pilot_ref,
        )
        return self.session.execute(statement).scalar_one_or_none()

    def replace_for_day(self, *, day_spec_ref: int) -> None:
        self.session.execute(delete(SeasonLeaderboardModel).where(SeasonLeaderboardModel.day_spec_ref == day_spec_ref))

    def upsert(
        self,
        *,
        day_spec_ref: int,
        category: str | None,
        pilot_ref: int,
        points: int | None,
        place: int | None,
    ) -> SeasonLeaderboardModel:
        row = self.get_by_day_and_pilot(day_spec_ref=day_spec_ref, pilot_ref=pilot_ref)
        if row is None:
            row = SeasonLeaderboardModel(
                day_spec_ref=day_spec_ref,
                category=category,
                pilot_ref=pilot_ref,
                points=points,
                place=place,
            )
            self.session.add(row)
        else:
            row.category = category
            row.points = points
            row.place = place
        self.session.flush()
        return row
