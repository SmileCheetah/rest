from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ScheduleStatus

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.route_segment import RouteSegment
    from app.models.visit_target import VisitTarget
    from app.models.work_session import WorkSession


class Schedule(TimestampMixin, Base):
    __tablename__ = "schedules"
    __table_args__ = (
        UniqueConstraint(
            "work_session_id",
            "visit_order",
            name="uq_schedule_visit_order",
        ),
        CheckConstraint("visit_order > 0", name="visit_order_positive"),
        CheckConstraint(
            "planned_visit_minutes IS NULL OR planned_visit_minutes >= 0",
            name="planned_visit_minutes_nonnegative",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED')",
            name="schedule_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("work_sessions.id"),
        nullable=False,
        index=True,
    )
    visit_target_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("visit_targets.id"),
        nullable=False,
        index=True,
    )
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    visit_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(
            ScheduleStatus,
            name="schedule_status",
            native_enum=False,
            create_constraint=False,
            length=20,
        ),
        default=ScheduleStatus.PENDING,
        nullable=False,
    )
    planned_visit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    work_session: Mapped[WorkSession] = relationship(back_populates="schedules")
    visit_target: Mapped[VisitTarget] = relationship(back_populates="schedules")
    route_segments: Mapped[list[RouteSegment]] = relationship(
        back_populates="schedule"
    )
    activity_logs: Mapped[list[ActivityLog]] = relationship(back_populates="schedule")
