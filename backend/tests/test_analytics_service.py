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


def test_pilot_comparison_uses_top_three_average_percentage_and_nulls_missing_days() -> None:
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    session = create_session_factory(engine)()

    race_date = date(2026, 8, 20)
    day_spec = DaySpecModel(
        date=race_date,
        race_class="open",
        track="Track",
        quad_of_the_day=None,
        season="2026-08",
    )
    session.add(day_spec)
    pilots = {}
    for name in ("Leader One", "Leader Two", "Leader Three", "Primary", "Opponent"):
        pilot = PilotModel(pilot=name, country="US")
        session.add(pilot)
        pilots[name] = pilot
    session.flush()

    for place, (name, time) in enumerate(
        (("Leader One", 10.0), ("Leader Two", 11.0), ("Leader Three", 12.0), ("Primary", 22.0), ("Opponent", 16.0)),
        start=1,
    ):
        session.add(
            ResultModel(
                day_spec_ref=day_spec.id,
                category=None,
                pilot_ref=pilots[name].id,
                quad="Quad",
                time=time,
                points=100 - place,
                place=place,
            ),
        )
    session.commit()

    response = AnalyticsService(session).get_pilot_comparison(
        primary_pilot="Primary",
        opponent_pilot="Opponent",
        race_class="open",
        date_from=race_date,
        date_to=race_date,
        season=None,
    )

    day = response["days"][0]
    assert day["primary_gap_to_leader"] == 12.0
    assert day["opponent_gap_to_leader"] == 6.0
    assert day["primary_gap_to_leader_percentage"] == 100.0
    assert day["opponent_gap_to_leader_percentage"] == 45.455

    missing_response = AnalyticsService(session).get_pilot_comparison(
        primary_pilot="Missing",
        opponent_pilot="Opponent",
        race_class="open",
        date_from=race_date,
        date_to=race_date,
        season=None,
    )
    missing_day = missing_response["days"][0]
    assert missing_day["primary_gap_to_leader_percentage"] is None
    assert missing_day["opponent_gap_to_leader_percentage"] == 45.455
    session.close()
