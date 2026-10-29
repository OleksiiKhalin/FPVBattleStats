from __future__ import annotations

from sqlalchemy import select

from fpvbattle_core.db.models import PilotModel
from fpvbattle_core.domain.pilots import canonicalize_pilot_name
from fpvbattle_core.repositories.base import Repository


class PilotRepository(Repository):
    def get_by_name(self, pilot: str) -> PilotModel | None:
        canonical_name = canonicalize_pilot_name(pilot)
        statement = select(PilotModel).where(PilotModel.pilot == canonical_name)
        return self.session.execute(statement).scalar_one_or_none()

    def upsert(self, *, pilot: str, country: str | None) -> PilotModel:
        canonical_name = canonicalize_pilot_name(pilot)
        pilot_row = self.get_by_name(canonical_name)
        if pilot_row is None:
            pilot_row = PilotModel(pilot=canonical_name, country=country)
            self.session.add(pilot_row)
            self.session.flush()
            return pilot_row

        if country:
            pilot_row.country = country
        self.session.flush()
        return pilot_row
