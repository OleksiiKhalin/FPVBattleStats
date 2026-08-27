from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[2] / "shared" / "python"))

from fpvbattle_core.db.models import DaySpecModel, PilotModel, ResultModel
from fpvbattle_core.db.session import create_db_engine, create_session_factory, init_db

from backend.app.schemas.analytics import ProgressCorrelationResponse
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
    day_spec = session.execute(
        select(DaySpecModel).where(DaySpecModel.date == race_date, DaySpecModel.race_class == race_class),
    ).scalar_one_or_none()
    if day_spec is None:
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


def test_general_day_streaks_and_days_flown_are_all_time_and_class_specific() -> None:
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    session = create_session_factory(engine)()

    cutoff = date.today() - timedelta(days=1)
    for offset in range(4, -1, -1):
        _seed_result(session, race_date=cutoff - timedelta(days=offset), race_class="open", pilot_name="Active", place=1)
    for offset in range(20, 16, -1):
        _seed_result(session, race_date=cutoff - timedelta(days=offset), race_class="open", pilot_name="Tie Pilot", place=2)
    for offset in range(4, 0, -1):
        _seed_result(session, race_date=cutoff - timedelta(days=offset), race_class="open", pilot_name="Tie Pilot", place=2)
    for offset in (2, 1):
        _seed_result(session, race_date=cutoff - timedelta(days=offset), race_class="open", pilot_name="Short Run", place=3)
    for offset in range(7, -1, -1):
        _seed_result(session, race_date=cutoff - timedelta(days=offset), race_class="open", pilot_name="Eight Days", place=4)
    for offset in range(10, -1, -1):
        _seed_result(session, race_date=cutoff - timedelta(days=offset), race_class="open", pilot_name="Eleven Days", place=5)
    for offset in range(30, 25, -1):
        _seed_result(session, race_date=cutoff - timedelta(days=offset), race_class="open", pilot_name="Split Pilot", place=6)
    for offset in range(2, -1, -1):
        _seed_result(session, race_date=cutoff - timedelta(days=offset), race_class="open", pilot_name="Split Pilot", place=6)
    _seed_result(session, race_date=date.today(), race_class="open", pilot_name="Today Only", place=6)
    _seed_result(session, race_date=cutoff, race_class="whoop", pilot_name="Whoop Pilot", place=1)
    session.commit()

    service = AnalyticsService(session)
    response = service.get_general_stats(
        race_class="open",
        date_from=cutoff,
        date_to=cutoff,
        selected_pilot="Active",
    )
    day_streaks = response["day_streaks"]

    assert day_streaks["active_cutoff_date"] == cutoff
    assert [row["pilot"] for row in day_streaks["streaks"]] == ["Eleven Days", "Eight Days", "Active", "Split Pilot", "Tie Pilot", "Tie Pilot", "Split Pilot"]
    tie_rows = [row for row in day_streaks["streaks"] if row["pilot"] == "Tie Pilot"]
    assert len(tie_rows) == 2
    tie_best = next(row for row in tie_rows if row["is_best"])
    tie_old = next(row for row in tie_rows if not row["is_best"])
    assert tie_best["length"] == 4
    assert tie_best["end_date"] == cutoff - timedelta(days=1)
    assert tie_best["is_active"] is False
    assert tie_old["is_best"] is False
    active_row = next(row for row in day_streaks["streaks"] if row["pilot"] == "Active")
    assert active_row["is_best"] is True
    assert active_row["is_active"] is True
    split_rows = [row for row in day_streaks["streaks"] if row["pilot"] == "Split Pilot"]
    split_best = next(row for row in split_rows if row["is_best"])
    split_active = next(row for row in split_rows if row["is_active"])
    assert split_best["length"] == 5
    assert split_best["is_active"] is False
    assert split_active["length"] == 3
    assert split_active["is_best"] is False
    assert [row["pilot"] for row in day_streaks["streaks"] if row["is_best"]] == ["Eleven Days", "Eight Days", "Active", "Split Pilot", "Tie Pilot"]
    assert [row["pilot"] for row in day_streaks["streaks"] if row["is_best"] or row["is_active"]] == ["Eleven Days", "Eight Days", "Active", "Split Pilot", "Tie Pilot", "Split Pilot"]
    assert "Short Run" not in {row["pilot"] for row in day_streaks["streaks"]}
    assert "Today Only" not in {row["pilot"] for row in day_streaks["days_flown"]}
    assert day_streaks["days_flown_summary"] == {
        "total_pilots": 6,
        "more_than_7_days": 4,
        "more_than_10_days": 1,
        "more_than_20_days": 0,
        "more_than_30_days": 0,
        "more_than_50_days": 0,
        "more_than_100_days": 0,
        "more_than_200_days": 0,
        "more_than_300_days": 0,
        "more_than_400_days": 0,
        "more_than_500_days": 0,
    }

    all_time_response = service.get_general_stats(race_class="open", date_from=None, date_to=None, selected_pilot=None)
    assert all_time_response["day_streaks"] == day_streaks
    whoop_response = service.get_general_stats(race_class="whoop", date_from=None, date_to=None, selected_pilot=None)
    assert [row["pilot"] for row in whoop_response["day_streaks"]["days_flown"]] == ["Whoop Pilot"]
    session.close()


