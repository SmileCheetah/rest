from math import cos, radians
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import CoolingSpot
from app.schemas.cooling_spot import CoolingSpotResponse
from app.services.public_shelters import sync_public_shelters

router = APIRouter(prefix="/cooling-spots", tags=["cooling-spots"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/sync-public", summary="공공 무더위쉼터 API 동기화")
async def sync_public(session: DbSession) -> dict[str, int]:
    try:
        async with session.begin():
            count = await sync_public_shelters(session)
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"synced": count}


@router.get("", response_model=list[CoolingSpotResponse], summary="주변 쿨링스팟 조회")
async def get_cooling_spots(
    session: DbSession,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius: float = Query(default=2_000, gt=0, le=20_000, description="반경(m)"),
) -> list[CoolingSpot]:
    spots = list((await session.execute(select(CoolingSpot).order_by(CoolingSpot.id))).scalars().all())
    if latitude is None or longitude is None:
        return spots
    lat_scale = 111_000
    lon_scale = 111_000 * cos(radians(latitude))
    return [
        spot for spot in spots
        if ((float(spot.latitude) - latitude) * lat_scale) ** 2
        + ((float(spot.longitude) - longitude) * lon_scale) ** 2 <= radius ** 2
    ]
