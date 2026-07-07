from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[2] / "shared" / "python"))

from fpvbattle_core.db.models import DaySpecModel, PilotModel, ResultModel
from fpvbattle_core.db.session import create_db_engine, create_session_factory, init_db

from backend.app.services.analytics_service import AnalyticsService


def _seed_result(
    session,
    *,
    race_date: date,
    race_class: str,
    pilot_name: str,
    place: int,
    country: str = "US",
) -> None:
    day_spec = DaySpecModel(
        date=race_date,
        race_class=race_class,
        track=f"Track {race_date.isoformat()}",
        quad_of_the_day=None,
        season=race_date.strftime("%Y-%m"),
    )
    session.add(day_spec)
    pilot = session.execute(select(PilotModel).where(PilotModel.pilot == pilot_name)).scalar_one_or_none()
    if pilot is None:
        pilot = PilotModel(pilot=pilot_name, country=country)
        session.add(pilot)
    session.flush()
    session.add(
        ResultModel(
            day_spec_ref=day_spec.id,
            category=None,
            pilot_ref=pilot.id,
            quad="Quad",
            time=20.0 + place,
            points=100 - place,
            place=place,
        ),
    )


def test_consistency_ignores_date_filters_and_uses_full_history() -> None:
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    session = create_session_factory(engine)()

    start = date(2026, 7, 1)
    alpha_places = [1, 1]
    bravo_places = [1, 1, 1, 1]
    chaos_places = [1, 4, 1, 4]
    improver_places = [10, 8, 6, 4, 3, 2]

    for index, place in enumerate(alpha_places):
        _seed_result(session, race_date=start + timedelta(days=index), race_class="open", pilot_name="Alpha", place=place)
    for index, place in enumerate(bravo_places):
        _seed_result(session, race_date=start + timedelta(days=10 + index), race_class="open", pilot_name="Bravo", place=place)
    for index, place in enumerate(chaos_places):
        _seed_result(session, race_date=start + timedelta(days=20 + index), race_class="open", pilot_name="Chaos", place=place)
    for index, place in enumerate(improver_places):
        _seed_result(session, race_date=start + timedelta(days=30 + index), race_class="open", pilot_name="Improver", place=place)
    _seed_result(session, race_date=start, race_class="whoop", pilot_name="WhoopOnly", place=1)
    session.commit()

    service = AnalyticsService(session)
    full_range = service.get_general_stats(
        race_class="open",
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
        selected_pilot="Bravo",
    )
    narrow_range = service.get_general_stats(
        race_class="open",
        date_from=date(2026, 7, 31),
        date_to=date(2026, 7, 31),
        selected_pilot="Bravo",
    )

    assert full_range["consistency_leaderboard"] == narrow_range["consistency_leaderboard"]
    assert full_range["selected_pilot_consistency"] == narrow_range["selected_pilot_consistency"]

    leaderboard = {row["pilot"]: row for row in full_range["consistency_leaderboard"]}
    assert "WhoopOnly" not in leaderboard
    assert leaderboard["Bravo"]["consistency_score"] > leaderboard["Alpha"]["consistency_score"]
    assert leaderboard["Alpha"]["consistency_score"] > leaderboard["Chaos"]["consistency_score"]
    assert leaderboard["Bravo"]["dispersion"] == 0.0
    assert leaderboard["Bravo"]["first_flight_date"] == date(2026, 7, 11)
    assert leaderboard["Bravo"]["last_flight_date"] == date(2026, 7, 14)

    improvements = {row["pilot"]: row["improvement_score"] for row in full_range["best_improvement"]}
    assert improvements["Improver"] > 0

    session.close()
