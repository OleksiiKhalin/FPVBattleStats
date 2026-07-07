from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from fpvbattle_core.repositories.day_specs import DaySpecRepository
from fpvbattle_core.repositories.pilots import PilotRepository
from fpvbattle_core.repositories.results import ResultRepository
from fpvbattle_core.repositories.season_leaderboard import SeasonLeaderboardRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None
        self.day_specs: DaySpecRepository
        self.pilots: PilotRepository
        self.results: ResultRepository
        self.season_leaderboard: SeasonLeaderboardRepository

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.day_specs = DaySpecRepository(self.session)
        self.pilots = PilotRepository(self.session)
        self.results = ResultRepository(self.session)
        self.season_leaderboard = SeasonLeaderboardRepository(self.session)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.session is None:
            return
        if exc:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
