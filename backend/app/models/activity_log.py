from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now
from app.models.enums import ActivityType

if TYPE_CHECKING:
    from app.models.cooling_spot import CoolingSpot
    from app.models.route_option import RouteOption
    from app.models.route_segment import RouteSegment
    from app.models.schedule import Schedule
    from app.models.work_session import WorkSession


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (
        CheckConstraint(
            "exposure_minutes IS NULL OR exposure_minutes >= 0",
            name="exposure_minutes_nonnegative",
        ),
        CheckConstraint(
            "rest_minutes IS NULL OR rest_minutes >= 0",
            name="rest_minutes_nonnegative",
        ),
        CheckConstraint(
            "activity_type IN ('WORK_STARTED', 'NORMAL_ROUTE_SELECTED', "
            "'SAFE_ROUTE_SELECTED', 'REST_COMPLETED', 'REST_SKIPPED', "
            "'VISIT_COMPLETED', 'WORK_COMPLETED')",
            name="activity_type",
        ),
        CheckConstraint(
            "(activity_type = 'REST_COMPLETED' AND rest_complied = 1) "
            "OR (activity_type = 'REST_SKIPPED' AND rest_complied = 0) "
            "OR (activity_type NOT IN ('REST_COMPLETED', 'REST_SKIPPED') "
            "AND rest_complied IS NULL)",
            name="rest_compliance_matches_activity",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("work_sessions.id"),
        nullable=False,
        index=True,
    )
    schedule_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("schedules.id"),
        nullable=True,
        index=True,
    )
    route_segment_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("route_segments.id"),
        nullable=True,
        index=True,
    )
    route_option_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("route_options.id"),
        nullable=True,
        index=True,
    )
    cooling_spot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cooling_spots.id"),
        nullable=True,
        index=True,
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(
            ActivityType,
            name="activity_type",
            native_enum=False,
            create_constraint=False,
            length=30,
        ),
        nullable=False,
    )
    exposure_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_complied: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    work_session: Mapped[WorkSession] = relationship(back_populates="activity_logs")
    schedule: Mapped[Schedule | None] = relationship(back_populates="activity_logs")
    route_segment: Mapped[RouteSegment | None] = relationship(
        back_populates="activity_logs"
    )
    route_option: Mapped[RouteOption | None] = relationship(
        back_populates="activity_logs"
    )
    cooling_spot: Mapped[CoolingSpot | None] = relationship(
        back_populates="activity_logs"
    )
