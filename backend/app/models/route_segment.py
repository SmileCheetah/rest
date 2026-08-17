from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.route_option import RouteOption
    from app.models.schedule import Schedule


class RouteSegment(TimestampMixin, Base):
    __tablename__ = "route_segments"
    __table_args__ = (
        CheckConstraint(
            "origin_latitude BETWEEN -90 AND 90",
            name="origin_latitude_range",
        ),
        CheckConstraint(
            "origin_longitude BETWEEN -180 AND 180",
            name="origin_longitude_range",
        ),
        CheckConstraint(
            "destination_latitude BETWEEN -90 AND 90",
            name="destination_latitude_range",
        ),
        CheckConstraint(
            "destination_longitude BETWEEN -180 AND 180",
            name="destination_longitude_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("schedules.id"),
        nullable=False,
        index=True,
    )
    origin_latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    origin_longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    destination_latitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    destination_longitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    departure_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    schedule: Mapped[Schedule] = relationship(back_populates="route_segments")
    route_options: Mapped[list[RouteOption]] = relationship(
        back_populates="route_segment"
    )
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        back_populates="route_segment"
    )
