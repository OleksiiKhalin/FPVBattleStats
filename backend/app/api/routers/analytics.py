from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..dependencies import get_session
from ...schemas.analytics import CountryStatsRow, PilotAnalyticsResponse
from ...services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/countries/{race_class}", response_model=list[CountryStatsRow])
def get_country_stats(
    race_class: str,
    season: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[CountryStatsRow]:
    rows = AnalyticsService(session).get_country_stats(race_class=race_class, season=season)
    return [CountryStatsRow.model_validate(row) for row in rows]


@router.get("/pilots/{race_class}/{pilot_name}", response_model=PilotAnalyticsResponse)
def get_pilot_analytics(
    race_class: str,
    pilot_name: str,
    season: str | None = Query(default=None),
    streak_threshold: int = Query(default=3, ge=3),
    session: Session = Depends(get_session),
) -> PilotAnalyticsResponse:
    service = AnalyticsService(session)
    return PilotAnalyticsResponse.model_validate(
        {
            "pilot": pilot_name,
            "race_class": race_class,
            "season": season,
            "points_timeline": service.get_pilot_timeline(pilot_name=pilot_name, race_class=race_class, season=season),
            "streaks": service.get_pilot_streaks(
                pilot_name=pilot_name,
                race_class=race_class,
                threshold=streak_threshold,
            ),
        },
    )
