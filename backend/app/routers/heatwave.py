from fastapi import APIRouter, HTTPException, status

from app.schemas.heatwave import HeatwaveCurrentResponse
from app.services.heatwave import (
    HeatwaveConfigurationError,
    HeatwaveProviderError,
    get_current_heatwave_impact,
)

router = APIRouter(prefix="/heatwave", tags=["heatwave"])


@router.get(
    "/current",
    response_model=HeatwaveCurrentResponse,
    summary="서울 폭염 영향예보 조회",
)
async def current_heatwave() -> HeatwaveCurrentResponse:
    try:
        return await get_current_heatwave_impact()
    except HeatwaveConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except HeatwaveProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
