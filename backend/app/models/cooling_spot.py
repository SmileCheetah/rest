from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, CheckConstraint, Enum, JSON, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CoolingSpotType

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.route_option import RouteOption


class CoolingSpot(TimestampMixin, Base):
    __tablename__ = "cooling_spots"
    __table_args__ = (
        CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="longitude_range",
        ),
        CheckConstraint(
            "type IN ('PUBLIC', 'COMPANY')",
            name="cooling_spot_type",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[CoolingSpotType] = mapped_column(
        Enum(
            CoolingSpotType,
            name="cooling_spot_type",
            native_enum=False,
            create_constraint=False,
            length=20,
        ),
        nullable=False,
    )
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    operating_days: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    facilities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    route_options: Mapped[list[RouteOption]] = relationship(
        back_populates="cooling_spot"
    )
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        back_populates="cooling_spot"
    )
