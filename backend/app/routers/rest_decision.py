from fastapi import APIRouter

from app.schemas.rest_decision import RestDecisionRequest, RestDecisionResponse
from app.services.rest_decision import RestDecisionService
from app.services.rest_need import calculate_rest_need
from app.services.rest_weather import RestWeatherUnavailableError, resolve_rest_weather

router = APIRouter(prefix="/rest", tags=["rest-decision"])


@router.post("/decision", response_model=RestDecisionResponse)
async def evaluate_rest_decision(
    request: RestDecisionRequest,
) -> RestDecisionResponse:
    try:
        weather = await resolve_rest_weather(request)
    except RestWeatherUnavailableError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    score = calculate_rest_need(weather.request)
    decision, source = await RestDecisionService().decide(weather.request, score)
    return RestDecisionResponse(
        restNeedScore=score.score,
        restNeedLevel=score.level,
        details=score.details,
        decision=decision,
        decisionSource=source,
        weatherSource=weather.source,
    )
