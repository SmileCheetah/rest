from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["MOVE_POSSIBLE", "REST_RECOMMENDED", "REST_REQUIRED"]


class RiskEvaluateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    route_option_id: int = Field(..., gt=0)
    temperature: float
    humidity: float = Field(..., ge=0, le=100)
    observed_at: datetime
    wind_speed: float | None = Field(default=None, ge=0)
    walking_minutes: int = Field(..., ge=0)
    current_continuous_exposure_minutes: int = Field(..., ge=0)
    expected_continuous_exposure_minutes: int = Field(..., ge=0)
    shelter_accessibility: float | None = Field(default=None, ge=0, le=1)


class RiskEvaluateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    route_option_id: int
    apparent_temperature: float = Field(serialization_alias="apparentTemperature")
    risk_level: RiskLevel
    rest_required: bool
    recommended_rest_count: int = Field(..., ge=0, le=1)
    reason_codes: list[str]
    reason_message: str
    model_version: str
