from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from fpvbattle_core.db.models import (
    DaySpecModel,
    GlobalLeaderboardRowModel,
    GlobalLeaderboardSnapshotModel,
    PilotModel,
    ResultModel,
)


class GlobalLeaderboardService:
    MIN_FLIGHT_DAYS = 15
    WINDOW_DAYS = 30

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_global_leaderboard(
        self,
        *,
        race_class: str,
        as_of_date: date | None = None,
        selected_pilot: str | None = None,
        view_mode: str = "current",
    ) -> dict:
        if view_mode not in {"current", "probable"}:
            raise ValueError("view_mode must be current or probable")
        as_of = as_of_date or self._latest_date(race_class=race_class) or date.today()
        state = self._calculate_state(race_class=race_class, as_of_date=as_of)
        self._apply_projection_ranks(state["rows"], forecast_key="weekly")
        self._apply_projection_ranks(state["rows"], forecast_key="monthly")

        latest_data_date = self._latest_date(race_class=race_class)
        is_historical = latest_data_date is not None and as_of < latest_data_date
        current_gap_by_pilot: dict[str, float | None] = {}
        if is_historical and latest_data_date is not None:
            current_state = self._calculate_state(race_class=race_class, as_of_date=latest_data_date)
            current_gap_by_pilot = {
                row["pilot"]: row["adjusted_average_gap_percentage"]
                for row in current_state["rows"]
            }

        latest_snapshot = self._latest_snapshot(race_class=race_class, as_of_date=as_of)
        season_start_snapshot = self._season_start_snapshot(race_class=race_class, as_of_date=as_of)
        if season_start_snapshot is not None:
            season_start_rows = self._snapshot_rows(season_start_snapshot.id)
            season_start_reference_date = season_start_snapshot.snapshot_date
        else:
            season_start_reference_date = date(as_of.year, as_of.month, 1)
            season_start_state = self._calculate_state(
                race_class=race_class,
                as_of_date=season_start_reference_date,
            )
            season_start_rows = self._state_rank_rows(season_start_state)

        change_reference_date, change_reference_kind, change_rows = self._change_reference(
            race_class=race_class,
            as_of_date=as_of,
        )

        rows = []
        for row in state["rows"]:
            decorated = {
                key: value
                for key, value in row.items()
                if not key.startswith("_")
            }
            change = change_rows.get(row["pilot"], {})
            season_start = season_start_rows.get(row["pilot"], {})
            decorated["rank_delta"] = self._rank_delta(row["rank"], change.get("rank"))
            decorated["league_delta"] = self._league_delta(row["league"], change.get("league"))
            decorated["current_league"] = row["league"] or "unranked"
            decorated["gap_change_percentage"] = self._gap_change(
                current=row["adjusted_average_gap_percentage"],
                baseline=change.get("adjusted_average_gap"),
            )
            decorated["change_reference_gap_percentage"] = change.get("adjusted_average_gap")
            decorated["season_start_rank"] = season_start.get("rank")
            decorated["season_start_league"] = season_start.get("league")
            decorated["season_start_snapshot_date"] = season_start_reference_date
            monthly = row["forecast_monthly"]
            decorated["projected_next_season_rank"] = monthly["continue_rank"]
            decorated["projected_next_season_league"] = monthly["continue_league"] or "unranked"
            decorated["projected_next_season_eligible"] = monthly["continue_rank"] is not None
            decorated["status"] = self._status_for(row=row)
            decorated["status_reason"] = self._status_reason(row=row, season_end_date=state["season_end_date"])
            decorated["current_gap_percentage"] = current_gap_by_pilot.get(row["pilot"]) if is_historical else None
            if view_mode == "probable":
                decorated["display_rank"] = monthly["continue_rank"]
                decorated["display_league"] = monthly["continue_league"] or "unranked"
            else:
                decorated["display_rank"] = row["rank"]
                decorated["display_league"] = row["league"] or "unranked"
            rows.append(decorated)

        rows.sort(
            key=lambda row: (
                row["display_rank"] is None,
                row["display_rank"] if row["display_rank"] is not None else math.inf,
                row["pilot"],
            ),
        )
        selected = next((row for row in rows if row["pilot"] == selected_pilot), None)
        return {
            "race_class": race_class,
            "view_mode": view_mode,
            "as_of_date": as_of,
            "latest_data_date": latest_data_date,
            "is_historical": is_historical,
            "window_from": state["window_from"],
            "window_to": state["window_to"],
            "last_official_snapshot_date": latest_snapshot.snapshot_date if latest_snapshot else None,
            "last_official_snapshot_kind": latest_snapshot.calculation_kind if latest_snapshot else None,
            "season_start_snapshot_date": season_start_reference_date,
            "change_reference_date": change_reference_date,
            "change_reference_kind": change_reference_kind,
            "next_weekly_checkpoint": state["next_weekly_checkpoint"],
            "next_month_start": state["next_month_start"],
            "season_end_date": state["season_end_date"],
            "minimum_flight_days": self.MIN_FLIGHT_DAYS,
            "window_days": self.WINDOW_DAYS,
            "gold_places": 10,
            "silver_places": 15,
            "selected_pilot": selected,
            "rows": rows,
        }

    def create_snapshot(
        self,
        *,
        race_class: str,
        snapshot_date: date | None = None,
    ) -> GlobalLeaderboardSnapshotModel:
        as_of = snapshot_date or self._latest_date(race_class=race_class) or date.today()
        state = self._calculate_state(race_class=race_class, as_of_date=as_of)
        snapshot = self.session.execute(
            select(GlobalLeaderboardSnapshotModel).where(
                GlobalLeaderboardSnapshotModel.race_class == race_class,
                GlobalLeaderboardSnapshotModel.snapshot_date == as_of,
            ),
        ).scalar_one_or_none()
        if snapshot is None:
            snapshot = GlobalLeaderboardSnapshotModel(
                race_class=race_class,
                snapshot_date=as_of,
                window_from=state["window_from"],
                window_to=state["window_to"],
            )
            self.session.add(snapshot)
            self.session.flush()

        snapshot.window_from = state["window_from"]
        snapshot.window_to = state["window_to"]
        if as_of.day == 1 and as_of.weekday() == 0:
            snapshot.calculation_kind = "weekly_and_monthly"
        elif as_of.day == 1:
            snapshot.calculation_kind = "monthly"
        else:
            snapshot.calculation_kind = "weekly"
        self.session.execute(
            delete(GlobalLeaderboardRowModel).where(GlobalLeaderboardRowModel.snapshot_ref == snapshot.id),
        )
        self.session.flush()
        for row in state["rows"]:
            self.session.add(
                GlobalLeaderboardRowModel(
                    snapshot_ref=snapshot.id,
                    pilot_ref=row["pilot_ref"],
                    rank=row["rank"],
                    league=row["league"],
                    status="qualified" if row["rank"] is not None else "candidate",
                    flight_days=row["flight_days"],
                    scored_days=row["scored_days"],
                    last_flight_date=row["last_flight_date"],
                    adjusted_average_gap=row["adjusted_average_gap_percentage"],
                    worst_day_gap=row["worst_day_gap_percentage"],
                ),
            )
        self.session.flush()
        return snapshot

    def _calculate_state(self, *, race_class: str, as_of_date: date) -> dict:
        window_from = as_of_date - timedelta(days=self.WINDOW_DAYS - 1)
        next_month_start = self._next_month_start(as_of_date)
        season_end_date = next_month_start - timedelta(days=1)
        raw_rows = self.session.execute(
            select(
                DaySpecModel.date,
                ResultModel.time,
                PilotModel.id,
                PilotModel.pilot,
                PilotModel.country,
            )
            .join(ResultModel, ResultModel.day_spec_ref == DaySpecModel.id)
            .join(PilotModel, PilotModel.id == ResultModel.pilot_ref)
            .where(
                DaySpecModel.race_class == race_class,
                DaySpecModel.date >= window_from,
                DaySpecModel.date <= as_of_date,
                ResultModel.time.is_not(None),
            )
            .order_by(DaySpecModel.date, ResultModel.time, PilotModel.pilot),
        ).all()

        all_timed_rows = self.session.execute(
            select(DaySpecModel.date, PilotModel.pilot)
            .join(ResultModel, ResultModel.day_spec_ref == DaySpecModel.id)
            .join(PilotModel, PilotModel.id == ResultModel.pilot_ref)
            .where(
                DaySpecModel.race_class == race_class,
                DaySpecModel.date <= as_of_date,
                ResultModel.time.is_not(None),
            ),
        ).all()
        all_flight_dates: dict[str, set[date]] = defaultdict(set)
        for race_date, pilot in all_timed_rows:
            all_flight_dates[pilot].add(race_date)

        season_start = date(as_of_date.year, as_of_date.month, 1)
        season_race_days = set(
            self.session.scalars(
                select(DaySpecModel.date).where(
                    DaySpecModel.race_class == race_class,
                    DaySpecModel.date >= season_start,
                    DaySpecModel.date <= as_of_date,
                ),
            ).all(),
        )

        day_rows: dict[date, list[tuple[int, str, str | None, float]]] = defaultdict(list)
        for race_date, time_value, pilot_ref, pilot, country in raw_rows:
            day_rows[race_date].append((pilot_ref, pilot, country, float(time_value)))

        pilot_data: dict[str, dict] = {}
        for race_date, rows in day_rows.items():
            top_times = sorted(row[3] for row in rows)[:3]
            top_three_average = sum(top_times) / len(top_times) if top_times else None
            if top_three_average in (None, 0):
                continue
            for pilot_ref, pilot, country, time_value in rows:
                data = pilot_data.setdefault(
                    pilot,
                    {
                        "pilot_ref": pilot_ref,
                        "pilot": pilot,
                        "country": country,
                        "dates": [],
                        "gaps": [],
                    },
                )
                data["dates"].append(race_date)
                data["gaps"].append((race_date, ((time_value - top_three_average) / top_three_average) * 100))

        rows = []
        for data in pilot_data.values():
            gaps = [gap for _, gap in data["gaps"]]
            adjusted_average_gap, worst_day_gap = self._adjusted_average(gaps)
            dates = sorted(set(data["dates"]))
            survival = self._survival_projection(
                dates=dates,
                as_of_date=as_of_date,
                next_month_start=next_month_start,
                season_end_date=season_end_date,
            )
            all_dates = all_flight_dates.get(data["pilot"], set(dates))
            first_flight_date = min(all_dates) if all_dates else None
            season_flight_days = {
                race_date
                for race_date in all_dates
                if season_start <= race_date <= as_of_date
            }
            season_counted_days = {
                race_date
                for race_date in season_race_days
                if first_flight_date is not None and race_date >= first_flight_date
            }
            recent_7_days = {
                race_date
                for race_date in season_race_days
                if as_of_date - timedelta(days=6) <= race_date <= as_of_date
                and first_flight_date is not None
                and race_date >= first_flight_date
            }
            recent_15_days = {
                race_date
                for race_date in season_race_days
                if as_of_date - timedelta(days=14) <= race_date <= as_of_date
                and first_flight_date is not None
                and race_date >= first_flight_date
            }
            rows.append(
                {
                    "pilot_ref": data["pilot_ref"],
                    "pilot": data["pilot"],
                    "country": data["country"],
                    "rank": None,
                    "league": None,
                    "flight_days": len(dates),
                    "scored_days": len(gaps),
                    "last_flight_date": dates[-1] if dates else None,
                    "first_flight_date": first_flight_date,
                    "inactive_days": (as_of_date - dates[-1]).days if dates else self.WINDOW_DAYS,
                    "season_missed_days": max(0, len(season_counted_days) - len(season_flight_days)),
                    "missed_last_7_days": len(recent_7_days - season_flight_days),
                    "missed_last_15_days": len(recent_15_days - season_flight_days),
                    "adjusted_average_gap_percentage": adjusted_average_gap,
                    "worst_day_gap_percentage": worst_day_gap,
                    "required_flight_days": max(0, self.MIN_FLIGHT_DAYS - len(dates)),
                    "days_needed_for_next_season": survival["days_needed"],
                    "available_days_before_next_season": survival["available_days"],
                    "next_season_retained_days": survival["retained_days"],
                    "can_pass_next_season": survival["can_pass"],
                    "target_league": None,
                    "gap_to_next_league_percentage": None,
                    "smart_sort_bucket": 3,
                    "_flight_dates": dates,
                    "_gaps": data["gaps"],
                },
            )

        qualified = sorted(
            [row for row in rows if row["flight_days"] >= self.MIN_FLIGHT_DAYS and row["adjusted_average_gap_percentage"] is not None],
            key=lambda row: (row["adjusted_average_gap_percentage"], row["pilot"]),
        )
        for index, row in enumerate(qualified, start=1):
            row["rank"] = index
            row["league"] = self._league_for_rank(index)

        qualified_by_pilot = {row["pilot"]: row for row in qualified}
        candidates = sorted(
            [row for row in rows if row["pilot"] not in qualified_by_pilot],
            key=lambda row: (
                row["adjusted_average_gap_percentage"] is None,
                row["adjusted_average_gap_percentage"] or math.inf,
                row["pilot"],
            ),
        )
        rows = qualified + candidates
        gold_cutoff = qualified[9]["adjusted_average_gap_percentage"] if len(qualified) >= 10 else None
        silver_cutoff = qualified[24]["adjusted_average_gap_percentage"] if len(qualified) >= 25 else None
        for row in rows:
            row["target_league"] = self._target_league(row=row)
            row["gap_to_next_league_percentage"] = self._gap_to_target(
                row=row,
                gold_cutoff=gold_cutoff,
                silver_cutoff=silver_cutoff,
            )

        for row in rows:
            row["forecast_weekly"] = self._forecast(
                row=row,
                horizon=self._next_monday(as_of_date),
                as_of_date=as_of_date,
                include_horizon_day=True,
            )
            row["forecast_monthly"] = self._forecast(
                row=row,
                horizon=next_month_start,
                as_of_date=as_of_date,
                include_horizon_day=False,
            )

        return {
            "window_from": window_from,
            "window_to": as_of_date,
            "next_weekly_checkpoint": self._next_monday(as_of_date),
            "next_month_start": next_month_start,
            "season_end_date": season_end_date,
            "rows": rows,
        }

    @staticmethod
    def _state_rank_rows(state: dict) -> dict[str, dict]:
        return {
            row["pilot"]: {
                "rank": row["rank"],
                "league": row["league"],
                "adjusted_average_gap": row["adjusted_average_gap_percentage"],
            }
            for row in state["rows"]
        }

    def _change_reference(
        self,
        *,
        race_class: str,
        as_of_date: date,
    ) -> tuple[date, str, dict[str, dict]]:
        season_start = date(as_of_date.year, as_of_date.month, 1)
        weekly_date = max(season_start, as_of_date - timedelta(days=as_of_date.weekday()))
        weekly_snapshot = self._change_reference_snapshot(
            race_class=race_class,
            as_of_date=as_of_date,
            reference_from=weekly_date,
        )
        season_snapshot = self._season_start_snapshot(
            race_class=race_class,
            as_of_date=as_of_date,
        )

        candidates: list[tuple[int, date, str, dict[str, dict]]] = []
        if weekly_snapshot is not None:
            candidates.append(
                (
                    (as_of_date - weekly_snapshot.snapshot_date).days,
                    weekly_snapshot.snapshot_date,
                    "weekly",
                    self._snapshot_rows(weekly_snapshot.id),
                ),
            )
        else:
            weekly_state = self._calculate_state(race_class=race_class, as_of_date=weekly_date)
            candidates.append(
                (
                    (as_of_date - weekly_date).days,
                    weekly_date,
                    "computed_weekly",
                    self._state_rank_rows(weekly_state),
                ),
            )

        season_date = season_snapshot.snapshot_date if season_snapshot is not None else season_start
        season_rows = (
            self._snapshot_rows(season_snapshot.id)
            if season_snapshot is not None
            else self._state_rank_rows(self._calculate_state(race_class=race_class, as_of_date=season_start))
        )
        candidates.append(
            (
                (as_of_date - season_date).days,
                season_date,
                "season" if season_snapshot is not None else "computed_season",
                season_rows,
            ),
        )
        _, reference_date, reference_kind, reference_rows = min(
            candidates,
            key=lambda item: (item[0], 0 if item[2].startswith("weekly") else 1),
        )
        return reference_date, reference_kind, reference_rows

    def _forecast(
        self,
        *,
        row: dict,
        horizon: date,
        as_of_date: date,
        include_horizon_day: bool,
    ) -> dict:
        window_from = horizon - timedelta(days=self.WINDOW_DAYS - 1)
        current_gaps = {race_date: gap for race_date, gap in row["_gaps"]}
        retained_dates = {race_date for race_date in row["_flight_dates"] if window_from <= race_date <= as_of_date}
        retained_gaps = [gap for race_date, gap in current_gaps.items() if window_from <= race_date <= as_of_date]
        last_future_offset = (horizon - as_of_date).days if include_horizon_day else (horizon - as_of_date).days - 1
        future_dates = {
            as_of_date + timedelta(days=offset)
            for offset in range(1, max(0, last_future_offset) + 1)
        }
        continue_dates = retained_dates | future_dates
        projected_gap = row["adjusted_average_gap_percentage"]
        continue_gaps = retained_gaps + ([projected_gap] * len(future_dates) if projected_gap is not None else [])
        no_flight_average, _ = self._adjusted_average(retained_gaps)
        continue_average, _ = self._adjusted_average(continue_gaps)
        return {
            "checkpoint_date": horizon,
            "no_flight_days": len(retained_dates),
            "continue_flight_days": len(continue_dates),
            "no_flight_adjusted_average_gap_percentage": no_flight_average,
            "continue_adjusted_average_gap_percentage": continue_average,
            "no_flight_rank": None,
            "no_flight_league": None,
            "continue_rank": None,
            "continue_league": None,
            "days_needed_to_qualify": max(0, self.MIN_FLIGHT_DAYS - len(continue_dates)),
            "can_qualify_if_active": len(continue_dates) >= self.MIN_FLIGHT_DAYS and continue_average is not None,
        }

    def _apply_projection_ranks(self, rows: list[dict], *, forecast_key: str) -> None:
        eligible = [
            row for row in rows
            if row["forecast_" + forecast_key]["can_qualify_if_active"]
        ]
        eligible.sort(
            key=lambda row: (
                row["forecast_" + forecast_key]["continue_adjusted_average_gap_percentage"],
                row["pilot"],
            ),
        )
        for rank, row in enumerate(eligible, start=1):
            forecast = row["forecast_" + forecast_key]
            forecast["continue_rank"] = rank
            forecast["continue_league"] = self._league_for_rank(rank)

        no_flight_eligible = [
            row for row in rows
            if row["forecast_" + forecast_key]["no_flight_days"] >= self.MIN_FLIGHT_DAYS
            and row["forecast_" + forecast_key]["no_flight_adjusted_average_gap_percentage"] is not None
        ]
        no_flight_eligible.sort(
            key=lambda row: (
                row["forecast_" + forecast_key]["no_flight_adjusted_average_gap_percentage"],
                row["pilot"],
            ),
        )
        for rank, row in enumerate(no_flight_eligible, start=1):
            forecast = row["forecast_" + forecast_key]
            forecast["no_flight_rank"] = rank
            forecast["no_flight_league"] = self._league_for_rank(rank)

        for row in rows:
            forecast = row["forecast_" + forecast_key]
            if forecast_key == "monthly":
                row["smart_sort_bucket"] = self._smart_sort_bucket(row=row)

    def _status_for(self, *, row: dict) -> str:
        if row["rank"] is not None:
            return "at_risk" if row["days_needed_for_next_season"] > 0 else "qualified"
        return "candidate" if row["can_pass_next_season"] and row["forecast_monthly"]["continue_rank"] is not None and row["forecast_monthly"]["continue_rank"] <= 25 else "guaranteed_out"

    def _status_reason(self, *, row: dict, season_end_date: date) -> str:
        status = self._status_for(row=row)
        if status == "at_risk":
            return f"Needs {row['days_needed_for_next_season']} more flight-days before {season_end_date} to stay eligible."
        if status == "guaranteed_out":
            if not row["can_pass_next_season"]:
                return "There are not enough remaining calendar days to reach 15 retained flight-days."
            return "The projected result does not reach the next-season top 25."
        if status == "candidate":
            return f"Can reach the projected leaderboard with {row['days_needed_for_next_season']} more flight-days."
        return "Qualified with no additional flight-days required for next season."

    def _survival_projection(
        self,
        *,
        dates: list[date],
        as_of_date: date,
        next_month_start: date,
        season_end_date: date,
    ) -> dict:
        transition_window_from = next_month_start - timedelta(days=self.WINDOW_DAYS - 1)
        retained_days = sum(1 for race_date in dates if transition_window_from <= race_date <= as_of_date)
        available_days = max(0, (season_end_date - as_of_date).days)
        days_needed = max(0, self.MIN_FLIGHT_DAYS - retained_days)
        return {
            "retained_days": retained_days,
            "available_days": available_days,
            "days_needed": days_needed,
            "can_pass": days_needed <= available_days,
        }

    @staticmethod
    def _smart_sort_bucket(*, row: dict) -> int:
        status = row["status"] if "status" in row else None
        if row["rank"] is not None and row["days_needed_for_next_season"] > 0:
            return 0
        if row["rank"] is None and row["forecast_monthly"]["continue_rank"] is not None and row["forecast_monthly"]["continue_rank"] <= 25:
            return 1
        if row["rank"] is not None:
            return 2
        return 3

    def _previous_snapshot(self, *, race_class: str, as_of_date: date) -> GlobalLeaderboardSnapshotModel | None:
        return self.session.execute(
            select(GlobalLeaderboardSnapshotModel)
            .where(
                GlobalLeaderboardSnapshotModel.race_class == race_class,
                GlobalLeaderboardSnapshotModel.snapshot_date < as_of_date,
            )
            .order_by(GlobalLeaderboardSnapshotModel.snapshot_date.desc())
            .limit(1),
        ).scalar_one_or_none()

    def _change_reference_snapshot(
        self,
        *,
        race_class: str,
        as_of_date: date,
        reference_from: date,
    ) -> GlobalLeaderboardSnapshotModel | None:
        return self.session.execute(
            select(GlobalLeaderboardSnapshotModel)
            .where(
                GlobalLeaderboardSnapshotModel.race_class == race_class,
                GlobalLeaderboardSnapshotModel.snapshot_date >= reference_from,
                GlobalLeaderboardSnapshotModel.snapshot_date <= as_of_date,
            )
            .order_by(GlobalLeaderboardSnapshotModel.snapshot_date.desc())
            .limit(1),
        ).scalar_one_or_none()

    def _latest_snapshot(self, *, race_class: str, as_of_date: date) -> GlobalLeaderboardSnapshotModel | None:
        return self.session.execute(
            select(GlobalLeaderboardSnapshotModel)
            .where(
                GlobalLeaderboardSnapshotModel.race_class == race_class,
                GlobalLeaderboardSnapshotModel.snapshot_date <= as_of_date,
            )
            .order_by(GlobalLeaderboardSnapshotModel.snapshot_date.desc())
            .limit(1),
        ).scalar_one_or_none()

    def _season_start_snapshot(self, *, race_class: str, as_of_date: date) -> GlobalLeaderboardSnapshotModel | None:
        season_start = date(as_of_date.year, as_of_date.month, 1)
        return self.session.execute(
            select(GlobalLeaderboardSnapshotModel)
            .where(
                GlobalLeaderboardSnapshotModel.race_class == race_class,
                GlobalLeaderboardSnapshotModel.snapshot_date >= season_start,
                GlobalLeaderboardSnapshotModel.snapshot_date <= as_of_date,
            )
            .order_by(GlobalLeaderboardSnapshotModel.snapshot_date.asc())
            .limit(1),
        ).scalar_one_or_none()

    def _snapshot_rows(self, snapshot_id: int) -> dict[str, dict]:
        rows = self.session.execute(
            select(GlobalLeaderboardRowModel, PilotModel.pilot)
            .join(PilotModel, PilotModel.id == GlobalLeaderboardRowModel.pilot_ref)
            .where(GlobalLeaderboardRowModel.snapshot_ref == snapshot_id),
        ).all()
        return {
            pilot: {
                "rank": row.rank,
                "league": row.league,
                "adjusted_average_gap": row.adjusted_average_gap,
            }
            for row, pilot in rows
        }

    def _latest_date(self, *, race_class: str) -> date | None:
        return self.session.execute(
            select(func.max(DaySpecModel.date)).where(DaySpecModel.race_class == race_class),
        ).scalar_one()

    @staticmethod
    def _adjusted_average(gaps: list[float]) -> tuple[float | None, float | None]:
        if not gaps:
            return None, None
        worst = max(gaps)
        values = list(gaps)
        if len(values) > 1:
            values.remove(worst)
        return round(sum(values) / len(values), 3), round(worst, 3) if len(gaps) > 1 else None

    @staticmethod
    def _league_for_rank(rank: int | None) -> str | None:
        if rank is None:
            return None
        if rank <= 10:
            return "gold"
        if rank <= 25:
            return "silver"
        return "bronze"

    @staticmethod
    def _target_league(*, row: dict) -> str | None:
        if row["rank"] is None:
            return "bronze"
        if row["rank"] <= 10:
            return None
        if row["rank"] <= 25:
            return "gold"
        return "silver"

    @staticmethod
    def _gap_to_target(*, row: dict, gold_cutoff: float | None, silver_cutoff: float | None) -> float | None:
        metric = row["adjusted_average_gap_percentage"]
        if metric is None:
            return None
        target_cutoff = gold_cutoff if row["target_league"] == "gold" else silver_cutoff
        if target_cutoff is None:
            return None
        return round(max(0.0, metric - target_cutoff), 3)

    @staticmethod
    def _rank_delta(current: int | None, previous: int | None) -> int | None:
        if current is None or previous is None:
            return None
        return previous - current

    @staticmethod
    def _gap_change(current: float | None, baseline: float | None) -> float | None:
        if current is None or baseline is None:
            return None
        return round(current - baseline, 3)

    @staticmethod
    def _league_delta(current: str | None, previous: str | None) -> str | None:
        if current is None or previous is None or current == previous:
            return None
        order = {"bronze": 1, "silver": 2, "gold": 3}
        if current not in order or previous not in order:
            return None
        return "up" if order[current] > order[previous] else "down"

    @staticmethod
    def _next_monday(value: date) -> date:
        days_ahead = (7 - value.weekday()) % 7 or 7
        return value + timedelta(days=days_ahead)

    @staticmethod
    def _next_month_start(value: date) -> date:
        if value.month == 12:
            return date(value.year + 1, 1, 1)
        return date(value.year, value.month + 1, 1)
