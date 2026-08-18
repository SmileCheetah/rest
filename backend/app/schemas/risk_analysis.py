from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["SAFE", "CAUTION", "REST_REQUIRED"]


class RiskEvaluateRequest(BaseModel):
    route_option_id: int = Field(..., gt=0)
    temperature: float
    humidity: float = Field(..., ge=0, le=100)
    apparent_temperature: float
    walking_minutes: int = Field(..., ge=0)
    current_continuous_exposure_minutes: int = Field(..., ge=0)
    expected_continuous_exposure_minutes: int = Field(..., ge=0)
    shelter_accessibility: float | None = Field(default=None, ge=0)


class RiskEvaluateResponse(BaseModel):
    route_option_id: int
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    rest_required: bool
    recommended_rest_count: int = Field(..., ge=0, le=1)
    reason_codes: list[str]
    model_version: str
