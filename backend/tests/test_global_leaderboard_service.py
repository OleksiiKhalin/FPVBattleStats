from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import func, select
import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "shared" / "python"))

from backend.app.services.global_leaderboard_service import GlobalLeaderboardService
from backend.app.schemas.analytics import GlobalLeaderboardResponse
from fpvbattle_core.db.models import DaySpecModel, GlobalLeaderboardSnapshotModel, PilotModel, ResultModel
from fpvbattle_core.db.session import create_db_engine, create_session_factory, init_db


def _add_day(session, race_date: date, race_class: str, results: list[tuple[str, float]]) -> None:
    day = DaySpecModel(
        date=race_date,
        race_class=race_class,
        track=f"Track {race_date.isoformat()}",
        quad_of_the_day=None,
        season=race_date.strftime("%Y-%m"),
    )
    session.add(day)
    session.flush()
    for pilot_name, time_value in results:
        pilot = session.execute(select(PilotModel).where(PilotModel.pilot == pilot_name)).scalar_one_or_none()
        if pilot is None:
            pilot = PilotModel(pilot=pilot_name, country="US")
            session.add(pilot)
            session.flush()
        session.add(
            ResultModel(
                day_spec_ref=day.id,
                pilot_ref=pilot.id,
                category=None,
                quad="Quad",
                time=time_value,
                points=1,
                place=1,
            ),
        )


def _build_session():
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    return create_session_factory(engine)()


def test_global_leaderboard_uses_30_day_window_top_three_and_worst_day_exclusion() -> None:
    session = _build_session()
    start = date(2026, 8, 1)
    for offset in range(30):
        race_date = start + timedelta(days=offset)
        results = [("Leader A", 10.0), ("Leader B", 11.0), ("Leader C", 12.0)]
        if offset < 15:
            results.append(("Target", 12.0 + offset if offset < 14 else 111.0))
        for pilot_index in range(25):
            if offset < 15:
                results.append((f"Pilot {pilot_index:02d}", 20.0 + pilot_index))
        _add_day(session, race_date, "open", results)
    _add_day(session, date(2026, 7, 31), "open", [("Outside", 13.0)])
    session.commit()

    payload = GlobalLeaderboardService(session).get_global_leaderboard(
        race_class="open",
        as_of_date=date(2026, 8, 30),
        selected_pilot="Target",
    )
    rows = {row["pilot"]: row for row in payload["rows"]}

    assert payload["window_from"] == date(2026, 8, 1)
    assert "Outside" not in rows
    assert rows["Target"]["flight_days"] == 15
    assert rows["Target"]["scored_days"] == 15
    assert rows["Target"]["worst_day_gap_percentage"] == pytest.approx(909.091)
    assert rows["Target"]["adjusted_average_gap_percentage"] == pytest.approx(68.182)
    assert rows["Target"]["season_missed_days"] == 15
    assert rows["Target"]["status"] == "at_risk"
    assert rows["Target"]["inactive_days"] == 15
    assert rows["Target"]["days_needed_for_next_season"] == 2
    assert rows["Target"]["available_days_before_next_season"] == 1
    assert rows["Target"]["can_pass_next_season"] is False
    assert rows["Leader A"]["rank"] == 1

    qualified = [row for row in payload["rows"] if row["rank"] is not None]
    assert qualified[9]["league"] == "gold"
    assert qualified[10]["league"] == "silver"
    assert qualified[24]["league"] == "silver"
    assert qualified[25]["league"] == "bronze"
    session.close()


def test_global_leaderboard_snapshots_are_idempotent_and_classes_are_separate() -> None:
    session = _build_session()
    race_date = date(2026, 8, 20)
    for offset in range(15):
        _add_day(session, race_date - timedelta(days=offset), "open", [("Open Pilot", 15.0)])
    _add_day(session, race_date, "whoop", [("Whoop Pilot", 20.0)])
    session.commit()

    service = GlobalLeaderboardService(session)
    service.create_snapshot(race_class="open", snapshot_date=race_date)
    service.create_snapshot(race_class="open", snapshot_date=race_date)
    service.create_snapshot(race_class="whoop", snapshot_date=race_date)
    session.commit()

    snapshot_count = session.scalar(select(func.count()).select_from(GlobalLeaderboardSnapshotModel))
    assert snapshot_count == 2
    open_payload = service.get_global_leaderboard(race_class="open", as_of_date=race_date, selected_pilot="Open Pilot")
    whoop_payload = service.get_global_leaderboard(race_class="whoop", as_of_date=race_date, selected_pilot="Whoop Pilot")
    assert open_payload["last_official_snapshot_date"] == race_date
    assert [row["pilot"] for row in open_payload["rows"]] == ["Open Pilot"]
    assert [row["pilot"] for row in whoop_payload["rows"]] == ["Whoop Pilot"]
    session.close()


