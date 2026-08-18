from app.schemas.risk_analysis import (
    RiskEvaluateRequest,
    RiskEvaluateResponse,
    RiskLevel,
)
from app.services.weather import calculate_apparent_temperature


def classify_risk(
    *,
    apparent_temperature: float,
    walking_minutes: int,
    current_continuous_exposure_minutes: int,
    expected_continuous_exposure_minutes: int,
    shelter_accessibility: float | None,
) -> RiskLevel:
    """Classify a route directly without producing an intermediate score."""
    if (
        apparent_temperature >= 38
        or current_continuous_exposure_minutes >= 120
        or expected_continuous_exposure_minutes >= 120
    ):
        return "REST_REQUIRED"

    if (
        apparent_temperature >= 31
        or current_continuous_exposure_minutes >= 30
        or expected_continuous_exposure_minutes >= 30
        or walking_minutes >= 30
        or (shelter_accessibility is not None and shelter_accessibility < 0.3)
    ):
        return "REST_RECOMMENDED"

    return "MOVE_POSSIBLE"


def build_reason_message(
    *,
    apparent_temperature: float,
    expected_continuous_exposure_minutes: int,
    risk_level: RiskLevel,
) -> str:
    facts: list[str] = []
    if apparent_temperature >= 31:
        facts.append(f"체감온도 {apparent_temperature:.1f}℃")
    if expected_continuous_exposure_minutes >= 30:
        facts.append(f"예상 연속 야외 노출 {expected_continuous_exposure_minutes}분")

    if risk_level == "REST_REQUIRED":
        action = "다음 방문 전 휴식이 필요합니다."
    elif risk_level == "REST_RECOMMENDED":
        action = "이동 전후 휴식을 권장합니다."
    else:
        action = "현재 기준으로 이동 가능합니다."

    if not facts:
        return action
    return f"{', '.join(facts)}입니다. {action}"


def evaluate_risk(request: RiskEvaluateRequest) -> RiskEvaluateResponse:
    apparent_temperature = calculate_apparent_temperature(
        request.temperature,
        request.humidity,
        request.observed_at,
        request.wind_speed,
    )
    level = classify_risk(
        apparent_temperature=apparent_temperature,
        walking_minutes=request.walking_minutes,
        current_continuous_exposure_minutes=(
            request.current_continuous_exposure_minutes
        ),
        expected_continuous_exposure_minutes=(
            request.expected_continuous_exposure_minutes
        ),
        shelter_accessibility=request.shelter_accessibility,
    )
    rest_required = level == "REST_REQUIRED"
    reasons: list[str] = []
    if apparent_temperature >= 31:
        reasons.append("HIGH_APPARENT_TEMPERATURE")
    if request.current_continuous_exposure_minutes >= 120:
        reasons.append("CONTINUOUS_EXPOSURE_LIMIT_REACHED")
    elif request.expected_continuous_exposure_minutes >= 120:
        reasons.append("EXPECTED_EXPOSURE_LIMIT_REACHED")
    elif (
        request.current_continuous_exposure_minutes >= 30
        or request.expected_continuous_exposure_minutes >= 30
    ):
        reasons.append("LONG_CONTINUOUS_EXPOSURE")
    if request.walking_minutes >= 30:
        reasons.append("LONG_WALKING_TIME")
    if (
        request.shelter_accessibility is not None
        and request.shelter_accessibility < 0.3
    ):
        reasons.append("LOW_SHELTER_ACCESSIBILITY")
    if not reasons:
        reasons.append("NO_MAJOR_RISK_FACTOR")
    return RiskEvaluateResponse(
        route_option_id=request.route_option_id,
        apparent_temperature=apparent_temperature,
        risk_level=level,
        rest_required=rest_required,
        recommended_rest_count=0 if level == "MOVE_POSSIBLE" else 1,
        reason_codes=reasons,
        reason_message=build_reason_message(
            apparent_temperature=apparent_temperature,
            expected_continuous_exposure_minutes=(
                request.expected_continuous_exposure_minutes
            ),
            risk_level=level,
        ),
        model_version="rule-classifier-mvp-1",
    )
