from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fpvbattle_core.db.base import Base


class DaySpecModel(Base):
    __tablename__ = "day_spec"
    __table_args__ = (UniqueConstraint("date", "race_class", name="uq_day_spec_date_class"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    race_class: Mapped[str] = mapped_column("race_class", String(16), nullable=False)
    track: Mapped[str] = mapped_column(String(255), nullable=False)
    quad_of_the_day: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    season: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    results: Mapped[list["ResultModel"]] = relationship(back_populates="day_spec", cascade="all, delete-orphan")
    season_leaderboard: Mapped[list["SeasonLeaderboardModel"]] = relationship(
        back_populates="day_spec",
        cascade="all, delete-orphan",
    )


class PilotModel(Base):
    __tablename__ = "pilots"
    __table_args__ = (UniqueConstraint("pilot", name="uq_pilots_pilot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pilot: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    results: Mapped[list["ResultModel"]] = relationship(back_populates="pilot")
    season_rows: Mapped[list["SeasonLeaderboardModel"]] = relationship(back_populates="pilot")


class ResultModel(Base):
    __tablename__ = "results"
    __table_args__ = (UniqueConstraint("day_spec_ref", "pilot_ref", name="uq_results_day_pilot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_spec_ref: Mapped[int] = mapped_column(ForeignKey("day_spec.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    pilot_ref: Mapped[int] = mapped_column(ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False, index=True)
    quad: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    place: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    day_spec: Mapped["DaySpecModel"] = relationship(back_populates="results")
    pilot: Mapped["PilotModel"] = relationship(back_populates="results")


class SeasonLeaderboardModel(Base):
    __tablename__ = "season_leaderboard"
    __table_args__ = (UniqueConstraint("day_spec_ref", "pilot_ref", name="uq_season_day_pilot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_spec_ref: Mapped[int] = mapped_column(ForeignKey("day_spec.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    pilot_ref: Mapped[int] = mapped_column(ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False, index=True)
    points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    place: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    day_spec: Mapped["DaySpecModel"] = relationship(back_populates="season_leaderboard")
    pilot: Mapped["PilotModel"] = relationship(back_populates="season_rows")

