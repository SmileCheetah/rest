from app.schemas.risk_analysis import RiskEvaluateRequest, RiskEvaluateResponse


def evaluate_risk(request: RiskEvaluateRequest) -> RiskEvaluateResponse:
    score = 10.0
    if request.apparent_temperature >= 38:
        score += 60
    elif request.apparent_temperature >= 35:
        score += 50
    elif request.apparent_temperature >= 33:
        score += 40
    elif request.apparent_temperature >= 31:
        score += 25
    if request.current_continuous_exposure_minutes >= 120:
        score += 30
    elif request.current_continuous_exposure_minutes >= 90:
        score += 20
    elif request.current_continuous_exposure_minutes >= 60:
        score += 10
    if request.expected_continuous_exposure_minutes >= 120:
        score += 20
    elif request.expected_continuous_exposure_minutes >= 90:
        score += 10
    if request.walking_minutes >= 30:
        score += 5
    if request.shelter_accessibility is not None and request.shelter_accessibility < 0.3:
        score += 5
    score = round(min(score, 100), 2)
    rest_required = (
        request.current_continuous_exposure_minutes >= 120
        or request.expected_continuous_exposure_minutes >= 120
        or request.apparent_temperature >= 38
        or score >= 66
    )
    level = "REST_REQUIRED" if rest_required else "CAUTION" if score >= 33 else "SAFE"
    reasons: list[str] = []
    if request.apparent_temperature >= 35:
        reasons.append("HIGH_APPARENT_TEMPERATURE")
    if request.current_continuous_exposure_minutes >= 120:
        reasons.append("CONTINUOUS_EXPOSURE_LIMIT_REACHED")
    elif request.expected_continuous_exposure_minutes >= 120:
        reasons.append("EXPECTED_EXPOSURE_LIMIT_REACHED")
    if request.walking_minutes >= 30:
        reasons.append("LONG_WALKING_TIME")
    if request.shelter_accessibility is not None and request.shelter_accessibility < 0.3:
        reasons.append("LOW_SHELTER_ACCESSIBILITY")
    if not reasons:
        reasons.append("NO_MAJOR_RISK_FACTOR")
    return RiskEvaluateResponse(
        route_option_id=request.route_option_id,
        risk_score=score,
        risk_level=level,
        rest_required=rest_required,
        recommended_rest_count=1 if rest_required else 0,
        reason_codes=reasons,
        model_version="rule-based-mvp-1",
    )
