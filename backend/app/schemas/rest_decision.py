from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RestNeedLevel = Literal["LOW", "MEDIUM", "HIGH"]
RestTiming = Literal["NOW", "AFTER_NEXT_VISIT", "SOON", "NOT_NEEDED"]
HeatLevel = Literal["LOW", "MEDIUM", "HIGH"]
RestStatus = Literal["MOVABLE", "REST_RECOMMENDED", "REST_BEFORE_NEXT_VISIT"]


class RestDecisionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    continuous_walking_minutes: int = Field(..., ge=0, validation_alias="continuousWalkingMinutes", serialization_alias="continuousWalkingMinutes")
    total_walking_minutes: int = Field(..., ge=0, validation_alias="totalWalkingMinutes", serialization_alias="totalWalkingMinutes")
    minutes_since_last_rest: int = Field(..., ge=0, validation_alias="minutesSinceLastRest", serialization_alias="minutesSinceLastRest")
    recent_rest_minutes: int = Field(..., ge=0, le=180, validation_alias="recentRestMinutes", serialization_alias="recentRestMinutes")
    station_id: int = Field(default=108, ge=1, validation_alias="stationId", serialization_alias="stationId")
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    wbgt: float | None = Field(default=None, ge=-20, le=60)
    wind_speed: float | None = Field(default=None, ge=0, validation_alias="windSpeed", serialization_alias="windSpeed")
    observed_at: datetime = Field(..., validation_alias="observedAt", serialization_alias="observedAt")
    next_travel_minutes: int = Field(..., ge=0, validation_alias="nextTravelMinutes", serialization_alias="nextTravelMinutes")
    cooling_spot_nearby: bool = Field(default=False, validation_alias="coolingSpotNearby", serialization_alias="coolingSpotNearby")
    distance_to_cooling_spot_meters: int | None = Field(
        default=None,
        ge=0,
        validation_alias="distanceToCoolingSpotMeters",
        serialization_alias="distanceToCoolingSpotMeters",
    )
    heat_level: HeatLevel | None = Field(default=None, validation_alias="heatLevel", serialization_alias="heatLevel")


class RestScoreDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    walking_score: float = Field(validation_alias="walkingScore", serialization_alias="walkingScore")
    activity_score: float = Field(validation_alias="activityScore", serialization_alias="activityScore")
    heat_score: float = Field(validation_alias="heatScore", serialization_alias="heatScore")
    recovery_score: float = Field(validation_alias="recoveryScore", serialization_alias="recoveryScore")


class RestDecision(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    should_rest: bool = Field(validation_alias="shouldRest", serialization_alias="shouldRest")
    rest_timing: RestTiming = Field(validation_alias="restTiming", serialization_alias="restTiming")
    recommendation: str
    reason: str
    recommended_rest_minutes: int = Field(ge=0, validation_alias="recommendedRestMinutes", serialization_alias="recommendedRestMinutes")


class RestDecisionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rest_need_score: int | None = Field(default=None, validation_alias="restNeedScore", serialization_alias="restNeedScore")
    rest_need_level: RestNeedLevel | None = Field(default=None, validation_alias="restNeedLevel", serialization_alias="restNeedLevel")
    details: RestScoreDetails | None = None
    decision: RestDecision
    rest_status_prediction: dict[str, object] | None = Field(
        default=None,
        validation_alias="restStatusPrediction",
        serialization_alias="restStatusPrediction",
    )
    decision_source: Literal["AI", "MODEL", "FALLBACK"] = Field(validation_alias="decisionSource", serialization_alias="decisionSource")
    weather_source: Literal["KMA_ASOS", "REQUEST_FALLBACK"] = Field(
        validation_alias="weatherSource",
        serialization_alias="weatherSource",
    )
