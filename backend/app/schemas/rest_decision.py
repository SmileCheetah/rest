from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RestNeedLevel = Literal["LOW", "MEDIUM", "HIGH"]
RestTiming = Literal["NOW", "AFTER_NEXT_VISIT", "SOON", "NOT_NEEDED"]
HeatLevel = Literal["LOW", "MEDIUM", "HIGH"]
RestStatus = Literal["MOVABLE", "REST_RECOMMENDED", "REST_BEFORE_NEXT_VISIT"]


class RestDecisionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    continuous_walking_minutes: int = Field(..., ge=0, alias="continuousWalkingMinutes")
    total_walking_minutes: int = Field(..., ge=0, alias="totalWalkingMinutes")
    minutes_since_last_rest: int = Field(..., ge=0, alias="minutesSinceLastRest")
    recent_rest_minutes: int = Field(..., ge=0, le=180, alias="recentRestMinutes")
    station_id: int = Field(default=108, ge=1, alias="stationId")
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    wbgt: float | None = Field(default=None, ge=-20, le=60)
    wind_speed: float | None = Field(default=None, ge=0, alias="windSpeed")
    observed_at: datetime = Field(..., alias="observedAt")
    next_travel_minutes: int = Field(..., ge=0, alias="nextTravelMinutes")
    cooling_spot_nearby: bool = Field(default=False, alias="coolingSpotNearby")
    distance_to_cooling_spot_meters: int | None = Field(
        default=None,
        ge=0,
        alias="distanceToCoolingSpotMeters",
    )
    heat_level: HeatLevel | None = Field(default=None, alias="heatLevel")


class RestScoreDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    walking_score: float = Field(alias="walkingScore")
    activity_score: float = Field(alias="activityScore")
    heat_score: float = Field(alias="heatScore")
    recovery_score: float = Field(alias="recoveryScore")


class RestDecision(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    should_rest: bool = Field(alias="shouldRest")
    rest_timing: RestTiming = Field(alias="restTiming")
    recommendation: str
    reason: str
    recommended_rest_minutes: int = Field(ge=0, alias="recommendedRestMinutes")


class RestDecisionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rest_need_score: int | None = Field(default=None, alias="restNeedScore")
    rest_need_level: RestNeedLevel | None = Field(default=None, alias="restNeedLevel")
    details: RestScoreDetails | None = None
    decision: RestDecision
    rest_status_prediction: dict[str, object] | None = Field(
        default=None,
        alias="restStatusPrediction",
    )
    decision_source: Literal["AI", "MODEL", "FALLBACK"] = Field(alias="decisionSource")
    weather_source: Literal["KMA_ASOS", "REQUEST_FALLBACK"] = Field(
        alias="weatherSource"
    )
