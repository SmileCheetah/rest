from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now
from app.models.enums import RouteType

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.cooling_spot import CoolingSpot
    from app.models.risk_assessment import RiskAssessment
    from app.models.route_segment import RouteSegment


class RouteOption(Base):
    __tablename__ = "route_options"
    __table_args__ = (
        CheckConstraint("total_distance_meters >= 0", name="distance_nonnegative"),
        CheckConstraint("walking_minutes >= 0", name="walking_minutes_nonnegative"),
        CheckConstraint(
            "total_travel_minutes >= 0",
            name="total_travel_minutes_nonnegative",
        ),
        CheckConstraint(
            "detour_distance_meters IS NULL OR detour_distance_meters >= 0",
            name="detour_distance_nonnegative",
        ),
        CheckConstraint(
            "additional_minutes IS NULL OR additional_minutes >= 0",
            name="additional_minutes_nonnegative",
        ),
        CheckConstraint(
            "detour_ratio IS NULL OR detour_ratio >= 0",
            name="detour_ratio_nonnegative",
        ),
        CheckConstraint(
            "minutes_to_cooling_spot IS NULL OR minutes_to_cooling_spot >= 0",
            name="minutes_to_cooling_spot_nonnegative",
        ),
        CheckConstraint(
            "planned_rest_minutes IS NULL OR planned_rest_minutes >= 0",
            name="planned_rest_minutes_nonnegative",
        ),
        CheckConstraint(
            "minutes_from_cooling_spot IS NULL OR minutes_from_cooling_spot >= 0",
            name="minutes_from_cooling_spot_nonnegative",
        ),
        CheckConstraint("selected IN (0, 1)", name="selected_boolean"),
        CheckConstraint(
            "route_type IN ('NORMAL', 'SAFE')",
            name="route_type",
        ),
        CheckConstraint(
            "(route_type = 'NORMAL' "
            "AND cooling_spot_id IS NULL "
            "AND planned_rest_minutes IS NULL "
            "AND minutes_to_cooling_spot IS NULL "
            "AND minutes_from_cooling_spot IS NULL "
            "AND cooling_spot_arrival_time IS NULL) "
            "OR (route_type = 'SAFE' "
            "AND cooling_spot_id IS NOT NULL "
            "AND planned_rest_minutes IS NOT NULL "
            "AND minutes_to_cooling_spot IS NOT NULL "
            "AND minutes_from_cooling_spot IS NOT NULL "
            "AND cooling_spot_arrival_time IS NOT NULL)",
            name="route_type_required_fields",
        ),
        CheckConstraint(
            "route_type != 'NORMAL' OR total_travel_minutes = walking_minutes",
            name="normal_travel_time",
        ),
        CheckConstraint(
            "route_type != 'SAFE' OR walking_minutes = "
            "minutes_to_cooling_spot + minutes_from_cooling_spot",
            name="safe_walking_time",
        ),
        CheckConstraint(
            "route_type != 'SAFE' OR total_travel_minutes = "
            "walking_minutes + planned_rest_minutes",
            name="safe_travel_time",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    route_segment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("route_segments.id"),
        nullable=False,
        index=True,
    )
    cooling_spot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cooling_spots.id"),
        nullable=True,
        index=True,
    )
    route_type: Mapped[RouteType] = mapped_column(
        Enum(
            RouteType,
            name="route_type",
            native_enum=False,
            create_constraint=False,
            length=20,
        ),
        nullable=False,
    )
    total_distance_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    walking_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_travel_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_arrival_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    detour_distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    additional_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detour_ratio: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    minutes_to_cooling_spot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    planned_rest_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes_from_cooling_spot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    cooling_spot_arrival_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    path: Mapped[list[dict[str, float]] | None] = mapped_column(JSON, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    route_segment: Mapped[RouteSegment] = relationship(back_populates="route_options")
    cooling_spot: Mapped[CoolingSpot | None] = relationship(
        back_populates="route_options"
    )
    risk_assessments: Mapped[list[RiskAssessment]] = relationship(
        back_populates="route_option"
    )
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        back_populates="route_option"
    )
