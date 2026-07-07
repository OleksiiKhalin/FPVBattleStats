from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fpvbattle_core.db.models import DaySpecModel, PilotModel, ResultModel, SeasonLeaderboardModel


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_scoreboard(self, *, target_date: date, race_class: str) -> dict | None:
        day_spec = self.session.execute(
            select(DaySpecModel).where(DaySpecModel.date == target_date, DaySpecModel.race_class == race_class),
        ).scalar_one_or_none()
        if day_spec is None:
            return None

        rows = self.session.execute(
            select(ResultModel, PilotModel)
            .join(PilotModel, PilotModel.id == ResultModel.pilot_ref)
            .where(ResultModel.day_spec_ref == day_spec.id)
            .order_by(ResultModel.category.is_(None), ResultModel.category, ResultModel.place, PilotModel.pilot),
        ).all()

        return {
            "date": day_spec.date,
            "race_class": day_spec.race_class,
            "season": day_spec.season,
            "track": day_spec.track,
            "quad_of_the_day": day_spec.quad_of_the_day,
            "rows": [
                {
                    "place": result.place,
                    "pilot": pilot.pilot,
                    "country": pilot.country,
                    "category": result.category,
                    "quad": result.quad,
                    "time": result.time,
                    "points": result.points,
                }
                for result, pilot in rows
            ],
        }

    def list_pilots(self, *, race_class: str | None = None) -> list[dict]:
        statement = (
            select(PilotModel.pilot, PilotModel.country)
            .join(ResultModel, ResultModel.pilot_ref == PilotModel.id)
            .join(DaySpecModel, DaySpecModel.id == ResultModel.day_spec_ref)
        )
        if race_class:
            statement = statement.where(DaySpecModel.race_class == race_class)

        rows = self.session.execute(statement.distinct().order_by(PilotModel.pilot)).all()
        return [{"pilot": pilot, "country": country} for pilot, country in rows]

    def get_pilot_stats(
        self,
        *,
        pilot_name: str,
        race_class: str,
        date_from: date | None,
        date_to: date | None,
        streak_threshold: int,
    ) -> dict:
        threshold = max(streak_threshold, 3)
        day_specs = self._get_day_specs(race_class=race_class, date_from=date_from, date_to=date_to)
        if not day_specs:
            return {
                "pilot": pilot_name,
                "race_class": race_class,
                "date_from": date_from,
                "date_to": date_to,
                "timeline": [],
                "active_timeline": [],
                "streaks": {
                    "threshold": threshold,
                    "streaks": [],
                    "lonely_single_days": 0,
                    "lonely_two_day_runs": 0,
                },
            }

        results_by_day = self._results_by_day([day_spec.id for day_spec in day_specs])
        timeline: list[dict] = []
        active_dates: list[date] = []

        for day_spec in day_specs:
            day_results = results_by_day.get(day_spec.id, [])
            point = self._build_pilot_timeline_point(day_spec=day_spec, day_results=day_results, pilot_name=pilot_name)
            timeline.append(point)
            if point["participated"]:
                active_dates.append(day_spec.date)

        return {
            "pilot": pilot_name,
            "race_class": race_class,
            "date_from": date_from,
            "date_to": date_to,
            "timeline": timeline,
            "active_timeline": [point for point in timeline if point["participated"]],
            "streaks": self._calculate_streaks(active_dates, threshold=threshold),
        }

    def get_pilot_hover_card(self, *, pilot_name: str, race_class: str, target_date: date) -> dict:
        target_day = self.session.execute(
            select(DaySpecModel).where(DaySpecModel.race_class == race_class, DaySpecModel.date == target_date),
        ).scalar_one_or_none()
        if target_day is None:
            season = target_date.strftime("%Y-%m")
        else:
            season = target_day.season

        season_days = self.session.execute(
            select(DaySpecModel).where(
                DaySpecModel.race_class == race_class,
                DaySpecModel.season == season,
                DaySpecModel.date <= target_date,
            ).order_by(DaySpecModel.date),
        ).scalars().all()

        if not season_days:
            return {
                "pilot": pilot_name,
                "race_class": race_class,
                "season": season,
                "target_date": target_date,
                "skipped_days": 0,
                "appearances": 0,
                "timeline": [],
            }

        pilot_rows = self.session.execute(
            select(DaySpecModel.date, ResultModel.place)
            .join(ResultModel, ResultModel.day_spec_ref == DaySpecModel.id)
            .join(PilotModel, PilotModel.id == ResultModel.pilot_ref)
            .where(
                DaySpecModel.race_class == race_class,
                DaySpecModel.season == season,
                DaySpecModel.date <= target_date,
                PilotModel.pilot == pilot_name,
            )
            .order_by(DaySpecModel.date),
        ).all()
        place_by_date = {race_date: place for race_date, place in pilot_rows}
        timeline = []
        skipped_days = 0
        appearances = 0
        for day in season_days:
            place = place_by_date.get(day.date)
            participated = place is not None
            if participated:
                appearances += 1
            else:
                skipped_days += 1
            timeline.append(
                {
                    "date": day.date,
                    "participated": participated,
                    "place": place,
                    "skipped": 0 if participated else 1,
                },
            )

        return {
            "pilot": pilot_name,
            "race_class": race_class,
            "season": season,
            "target_date": target_date,
            "skipped_days": skipped_days,
            "appearances": appearances,
            "timeline": timeline,
        }

    def get_general_stats(
        self,
        *,
        race_class: str,
        date_from: date | None,
        date_to: date | None,
        selected_pilot: str | None,
    ) -> dict:
        day_specs = self._get_day_specs(race_class=race_class, date_from=date_from, date_to=date_to)
        day_spec_ids = [day_spec.id for day_spec in day_specs]
        results_by_day = self._results_by_day(day_spec_ids)
        latest_season_day_ids = self._latest_season_day_ids(day_specs)
        season_rows = self._season_rows_by_day(latest_season_day_ids)
        full_history_rows = self._results_with_dates(race_class=race_class)
        consistency_rows = self._build_consistency_rows(full_history_rows)

        return {
            "race_class": race_class,
            "date_from": date_from,
            "date_to": date_to,
            "selected_pilot": selected_pilot,
            "countries": self._build_country_rows(season_rows),
            "quads": self._build_quad_rows(results_by_day),
            "track_ratings": self._build_track_ratings(day_specs),
            "seasons": self._build_season_rows(day_specs, results_by_day, season_rows),
            "participation": self._build_participation_stats(day_specs, results_by_day),
            "selected_pilot_consistency": next((row for row in consistency_rows if row["pilot"] == selected_pilot), None),
            "consistency_leaderboard": consistency_rows,
            "best_improvement": [
                row
                for row in sorted(
                    [row for row in consistency_rows if row["improvement_score"] is not None],
                    key=lambda item: item["improvement_score"],
                    reverse=True,
                )[:15]
            ],
        }

    def _get_day_specs(self, *, race_class: str, date_from: date | None, date_to: date | None) -> list[DaySpecModel]:
        statement = select(DaySpecModel).where(DaySpecModel.race_class == race_class)
        if date_from is not None:
            statement = statement.where(DaySpecModel.date >= date_from)
        if date_to is not None:
            statement = statement.where(DaySpecModel.date <= date_to)
        return list(self.session.execute(statement.order_by(DaySpecModel.date)).scalars().all())

    def _results_by_day(self, day_spec_ids: list[int]) -> dict[int, list[dict]]:
        if not day_spec_ids:
            return {}
        rows = self.session.execute(
            select(
                ResultModel.day_spec_ref,
                ResultModel.category,
                ResultModel.quad,
                ResultModel.time,
                ResultModel.points,
                ResultModel.place,
                PilotModel.pilot,
                PilotModel.country,
            )
            .join(PilotModel, PilotModel.id == ResultModel.pilot_ref)
            .where(ResultModel.day_spec_ref.in_(day_spec_ids))
            .order_by(ResultModel.day_spec_ref, ResultModel.place, PilotModel.pilot),
        ).all()

        payload: dict[int, list[dict]] = defaultdict(list)
        for day_spec_ref, category, quad, time_value, points, place, pilot, country in rows:
            payload[day_spec_ref].append(
                {
                    "category": category,
                    "quad": quad,
                    "time": time_value,
                    "points": points,
                    "place": place,
                    "pilot": pilot,
                    "country": country,
                },
            )
        return payload

    def _results_with_dates(self, *, race_class: str) -> list[dict]:
        rows = self.session.execute(
            select(
                DaySpecModel.date,
                ResultModel.place,
                PilotModel.pilot,
                PilotModel.country,
            )
            .join(ResultModel, ResultModel.day_spec_ref == DaySpecModel.id)
            .join(PilotModel, PilotModel.id == ResultModel.pilot_ref)
            .where(DaySpecModel.race_class == race_class)
            .order_by(PilotModel.pilot, DaySpecModel.date),
        ).all()
        return [
            {
                "date": race_date,
                "place": place,
                "pilot": pilot,
                "country": country,
            }
            for race_date, place, pilot, country in rows
        ]

    def _latest_season_day_ids(self, day_specs: list[DaySpecModel]) -> list[int]:
        latest_by_season: dict[str, DaySpecModel] = {}
        for day_spec in day_specs:
            latest_by_season[day_spec.season] = day_spec
        return [day_spec.id for day_spec in latest_by_season.values()]

    def _season_rows_by_day(self, day_spec_ids: list[int]) -> dict[int, list[dict]]:
        if not day_spec_ids:
            return {}
        rows = self.session.execute(
            select(
                SeasonLeaderboardModel.day_spec_ref,
                SeasonLeaderboardModel.points,
                SeasonLeaderboardModel.place,
                SeasonLeaderboardModel.category,
                PilotModel.pilot,
                PilotModel.country,
            )
            .join(PilotModel, PilotModel.id == SeasonLeaderboardModel.pilot_ref)
            .where(SeasonLeaderboardModel.day_spec_ref.in_(day_spec_ids))
            .order_by(SeasonLeaderboardModel.day_spec_ref, SeasonLeaderboardModel.place, PilotModel.pilot),
        ).all()

        payload: dict[int, list[dict]] = defaultdict(list)
        for day_spec_ref, points, place, category, pilot, country in rows:
            payload[day_spec_ref].append(
                {
                    "points": points,
                    "place": place,
                    "category": category,
                    "pilot": pilot,
                    "country": country,
                },
            )
        return payload

    def _build_pilot_timeline_point(self, *, day_spec: DaySpecModel, day_results: list[dict], pilot_name: str) -> dict:
        timed_results = [row for row in day_results if row["time"] is not None]
        timed_results.sort(key=lambda row: row["time"])
        top_times = [row["time"] for row in timed_results[:3]]
        leader_average = round(sum(top_times) / len(top_times), 3) if top_times else None
        leader_time = round(timed_results[0]["time"], 3) if timed_results else None
        field_average = round(sum(row["time"] for row in timed_results) / len(timed_results), 3) if timed_results else None
        participant_count = len(day_results)
        pilot_row = next((row for row in day_results if row["pilot"] == pilot_name), None)
        if pilot_row is None:
            return {
                "date": day_spec.date,
                "participated": False,
                "pilot_time": None,
                "leader_average_time": leader_average,
                "leader_time": leader_time,
                "field_average_time": field_average,
                "gap_to_leader_average": None,
                "gap_to_leader": None,
                "normalized_score": None,
                "place": None,
                "participant_count": participant_count,
            }

        pilot_time = round(pilot_row["time"], 3) if pilot_row["time"] is not None else None
        worst_time = round(timed_results[-1]["time"], 3) if timed_results else None
        normalized_score = None
        if pilot_time is not None and leader_time is not None:
            if worst_time is None or math.isclose(worst_time, leader_time):
                normalized_score = 100.0
            else:
                normalized_score = round(max(0.0, min(100.0, ((worst_time - pilot_time) / (worst_time - leader_time)) * 100.0)), 2)

        return {
            "date": day_spec.date,
            "participated": True,
            "pilot_time": pilot_time,
            "leader_average_time": leader_average,
            "leader_time": leader_time,
            "field_average_time": field_average,
            "gap_to_leader_average": round(pilot_time - leader_average, 3) if pilot_time is not None and leader_average is not None else None,
            "gap_to_leader": round(pilot_time - leader_time, 3) if pilot_time is not None and leader_time is not None else None,
            "normalized_score": normalized_score,
            "place": pilot_row["place"],
            "participant_count": participant_count,
        }

    def _calculate_streaks(self, dates: list[date], *, threshold: int) -> dict:
        streaks: list[list[date]] = []
        singles = 0
        two_day_runs = 0
        current: list[date] = []

        for race_date in dates:
            if not current or race_date == current[-1] + timedelta(days=1):
                current.append(race_date)
                continue

            singles, two_day_runs = self._append_streak_summary(
                current=current,
                threshold=threshold,
                streaks=streaks,
                singles=singles,
                two_day_runs=two_day_runs,
            )
            current = [race_date]

        if current:
            singles, two_day_runs = self._append_streak_summary(
                current=current,
                threshold=threshold,
                streaks=streaks,
                singles=singles,
                two_day_runs=two_day_runs,
            )

        return {
            "threshold": threshold,
            "streaks": [
                {
                    "start_date": group[0],
                    "end_date": group[-1],
                    "length": len(group),
                    "dates": group,
                }
                for group in streaks
            ],
            "lonely_single_days": singles,
            "lonely_two_day_runs": two_day_runs,
        }

    def _build_country_rows(self, season_rows_by_day: dict[int, list[dict]]) -> list[dict]:
        by_country: dict[str | None, dict] = defaultdict(
            lambda: {
                "pilots": set(),
                "scores": [],
                "places": [],
                "season_wins": 0,
                "gold_medals": 0,
                "silver_medals": 0,
                "bronze_medals": 0,
            },
        )

        for rows in season_rows_by_day.values():
            for row in rows:
                country_bucket = by_country[row["country"]]
                country_bucket["pilots"].add(row["pilot"])
                if row["points"] is not None:
                    country_bucket["scores"].append(row["points"])
                if row["place"] is not None:
                    country_bucket["places"].append(row["place"])
                    if row["place"] == 1:
                        country_bucket["season_wins"] += 1
                        country_bucket["gold_medals"] += 1
                    elif row["place"] == 2:
                        country_bucket["silver_medals"] += 1
                    elif row["place"] == 3:
                        country_bucket["bronze_medals"] += 1

        rows: list[dict] = []
        for country, bucket in by_country.items():
            pilot_count = len(bucket["pilots"])
            medals_total = bucket["gold_medals"] + bucket["silver_medals"] + bucket["bronze_medals"]
            rows.append(
                {
                    "country": country,
                    "unique_pilots": pilot_count,
                    "avg_season_score": round(sum(bucket["scores"]) / len(bucket["scores"]), 2) if bucket["scores"] else None,
                    "avg_place": round(sum(bucket["places"]) / len(bucket["places"]), 2) if bucket["places"] else None,
                    "season_wins": bucket["season_wins"],
                    "gold_medals": bucket["gold_medals"],
                    "silver_medals": bucket["silver_medals"],
                    "bronze_medals": bucket["bronze_medals"],
                    "medals_per_pilot": round(medals_total / pilot_count, 2) if pilot_count else None,
                },
            )
        return sorted(rows, key=lambda row: (-row["unique_pilots"], row["country"] or ""))

    def _build_quad_rows(self, results_by_day: dict[int, list[dict]]) -> list[dict]:
        total_entries = sum(len(rows) for rows in results_by_day.values())
        stats: dict[tuple[str, str | None], dict] = defaultdict(
            lambda: {"entries": 0, "pilots": set(), "places": [], "wins": 0},
        )

        for rows in results_by_day.values():
            for row in rows:
                if not row["quad"]:
                    continue
                key = (row["quad"], row["category"])
                bucket = stats[key]
                bucket["entries"] += 1
                bucket["pilots"].add(row["pilot"])
                if row["place"] is not None:
                    bucket["places"].append(row["place"])
                    if row["place"] == 1:
                        bucket["wins"] += 1

        payload: list[dict] = []
        for (quad, category), bucket in stats.items():
            payload.append(
                {
                    "quad": quad,
                    "category": category,
                    "entries": bucket["entries"],
                    "usage_percentage": round((bucket["entries"] / total_entries) * 100, 2) if total_entries else 0.0,
                    "unique_pilots": len(bucket["pilots"]),
                    "avg_place": round(sum(bucket["places"]) / len(bucket["places"]), 2) if bucket["places"] else None,
                    "wins": bucket["wins"],
                },
            )
        return sorted(payload, key=lambda row: (-row["entries"], row["quad"], row["category"] or ""))

    def _build_track_ratings(self, day_specs: list[DaySpecModel]) -> list[dict]:
        unique_tracks = sorted({day_spec.track for day_spec in day_specs if day_spec.track})
        rows: list[dict] = []
        for track in unique_tracks:
            seed = sum(ord(char) for char in track)
            votes = 12 + seed % 89
            average_score = round(3.2 + ((seed % 170) / 100), 2)
            weighted_score = round(average_score * math.log10(votes + 10), 2)
            rows.append(
                {
                    "track": track,
                    "votes": votes,
                    "average_score": average_score,
                    "weighted_score": weighted_score,
                },
            )
        return sorted(rows, key=lambda row: (-row["weighted_score"], -row["votes"], row["track"]))

    def _build_season_rows(
        self,
        day_specs: list[DaySpecModel],
        results_by_day: dict[int, list[dict]],
        season_rows_by_day: dict[int, list[dict]],
    ) -> list[dict]:
        day_specs_by_season: dict[str, list[DaySpecModel]] = defaultdict(list)
        for day_spec in day_specs:
            day_specs_by_season[day_spec.season].append(day_spec)

        rows: list[dict] = []
        for season, season_days in sorted(day_specs_by_season.items()):
            latest_day = season_days[-1]
            season_rows = season_rows_by_day.get(latest_day.id, [])
            unique_pilots = len({row["pilot"] for row in season_rows})
            consistent_pilots = 0
            appearances_by_pilot: dict[str, int] = defaultdict(int)
            for day_spec in season_days:
                for result in results_by_day.get(day_spec.id, []):
                    appearances_by_pilot[result["pilot"]] += 1
            threshold = max(3, math.ceil(len(season_days) * 0.5))
            consistent_pilots = sum(1 for appearances in appearances_by_pilot.values() if appearances >= threshold)

            largest_margin = None
            for day_spec in season_days:
                timed = sorted(
                    [row["time"] for row in results_by_day.get(day_spec.id, []) if row["time"] is not None],
                )
                if len(timed) >= 2:
                    margin = round(timed[1] - timed[0], 3)
                    if largest_margin is None or margin > largest_margin:
                        largest_margin = margin

            rows.append(
                {
                    "season": season,
                    "unique_pilots": unique_pilots,
                    "consistent_pilots": consistent_pilots,
                    "largest_victory_margin": largest_margin,
                },
            )
        return rows

    def _build_participation_stats(self, day_specs: list[DaySpecModel], results_by_day: dict[int, list[dict]]) -> dict:
        daily_counts = [
            {"date": day_spec.date, "participants": len(results_by_day.get(day_spec.id, []))}
            for day_spec in day_specs
        ]
        counts = [row["participants"] for row in daily_counts]
        average_participants = round(sum(counts) / len(counts), 2) if counts else 0.0
        peak = max(daily_counts, key=lambda row: row["participants"], default=None)
        lowest = min(daily_counts, key=lambda row: row["participants"], default=None)
        trend = None
        if len(daily_counts) >= 2:
            trend = round(daily_counts[-1]["participants"] - daily_counts[0]["participants"], 2)
        return {
            "daily_counts": daily_counts,
            "average_participants": average_participants,
            "peak_participation_day": peak,
            "lowest_participation_day": lowest,
            "participation_trend": trend,
        }

    def _build_consistency_rows(self, rows_with_dates: list[dict]) -> list[dict]:
        pilot_results: dict[str, list[dict]] = defaultdict(list)
        for row in rows_with_dates:
            pilot_results[row["pilot"]].append(row)

        rows: list[dict] = []
        for pilot, results in pilot_results.items():
            places = [row["place"] for row in results if row["place"] is not None]
            if not places:
                continue
            average_place = sum(places) / len(places)
            dispersion = self._mean_absolute_deviation(places)
            consistency_score = round(self._calculate_consistency_score(appearances=len(places), dispersion=dispersion), 2)

            improvement_score = None
            if len(places) >= 6:
                improvement_score = round(self._calculate_improvement_score(places), 4)

            rows.append(
                {
                    "pilot": pilot,
                    "country": results[0]["country"],
                    "appearances": len(places),
                    "average_place": round(average_place, 2),
                    "dispersion": round(dispersion, 3),
                    "consistency_score": consistency_score,
                    "first_flight_date": results[0]["date"],
                    "last_flight_date": results[-1]["date"],
                    "improvement_score": improvement_score,
                },
            )
        return sorted(rows, key=lambda row: (-row["consistency_score"], row["average_place"] or 999, row["pilot"]))

    def _mean_absolute_deviation(self, values: list[int]) -> float:
        if not values:
            return 0.0
        average = sum(values) / len(values)
        return sum(abs(value - average) for value in values) / len(values)

    def _calculate_consistency_score(self, *, appearances: int, dispersion: float) -> float:
        appearance_weight = 1.0 + math.log1p(appearances) / 6.0
        return max(0.0, (100.0 / (1.0 + dispersion)) * appearance_weight)

    def _calculate_improvement_score(self, places: list[int]) -> float:
        if len(places) < 2:
            return 0.0
        x_values = list(range(len(places)))
        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(places) / len(places)
        denominator = sum((x_value - x_mean) ** 2 for x_value in x_values)
        if math.isclose(denominator, 0.0):
            return 0.0
        numerator = sum((x_value - x_mean) * (place - y_mean) for x_value, place in zip(x_values, places, strict=False))
        slope = numerator / denominator
        return -slope

    def _append_streak_summary(
        self,
        *,
        current: list[date],
        threshold: int,
        streaks: list[list[date]],
        singles: int,
        two_day_runs: int,
    ) -> tuple[int, int]:
        if len(current) >= threshold:
            streaks.append(list(current))
        elif len(current) == 1:
            singles += 1
        elif len(current) == 2:
            two_day_runs += 1
        return singles, two_day_runs
