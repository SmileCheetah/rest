from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import WorkSessionStatus

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.schedule import Schedule


class WorkSession(TimestampMixin, Base):
    __tablename__ = "work_sessions"
    __table_args__ = (
        CheckConstraint(
            "total_exposure_minutes >= 0",
            name="total_exposure_minutes_nonnegative",
        ),
        CheckConstraint(
            "max_continuous_exposure_minutes >= 0",
            name="max_continuous_exposure_minutes_nonnegative",
        ),
        CheckConstraint(
            "total_rest_minutes >= 0",
            name="total_rest_minutes_nonnegative",
        ),
        CheckConstraint("rest_count >= 0", name="rest_count_nonnegative"),
        CheckConstraint(
            "status IN ('READY', 'IN_PROGRESS', 'COMPLETED')",
            name="work_session_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[WorkSessionStatus] = mapped_column(
        Enum(
            WorkSessionStatus,
            name="work_session_status",
            native_enum=False,
            create_constraint=False,
            length=20,
        ),
        default=WorkSessionStatus.READY,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_exposure_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_continuous_exposure_minutes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_rest_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rest_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    schedules: Mapped[list[Schedule]] = relationship(back_populates="work_session")
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        back_populates="work_session"
    )
