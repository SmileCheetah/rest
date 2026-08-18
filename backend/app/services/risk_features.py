from datetime import datetime

from pydantic import BaseModel, Field

from app.services.exposure import ExposureState


class RouteRiskFeatures(BaseModel):
    """Internal, model-ready features for one route segment."""

    weather_at: datetime
    temperature: float
    humidity: float = Field(..., ge=0, le=100)
    wind_speed: float | None = Field(default=None, ge=0)
    walking_minutes: int = Field(..., ge=0)
    current_continuous_exposure_minutes: int = Field(..., ge=0)
    expected_continuous_exposure_minutes: int = Field(..., ge=0)
    current_daily_exposure_minutes: int = Field(..., ge=0)
    expected_daily_exposure_minutes: int = Field(..., ge=0)
    current_daily_rest_minutes: int = Field(..., ge=0)
    expected_daily_rest_minutes: int = Field(..., ge=0)
    shelter_accessibility: float | None = Field(default=None, ge=0, le=1)


def build_route_risk_features(
    *,
    weather_at: datetime,
    temperature: float,
    humidity: float,
    wind_speed: float | None,
    walking_minutes: int,
    current_state: ExposureState,
    projected_state: ExposureState,
    shelter_accessibility: float | None = None,
) -> RouteRiskFeatures:
    """Combine weather, movement, and exposure state into one feature object."""
    return RouteRiskFeatures(
        weather_at=weather_at,
        temperature=temperature,
        humidity=humidity,
        wind_speed=wind_speed,
        walking_minutes=walking_minutes,
        current_continuous_exposure_minutes=current_state.continuous_exposure_minutes,
        expected_continuous_exposure_minutes=projected_state.continuous_exposure_minutes,
        current_daily_exposure_minutes=current_state.daily_exposure_minutes,
        expected_daily_exposure_minutes=projected_state.daily_exposure_minutes,
        current_daily_rest_minutes=current_state.daily_rest_minutes,
        expected_daily_rest_minutes=projected_state.daily_rest_minutes,
        shelter_accessibility=shelter_accessibility,
    )
