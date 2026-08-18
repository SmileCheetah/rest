from fastapi import APIRouter

from app.schemas.rest_decision import RestDecisionRequest, RestDecisionResponse
from app.services.rest_decision import RestDecisionService
from app.services.rest_need import calculate_rest_need

router = APIRouter(prefix="/rest", tags=["rest-decision"])


@router.post("/decision", response_model=RestDecisionResponse)
async def evaluate_rest_decision(
    request: RestDecisionRequest,
) -> RestDecisionResponse:
    score = calculate_rest_need(request)
    decision, source = await RestDecisionService().decide(request, score)
    return RestDecisionResponse(
        restNeedScore=score.score,
        restNeedLevel=score.level,
        details=score.details,
        decision=decision,
        decisionSource=source,
    )
