from __future__ import annotations

from sqlalchemy import delete, select

from fpvbattle_core.db.models import ResultModel
from fpvbattle_core.repositories.base import Repository


class ResultRepository(Repository):
    def get_by_day_and_pilot(self, *, day_spec_ref: int, pilot_ref: int) -> ResultModel | None:
        statement = select(ResultModel).where(
            ResultModel.day_spec_ref == day_spec_ref,
            ResultModel.pilot_ref == pilot_ref,
        )
        return self.session.execute(statement).scalar_one_or_none()

    def replace_for_day(self, *, day_spec_ref: int) -> None:
        self.session.execute(delete(ResultModel).where(ResultModel.day_spec_ref == day_spec_ref))

    def upsert(
        self,
        *,
        day_spec_ref: int,
        category: str | None,
        pilot_ref: int,
        quad: str | None,
        time: float | None,
        points: int | None,
        place: int | None,
    ) -> ResultModel:
        result = self.get_by_day_and_pilot(day_spec_ref=day_spec_ref, pilot_ref=pilot_ref)
        if result is None:
            result = ResultModel(
                day_spec_ref=day_spec_ref,
                category=category,
                pilot_ref=pilot_ref,
                quad=quad,
                time=time,
                points=points,
                place=place,
            )
            self.session.add(result)
        else:
            result.category = category
            result.quad = quad
            result.time = time
            result.points = points
            result.place = place
        self.session.flush()
        return result
