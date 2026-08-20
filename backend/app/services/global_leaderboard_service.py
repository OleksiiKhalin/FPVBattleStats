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
    ) -> dict:
        as_of = as_of_date or self._latest_date(race_class=race_class) or date.today()
        state = self._calculate_state(race_class=race_class, as_of_date=as_of)
        latest_snapshot = self._latest_snapshot(race_class=race_class, as_of_date=as_of)
        previous_snapshot = self._previous_snapshot(
            race_class=race_class,
            as_of_date=latest_snapshot.snapshot_date if latest_snapshot is not None else as_of,
        )
        previous_rows = self._snapshot_rows(previous_snapshot.id) if previous_snapshot is not None else {}

        rows = []
        for row in state["rows"]:
            forecasts = {
                "weekly": self._forecast(
                    row=row,
                    horizon=state["next_weekly_checkpoint"],
                    current_rows=state["rows"],
                    as_of_date=as_of,
                ),
                "monthly": self._forecast(
                    row=row,
                    horizon=state["next_month_start"],
                    current_rows=state["rows"],
                    as_of_date=as_of,
                ),
            }
            decorated = {
                key: value
                for key, value in row.items()
                if not key.startswith("_")
            }
            decorated["rank_delta"] = self._rank_delta(row["rank"], previous_rows.get(row["pilot"], {}).get("rank"))
            decorated["league_delta"] = self._league_delta(row["league"], previous_rows.get(row["pilot"], {}).get("league"))
            decorated["forecast_weekly"] = forecasts["weekly"]
            decorated["forecast_monthly"] = forecasts["monthly"]
            decorated["status"] = self._status_for(row=row, forecasts=forecasts)
            decorated["status_reason"] = self._status_reason(row=row, forecasts=forecasts)
            rows.append(decorated)

        selected = next((row for row in rows if row["pilot"] == selected_pilot), None)
        return {
            "race_class": race_class,
            "as_of_date": as_of,
            "window_from": state["window_from"],
            "window_to": state["window_to"],
            "last_official_snapshot_date": latest_snapshot.snapshot_date if latest_snapshot else None,
            "last_official_snapshot_kind": latest_snapshot.calculation_kind if latest_snapshot else None,
            "next_weekly_checkpoint": state["next_weekly_checkpoint"],
            "next_month_start": state["next_month_start"],
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
                    status=row["status"],
                    flight_days=row["flight_days"],
                    scored_days=row["scored_days"],
                    last_flight_date=row["last_flight_date"],
                    adjusted_average_gap=row["adjusted_average_gap"],
                    worst_day_gap=row["worst_day_gap"],
                ),
            )
        self.session.flush()
        return snapshot

    def _calculate_state(self, *, race_class: str, as_of_date: date) -> dict:
        window_from = as_of_date - timedelta(days=self.WINDOW_DAYS - 1)
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

        day_rows: dict[date, list[tuple[int, str, str | None, float]]] = defaultdict(list)
        for race_date, time_value, pilot_ref, pilot, country in raw_rows:
            day_rows[race_date].append((pilot_ref, pilot, country, float(time_value)))

        pilot_data: dict[str, dict] = {}
        for race_date, rows in day_rows.items():
            top_times = sorted(row[3] for row in rows)[:3]
            if not top_times:
                continue
            top_three_average = sum(top_times) / len(top_times)
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
                data["gaps"].append((race_date, time_value - top_three_average))

        rows = []
        for data in pilot_data.values():
            gaps = [gap for _, gap in data["gaps"]]
            adjusted_average_gap, worst_day_gap = self._adjusted_average(gaps)
            dates = sorted(set(data["dates"]))
            rows.append(
                {
                    "pilot_ref": data["pilot_ref"],
                    "pilot": data["pilot"],
                    "country": data["country"],
                    "rank": None,
                    "league": None,
                    "status": "qualified" if len(dates) >= self.MIN_FLIGHT_DAYS else "candidate",
                    "flight_days": len(dates),
                    "scored_days": len(gaps),
                    "last_flight_date": dates[-1] if dates else None,
                    "inactive_days": (as_of_date - dates[-1]).days if dates else self.WINDOW_DAYS,
                    "adjusted_average_gap": adjusted_average_gap,
                    "worst_day_gap": worst_day_gap,
                    "required_flight_days": max(0, self.MIN_FLIGHT_DAYS - len(dates)),
                    "_flight_dates": dates,
                    "_gaps": data["gaps"],
                },
            )

        qualified = sorted(
            [row for row in rows if row["flight_days"] >= self.MIN_FLIGHT_DAYS and row["adjusted_average_gap"] is not None],
            key=lambda row: (row["adjusted_average_gap"], row["pilot"]),
        )
        for index, row in enumerate(qualified, start=1):
            row["rank"] = index
            row["league"] = self._league_for_rank(index)

        qualified_by_pilot = {row["pilot"]: row for row in qualified}
        candidates = sorted(
            [row for row in rows if row["pilot"] not in qualified_by_pilot],
            key=lambda row: (row["adjusted_average_gap"] is None, row["adjusted_average_gap"] or math.inf, row["pilot"]),
        )
        rows = qualified + candidates
        gold_cutoff = qualified[9]["adjusted_average_gap"] if len(qualified) >= 10 else None
        silver_cutoff = qualified[24]["adjusted_average_gap"] if len(qualified) >= 25 else None
        for row in rows:
            row["target_league"] = self._target_league(row=row)
            row["gap_to_next_league"] = self._gap_to_target(
                row=row,
                gold_cutoff=gold_cutoff,
                silver_cutoff=silver_cutoff,
            )

        return {
            "window_from": window_from,
            "window_to": as_of_date,
            "next_weekly_checkpoint": self._next_monday(as_of_date),
            "next_month_start": self._next_month_start(as_of_date),
            "rows": rows,
        }

    def _forecast(
        self,
        *,
        row: dict,
        horizon: date,
        current_rows: list[dict],
        as_of_date: date,
    ) -> dict:
        window_from = horizon - timedelta(days=self.WINDOW_DAYS - 1)
        current_dates = set(row["_flight_dates"])
        current_gaps = {race_date: gap for race_date, gap in row["_gaps"]}
        retained_dates = {race_date for race_date in current_dates if race_date >= window_from}
        retained_gaps = [gap for race_date, gap in current_gaps.items() if race_date >= window_from]
        future_dates = {
            as_of_date + timedelta(days=offset)
            for offset in range(1, max(0, (horizon - as_of_date).days) + 1)
        }
        continue_dates = retained_dates | future_dates
        projected_gap = row["adjusted_average_gap"]
        continue_gaps = retained_gaps + ([projected_gap] * len(future_dates) if projected_gap is not None else [])
        no_flight_average, _ = self._adjusted_average(retained_gaps)
        continue_average, _ = self._adjusted_average(continue_gaps)
        no_flight_rank = self._projected_rank(
            pilot=row["pilot"],
            metric=no_flight_average,
            qualified=len(retained_dates) >= self.MIN_FLIGHT_DAYS and no_flight_average is not None,
            current_rows=current_rows,
        )
        continue_rank = self._projected_rank(
            pilot=row["pilot"],
            metric=continue_average,
            qualified=len(continue_dates) >= self.MIN_FLIGHT_DAYS and continue_average is not None,
            current_rows=current_rows,
        )
        return {
            "checkpoint_date": horizon,
            "no_flight_days": len(retained_dates),
            "continue_flight_days": len(continue_dates),
            "no_flight_adjusted_average_gap": no_flight_average,
            "continue_adjusted_average_gap": continue_average,
            "no_flight_rank": no_flight_rank,
            "no_flight_league": self._league_for_rank(no_flight_rank),
            "continue_rank": continue_rank,
            "continue_league": self._league_for_rank(continue_rank),
            "days_needed_to_qualify": max(0, self.MIN_FLIGHT_DAYS - len(continue_dates)),
            "can_qualify_if_active": len(continue_dates) >= self.MIN_FLIGHT_DAYS and continue_average is not None,
        }

    def _projected_rank(self, *, pilot: str, metric: float | None, qualified: bool, current_rows: list[dict]) -> int | None:
        if not qualified or metric is None:
            return None
        competitors = [
            row
            for row in current_rows
            if row["pilot"] != pilot and row["rank"] is not None and row["adjusted_average_gap"] is not None
        ]
        better = sum(
            1
            for row in competitors
            if row["adjusted_average_gap"] < metric
            or (math.isclose(row["adjusted_average_gap"], metric) and row["pilot"] < pilot)
        )
        return better + 1

    def _status_for(self, *, row: dict, forecasts: dict[str, dict]) -> str:
        if row["flight_days"] >= self.MIN_FLIGHT_DAYS:
            if forecasts["weekly"]["no_flight_days"] < self.MIN_FLIGHT_DAYS or forecasts["monthly"]["no_flight_days"] < self.MIN_FLIGHT_DAYS:
                return "at_risk"
            return "qualified"
        if not forecasts["monthly"]["can_qualify_if_active"]:
            return "guaranteed_out"
        return "candidate"

    def _status_reason(self, *, row: dict, forecasts: dict[str, dict]) -> str:
        status = self._status_for(row=row, forecasts=forecasts)
        if status == "at_risk":
            checkpoint = forecasts["weekly"] if forecasts["weekly"]["no_flight_days"] < self.MIN_FLIGHT_DAYS else forecasts["monthly"]
            return f"Без нового польоту до {checkpoint['checkpoint_date']} залишиться лише {checkpoint['no_flight_days']} із {self.MIN_FLIGHT_DAYS} потрібних днів."
        if status == "guaranteed_out":
            return f"Навіть за щоденних польотів до {forecasts['monthly']['checkpoint_date']} неможливо набрати {self.MIN_FLIGHT_DAYS} днів."
        if status == "candidate":
            return f"Потрібно ще {row['required_flight_days']} flight-days; за поточним gap пілот може потрапити в рейтинг."
        return "Кваліфікація збережена за поточним сценарієм активності."

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

    def _snapshot_rows(self, snapshot_id: int) -> dict[str, dict]:
        rows = self.session.execute(
            select(GlobalLeaderboardRowModel, PilotModel.pilot)
            .join(PilotModel, PilotModel.id == GlobalLeaderboardRowModel.pilot_ref)
            .where(GlobalLeaderboardRowModel.snapshot_ref == snapshot_id),
        ).all()
        return {
            pilot: {"rank": row.rank, "league": row.league}
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
        if row["adjusted_average_gap"] is None:
            return None
        target_cutoff = gold_cutoff if row["target_league"] == "gold" else silver_cutoff if row["target_league"] == "silver" else silver_cutoff
        if target_cutoff is None:
            return None
        return round(max(0.0, row["adjusted_average_gap"] - target_cutoff), 3)

    @staticmethod
    def _rank_delta(current: int | None, previous: int | None) -> int | None:
        if current is None or previous is None:
            return None
        return previous - current

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