def test_progress_correlation_uses_cumulative_experience_and_post_cutoff_gaps() -> None:
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    session = create_session_factory(engine)()

    pre_gap_date = date(2026, 2, 28)
    gap_start = date(2026, 3, 1)
    for pilot_name, place in (("Novice", 1),):
        _seed_result(session, race_date=pre_gap_date, race_class="open", pilot_name=pilot_name, place=place)
    for pilot_name, place in (("Leader One", 1), ("Leader Two", 2), ("Leader Three", 3), ("Novice", 4)):
        _seed_result(session, race_date=gap_start, race_class="open", pilot_name=pilot_name, place=place)
    for pilot_name, place in (("Leader One", 1), ("Leader Two", 2), ("Leader Three", 3), ("Novice", 2)):
        _seed_result(session, race_date=gap_start + timedelta(days=1), race_class="open", pilot_name=pilot_name, place=place)
    _seed_result(session, race_date=date.today(), race_class="open", pilot_name="Today Only", place=5)
    _seed_result(session, race_date=gap_start, race_class="whoop", pilot_name="Whoop Only", place=1)
    session.commit()

    response = AnalyticsService(session).get_progress_correlation(
        race_class="open",
        gap_from=gap_start,
        viewport_pilot="Novice",
    )
    validated = ProgressCorrelationResponse.model_validate(response)
    novice_points = [point for point in response["points"] if point["pilot"] == "Novice"]

    assert validated.viewport_pilot == "Novice"
    assert response["completed_through"] == date.today() - timedelta(days=1)
    assert [point["days_flown"] for point in novice_points] == [2, 3]
    assert all(point["date"] >= gap_start for point in response["points"])
    assert all(point["pilot"] != "Today Only" for point in response["points"])
    assert novice_points[0]["gap_percentage"] == 9.091
    average_day_two = next(row for row in response["averages"] if row["days_flown"] == 2)
    assert average_day_two == {"days_flown": 2, "average_gap_percentage": 3.426, "median_gap_percentage": 3.846, "sample_size": 4}

    later_response = AnalyticsService(session).get_progress_correlation(
        race_class="open",
        gap_from=gap_start + timedelta(days=1),
        viewport_pilot="Novice",
    )
    later_novice_points = [point for point in later_response["points"] if point["pilot"] == "Novice"]
    assert [point["days_flown"] for point in later_novice_points] == [3]
    assert "Whoop Only" not in {point["pilot"] for point in response["points"]}
    session.close()


def test_progress_correlation_median_handles_odd_sample_groups() -> None:
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    session = create_session_factory(engine)()

    cutoff = date.today() - timedelta(days=1)
    gap_start = cutoff - timedelta(days=1)
    _seed_result(session, race_date=cutoff - timedelta(days=2), race_class="open", pilot_name="A", place=1)
    for pilot_name, place in (("A", 1), ("B", 2), ("C", 3)):
        _seed_result(session, race_date=gap_start, race_class="open", pilot_name=pilot_name, place=place)
    for pilot_name, place in (("A", 3), ("B", 1), ("C", 2)):
        _seed_result(session, race_date=cutoff, race_class="open", pilot_name=pilot_name, place=place)
    session.commit()

    response = AnalyticsService(session).get_progress_correlation(
        race_class="open",
        gap_from=gap_start,
        viewport_pilot="A",
    )

    median_day_two = next(row for row in response["averages"] if row["days_flown"] == 2)
    assert median_day_two["sample_size"] == 3
    assert median_day_two["median_gap_percentage"] == -4.545
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
