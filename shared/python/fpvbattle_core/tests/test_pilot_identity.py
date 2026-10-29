from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from fpvbattle_core.db.base import Base
from fpvbattle_core.db.models import (
    DaySpecModel,
    GlobalLeaderboardRowModel,
    GlobalLeaderboardSnapshotModel,
    PilotModel,
    ResultModel,
    SeasonLeaderboardModel,
)
from fpvbattle_core.db.pilot_identity import merge_pilot_aliases
from fpvbattle_core.domain.pilots import canonicalize_pilot_name


def test_canonicalize_pilot_name_resolves_renamed_account() -> None:
    assert canonicalize_pilot_name(" ol_ek ") == "dronovoda"
    assert canonicalize_pilot_name("DRONOVODA") == "dronovoda"


def test_merge_pilot_aliases_moves_all_statistics_to_canonical_row() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        alias = PilotModel(pilot="ol_ek", country="UA")
        canonical = PilotModel(pilot="dronovoda")
        day = DaySpecModel(
            date=date(2026, 1, 1),
            race_class="open",
            track="Track",
            season="2026-01",
        )
        snapshot = GlobalLeaderboardSnapshotModel(
            race_class="open",
            snapshot_date=date(2026, 1, 1),
            window_from=date(2025, 12, 3),
            window_to=date(2026, 1, 1),
        )
        session.add_all([alias, canonical, day, snapshot])
        session.flush()
        session.add_all(
            [
                ResultModel(day_spec_ref=day.id, pilot_ref=alias.id, place=1),
                SeasonLeaderboardModel(day_spec_ref=day.id, pilot_ref=alias.id, place=1),
                GlobalLeaderboardRowModel(
                    snapshot_ref=snapshot.id,
                    pilot_ref=alias.id,
                    status="qualified",
                    flight_days=15,
                    scored_days=15,
                ),
            ],
        )
        session.commit()

    with Session(engine) as session:
        merge_pilot_aliases(session)
        session.commit()

        pilots = session.execute(select(PilotModel)).scalars().all()
        assert [(pilot.pilot, pilot.country) for pilot in pilots] == [("dronovoda", "UA")]
        pilot_id = pilots[0].id
        assert session.scalar(select(ResultModel.pilot_ref)) == pilot_id
        assert session.scalar(select(SeasonLeaderboardModel.pilot_ref)) == pilot_id
        assert session.scalar(select(GlobalLeaderboardRowModel.pilot_ref)) == pilot_id
