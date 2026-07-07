from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..dependencies import get_session
from ...schemas.analytics import GeneralStatsResponse, PilotHoverCardResponse, PilotOption, PilotStatsResponse
from ...services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/pilots", response_model=list[PilotOption])
def list_pilots(
    race_class: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[PilotOption]:
    rows = AnalyticsService(session).list_pilots(race_class=race_class)
    return [PilotOption.model_validate(row) for row in rows]


@router.get("/pilot-stats/{race_class}/{pilot_name}", response_model=PilotStatsResponse)
def get_pilot_stats(
    race_class: str,
    pilot_name: str,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    streak_threshold: int = Query(default=3, ge=3),
    session: Session = Depends(get_session),
) -> PilotStatsResponse:
    payload = AnalyticsService(session).get_pilot_stats(
        pilot_name=pilot_name,
        race_class=race_class,
        date_from=date_from,
        date_to=date_to,
        streak_threshold=streak_threshold,
    )
    return PilotStatsResponse.model_validate(payload)


@router.get("/pilot-hover/{race_class}/{pilot_name}", response_model=PilotHoverCardResponse)
def get_pilot_hover_card(
    race_class: str,
    pilot_name: str,
    target_date: date = Query(...),
    session: Session = Depends(get_session),
) -> PilotHoverCardResponse:
    payload = AnalyticsService(session).get_pilot_hover_card(
        pilot_name=pilot_name,
        race_class=race_class,
        target_date=target_date,
    )
    return PilotHoverCardResponse.model_validate(payload)


@router.get("/general-stats/{race_class}", response_model=GeneralStatsResponse)
def get_general_stats(
    race_class: str,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    pilot_name: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> GeneralStatsResponse:
    payload = AnalyticsService(session).get_general_stats(
        race_class=race_class,
        date_from=date_from,
        date_to=date_to,
        selected_pilot=pilot_name,
    )
    return GeneralStatsResponse.model_validate(payload)
