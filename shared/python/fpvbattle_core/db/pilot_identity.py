from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from fpvbattle_core.db.models import (
    GlobalLeaderboardRowModel,
    PilotModel,
    ResultModel,
    SeasonLeaderboardModel,
)
from fpvbattle_core.domain.pilots import canonicalize_pilot_name


def merge_pilot_aliases(session: Session) -> None:
    """Merge stored alias rows into their canonical pilot rows.

    This is intentionally idempotent so it can run during database bootstrap. If
    an alias and canonical pilot both have a row for the same logical parent, the
    canonical row is retained and the duplicate alias row is removed.
    """
    pilots = list(session.execute(select(PilotModel)).scalars())
    pilots_by_name = {pilot.pilot.casefold(): pilot for pilot in pilots}

    for source in pilots:
        canonical_name = canonicalize_pilot_name(source.pilot)
        if canonical_name == source.pilot:
            continue

        target = pilots_by_name.get(canonical_name.casefold())
        if target is None:
            source.pilot = canonical_name
            pilots_by_name[canonical_name.casefold()] = source
            continue
        if target.id == source.id:
            continue

        if not target.country and source.country:
            target.country = source.country
        _merge_result_rows(session, source_id=source.id, target_id=target.id)
        _merge_season_rows(session, source_id=source.id, target_id=target.id)
        _merge_global_rows(session, source_id=source.id, target_id=target.id)
        session.flush()
        session.delete(source)

    session.flush()


def _merge_result_rows(session: Session, *, source_id: int, target_id: int) -> None:
    source_rows = list(
        session.execute(select(ResultModel).where(ResultModel.pilot_ref == source_id)).scalars(),
    )
    target_days = set(
        session.execute(
            select(ResultModel.day_spec_ref).where(ResultModel.pilot_ref == target_id),
        ).scalars(),
    )
    for row in source_rows:
        if row.day_spec_ref in target_days:
            session.delete(row)
        else:
            row.pilot_ref = target_id


def _merge_season_rows(session: Session, *, source_id: int, target_id: int) -> None:
    source_rows = list(
        session.execute(select(SeasonLeaderboardModel).where(SeasonLeaderboardModel.pilot_ref == source_id)).scalars(),
    )
    target_days = set(
        session.execute(
            select(SeasonLeaderboardModel.day_spec_ref).where(SeasonLeaderboardModel.pilot_ref == target_id),
        ).scalars(),
    )
    for row in source_rows:
        if row.day_spec_ref in target_days:
            session.delete(row)
        else:
            row.pilot_ref = target_id


def _merge_global_rows(session: Session, *, source_id: int, target_id: int) -> None:
    source_rows = list(
        session.execute(
            select(GlobalLeaderboardRowModel).where(GlobalLeaderboardRowModel.pilot_ref == source_id),
        ).scalars(),
    )
    target_snapshots = set(
        session.execute(
            select(GlobalLeaderboardRowModel.snapshot_ref).where(GlobalLeaderboardRowModel.pilot_ref == target_id),
        ).scalars(),
    )
    for row in source_rows:
        if row.snapshot_ref in target_snapshots:
            session.delete(row)
        else:
            row.pilot_ref = target_id
