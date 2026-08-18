from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.schemas.rest_decision import RestDecisionRequest, RestNeedLevel, RestScoreDetails
from app.services.weather import calculate_apparent_temperature

# MVP 정책값: 모든 기준과 가중치는 실증 데이터 확보 후 조정할 수 있다.
WALKING_WEIGHT = 0.40
ACTIVITY_WEIGHT = 0.20
HEAT_WEIGHT = 0.30
RECOVERY_WEIGHT = 0.10

MAX_CONTINUOUS_WALKING_MINUTES = 60
MAX_DAILY_WALKING_MINUTES = 180
FULL_RECOVERY_MINUTES = 20
LOW_LEVEL_MAX_SCORE = 39
MEDIUM_LEVEL_MAX_SCORE = 69


@dataclass(frozen=True)
class RestScore:
    score: int
    level: RestNeedLevel
    details: RestScoreDetails


def calculate_rest_need(request: RestDecisionRequest) -> RestScore:
    if request.temperature is None or request.humidity is None:
        raise ValueError("temperature and humidity are required after weather resolution")
    apparent_temperature = calculate_apparent_temperature(
        request.temperature,
        request.humidity,
        request.observed_at,
        request.wind_speed,
    )
    walking = _normalize(request.continuous_walking_minutes, MAX_CONTINUOUS_WALKING_MINUTES)
    activity = _normalize(request.total_walking_minutes, MAX_DAILY_WALKING_MINUTES)
    heat = _heat_score(apparent_temperature, request.heat_level)
    recovery = _normalize(request.recent_rest_minutes, FULL_RECOVERY_MINUTES)
    raw_score = (
        WALKING_WEIGHT * walking
        + ACTIVITY_WEIGHT * activity
        + HEAT_WEIGHT * heat
        - RECOVERY_WEIGHT * recovery
    )
    score = int(round(max(0.0, min(100.0, raw_score))))
    return RestScore(
        score=score,
        level=classify_rest_need(score),
        details=RestScoreDetails(
            walking_score=round(walking, 2),
            activity_score=round(activity, 2),
            heat_score=round(heat, 2),
            recovery_score=round(recovery, 2),
        ),
    )


def classify_rest_need(score: int) -> RestNeedLevel:
    if score <= LOW_LEVEL_MAX_SCORE:
        return "LOW"
    if score <= MEDIUM_LEVEL_MAX_SCORE:
        return "MEDIUM"
    return "HIGH"


def _normalize(value: int, maximum: int) -> float:
    if maximum <= 0:
        raise ValueError("normalization maximum must be positive")
    return max(0.0, min(100.0, value / maximum * 100.0))


def _heat_score(apparent_temperature: float, heat_level: str | None) -> float:
    if heat_level == "LOW":
        return 25.0
    if heat_level == "MEDIUM":
        return 60.0
    if heat_level == "HIGH":
        return 90.0
    # Apparent temperature is used only as the deterministic MVP proxy.
    return max(0.0, min(100.0, (apparent_temperature - 20.0) / 18.0 * 100.0))
