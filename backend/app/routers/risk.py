from fastapi import APIRouter

from app.schemas.risk_analysis import RiskEvaluateRequest, RiskEvaluateResponse
from app.services.risk_analysis import evaluate_risk

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/evaluate", response_model=RiskEvaluateResponse)
def evaluate_heat_risk(request: RiskEvaluateRequest) -> RiskEvaluateResponse:
    return evaluate_risk(request)
