from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..dependencies import get_session
from ...schemas.scoreboard import ScoreboardResponse
from ...services.analytics_service import AnalyticsService

router = APIRouter(prefix="/scoreboards", tags=["scoreboards"])


@router.get("/{race_class}/{target_date}", response_model=ScoreboardResponse)
def get_scoreboard(race_class: str, target_date: date, session: Session = Depends(get_session)) -> ScoreboardResponse:
    payload = AnalyticsService(session).get_scoreboard(target_date=target_date, race_class=race_class)
    if payload is None:
        raise HTTPException(status_code=404, detail="Scoreboard not found")
    return ScoreboardResponse.model_validate(payload)
