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
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now
from app.models.enums import RiskLevel

if TYPE_CHECKING:
    from app.models.route_option import RouteOption


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("humidity BETWEEN 0 AND 100", name="humidity_range"),
        CheckConstraint("walking_minutes >= 0", name="walking_minutes_nonnegative"),
        CheckConstraint(
            "current_continuous_exposure_minutes >= 0",
            name="current_exposure_nonnegative",
        ),
        CheckConstraint(
            "expected_continuous_exposure_minutes >= 0",
            name="expected_exposure_nonnegative",
        ),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        CheckConstraint(
            "risk_level IN ('SAFE', 'CAUTION', 'REST_REQUIRED')",
            name="risk_level",
        ),
        CheckConstraint(
            "recommended_rest_count BETWEEN 0 AND 1",
            name="recommended_rest_count_range",
        ),
        CheckConstraint("rest_required IN (0, 1)", name="rest_required_boolean"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    route_option_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("route_options.id"),
        nullable=False,
        index=True,
    )
    temperature: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    humidity: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    apparent_temperature: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    wbgt_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    walking_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    current_continuous_exposure_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    expected_continuous_exposure_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    shelter_accessibility: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            name="risk_level",
            native_enum=False,
            create_constraint=False,
            length=20,
        ),
        nullable=False,
    )
    rest_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recommended_rest_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    reason_codes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    route_option: Mapped[RouteOption] = relationship(
        back_populates="risk_assessments"
    )
