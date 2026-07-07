from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import case, func, select
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

    def get_pilot_timeline(self, *, pilot_name: str, race_class: str, season: str | None) -> list[dict]:
        statement = (
            select(DaySpecModel.date, ResultModel.time, DaySpecModel.id)
            .join(ResultModel, ResultModel.day_spec_ref == DaySpecModel.id)
            .join(PilotModel, PilotModel.id == ResultModel.pilot_ref)
            .where(PilotModel.pilot == pilot_name, DaySpecModel.race_class == race_class)
            .order_by(DaySpecModel.date)
        )
        if season:
            statement = statement.where(DaySpecModel.season == season)

        pilot_rows = self.session.execute(statement).all()
        if not pilot_rows:
            return []

        timeline = []
        for race_date, pilot_time, day_spec_id in pilot_rows:
            top_times = self.session.execute(
                select(ResultModel.time)
                .where(ResultModel.day_spec_ref == day_spec_id, ResultModel.time.is_not(None))
                .order_by(ResultModel.time)
                .limit(3),
            ).scalars().all()
            field_times = self.session.execute(
                select(ResultModel.time)
                .where(ResultModel.day_spec_ref == day_spec_id, ResultModel.time.is_not(None)),
            ).scalars().all()
            leader_average = round(sum(top_times) / len(top_times), 3) if top_times else None
            field_average = round(sum(field_times) / len(field_times), 3) if field_times else None
            gap = round(pilot_time - leader_average, 3) if pilot_time is not None and leader_average is not None else None
            timeline.append(
                {
                    "date": race_date,
                    "pilot_time": pilot_time,
                    "leader_average_time": leader_average,
                    "field_average_time": field_average,
                    "gap_to_leader_average": gap,
                },
            )
        return timeline

    def get_country_stats(self, *, race_class: str, season: str | None) -> list[dict]:
        statement = (
            select(
                PilotModel.country,
                func.count(func.distinct(PilotModel.id)),
                func.avg(SeasonLeaderboardModel.points),
                func.avg(SeasonLeaderboardModel.place),
                func.sum(case((SeasonLeaderboardModel.place == 1, 1), else_=0)),
                func.sum(case((SeasonLeaderboardModel.place == 1, 1), else_=0)),
                func.sum(case((SeasonLeaderboardModel.place == 2, 1), else_=0)),
                func.sum(case((SeasonLeaderboardModel.place == 3, 1), else_=0)),
            )
            .join(PilotModel, PilotModel.id == SeasonLeaderboardModel.pilot_ref)
            .join(DaySpecModel, DaySpecModel.id == SeasonLeaderboardModel.day_spec_ref)
            .where(DaySpecModel.race_class == race_class)
            .group_by(PilotModel.country)
            .order_by(func.count(func.distinct(PilotModel.id)).desc(), PilotModel.country)
        )
        if season:
            statement = statement.where(DaySpecModel.season == season)

        return [
            {
                "country": country,
                "unique_pilots": unique_pilots or 0,
                "avg_season_score": round(avg_score, 2) if avg_score is not None else None,
                "avg_place": round(avg_place, 2) if avg_place is not None else None,
                "season_wins": season_wins or 0,
                "gold_medals": gold_medals or 0,
                "silver_medals": silver_medals or 0,
                "bronze_medals": bronze_medals or 0,
            }
            for country, unique_pilots, avg_score, avg_place, season_wins, gold_medals, silver_medals, bronze_medals in self.session.execute(statement).all()
        ]

    def get_pilot_streaks(self, *, pilot_name: str, race_class: str, threshold: int = 3) -> dict:
        threshold = max(threshold, 3)
        dates = self.session.execute(
            select(DaySpecModel.date)
            .join(ResultModel, ResultModel.day_spec_ref == DaySpecModel.id)
            .join(PilotModel, PilotModel.id == ResultModel.pilot_ref)
            .where(PilotModel.pilot == pilot_name, DaySpecModel.race_class == race_class)
            .order_by(DaySpecModel.date),
        ).scalars().all()

        streaks: list[list[date]] = []
        singles = 0
        two_day_runs = 0
        current: list[date] = []

        for race_date in dates:
            if not current or race_date == current[-1] + timedelta(days=1):
                current.append(race_date)
            else:
                if len(current) >= threshold:
                    streaks.append(current)
                elif len(current) == 1:
                    singles += 1
                elif len(current) == 2:
                    two_day_runs += 1
                current = [race_date]

        if current:
            if len(current) >= threshold:
                streaks.append(current)
            elif len(current) == 1:
                singles += 1
            elif len(current) == 2:
                two_day_runs += 1

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