def test_projected_rank_includes_candidate_who_can_reach_next_season() -> None:
    session = _build_session()
    start = date(2026, 8, 1)
    for offset in range(-5, 20):
        race_date = start + timedelta(days=offset)
        results = [("Leader A", 10.0), ("Leader B", 11.0), ("Leader C", 12.0)]
        if offset < 15:
            results.append(("Qualified", 20.0))
        if offset >= 16:
            results.append(("Candidate", 12.1))
        _add_day(session, race_date, "open", results)
    session.commit()

    payload = GlobalLeaderboardService(session).get_global_leaderboard(
        race_class="open",
        as_of_date=date(2026, 8, 20),
        selected_pilot="Candidate",
    )
    GlobalLeaderboardResponse.model_validate(payload)
    candidate = payload["selected_pilot"]

    assert candidate is not None
    assert candidate["flight_days"] == 4
    assert candidate["days_needed_for_next_season"] == 11
    assert candidate["available_days_before_next_season"] == 11
    assert candidate["can_pass_next_season"] is True
    assert candidate["projected_next_season_rank"] is not None
    assert candidate["projected_next_season_rank"] <= 25
    assert candidate["status"] == "candidate"
    assert candidate["smart_sort_bucket"] == 1
    session.close()


def test_season_start_rank_uses_first_available_snapshot_in_current_month() -> None:
    session = _build_session()
    start = date(2026, 8, 1)
    for offset in range(-5, 20):
        race_date = start + timedelta(days=offset)
        _add_day(session, race_date, "open", [("Pilot A", 10.0), ("Pilot B", 11.0)])
    session.commit()

    service = GlobalLeaderboardService(session)
    service.create_snapshot(race_class="open", snapshot_date=date(2026, 8, 10))
    session.commit()
    payload = service.get_global_leaderboard(race_class="open", as_of_date=date(2026, 8, 20), selected_pilot="Pilot A")

    assert payload["season_start_snapshot_date"] == date(2026, 8, 10)
    assert payload["selected_pilot"]["season_start_rank"] == 1
    assert payload["selected_pilot"]["season_start_snapshot_date"] == date(2026, 8, 10)
    session.close()


def test_season_start_rank_is_computed_when_no_official_snapshot_exists() -> None:
    session = _build_session()
    for offset in range(-29, 20):
        race_date = date(2026, 8, 1) + timedelta(days=offset)
        _add_day(session, race_date, "open", [("Pilot A", 10.0), ("Pilot B", 11.0), ("Pilot C", 12.0)])
    session.commit()

    payload = GlobalLeaderboardService(session).get_global_leaderboard(
        race_class="open",
        as_of_date=date(2026, 8, 20),
        selected_pilot="Pilot A",
    )

    assert payload["season_start_snapshot_date"] == date(2026, 8, 1)
    assert payload["selected_pilot"]["season_start_rank"] == 1
    assert payload["selected_pilot"]["season_start_league"] == "gold"
    session.close()


def test_probable_view_uses_projected_rank_and_projected_league() -> None:
    session = _build_session()
    start = date(2026, 8, 1)
    for offset in range(20):
        race_date = start + timedelta(days=offset)
        results = [("Leader A", 10.0), ("Leader B", 11.0), ("Leader C", 12.0)]
        if offset < 15:
            results.append(("Qualified", 20.0))
        if offset >= 15:
            results.append(("Late Pilot", 20.5))
        if offset == 19:
            results.append(("Too Late", 20.7))
        _add_day(session, race_date, "open", results)
    session.commit()

    payload = GlobalLeaderboardService(session).get_global_leaderboard(
        race_class="open",
        as_of_date=date(2026, 8, 20),
        selected_pilot="Late Pilot",
        view_mode="probable",
    )

    late_pilot = payload["selected_pilot"]
    assert payload["view_mode"] == "probable"
    assert payload["change_reference_date"] == date(2026, 8, 17)
    assert payload["change_reference_kind"] == "computed"
    assert late_pilot is not None
    assert late_pilot["display_rank"] == late_pilot["projected_next_season_rank"]
    assert late_pilot["display_league"] == late_pilot["projected_next_season_league"]
    assert late_pilot["display_league"] in {"gold", "silver", "bronze"}
    too_late = next(row for row in payload["rows"] if row["pilot"] == "Too Late")
    assert too_late["display_rank"] is None
    assert too_late["display_league"] == "unranked"
    session.close()


def test_historical_slice_excludes_future_rows_but_exposes_current_gap_separately() -> None:
    session = _build_session()
    for offset in range(20):
        race_date = date(2026, 8, 1) + timedelta(days=offset)
        results = [("Leader A", 10.0), ("Leader B", 11.0), ("Leader C", 12.0)]
        if offset < 15 or offset >= 18:
            results.append(("Returning Pilot", 20.0))
        if offset >= 18:
            results.append(("Future Pilot", 20.5))
        _add_day(session, race_date, "open", results)
    session.commit()

    payload = GlobalLeaderboardService(session).get_global_leaderboard(
        race_class="open",
        as_of_date=date(2026, 8, 15),
        selected_pilot="Returning Pilot",
    )
    rows = {row["pilot"]: row for row in payload["rows"]}

    assert payload["is_historical"] is True
    assert payload["latest_data_date"] == date(2026, 8, 20)
    assert "Future Pilot" not in rows
    assert rows["Returning Pilot"]["current_gap_percentage"] == pytest.approx(
        rows["Returning Pilot"]["adjusted_average_gap_percentage"],
    )
    session.close()
