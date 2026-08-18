from datetime import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import CoolingSpot
from app.models.enums import CoolingSpotType


SEOUL_BOUNDS = (37.54, 37.70, 126.80, 127.20)


def _time(value: object) -> time | None:
    text = str(value or "").strip()
    if len(text) != 4 or not text.isdigit():
        return None
    return time(int(text[:2]), int(text[2:]))


async def sync_public_shelters(session: AsyncSession, *, limit: int = 1000) -> int:
    if not settings.public_shelter_api_key:
        raise RuntimeError("PUBLIC_SHELTER_API_KEY is not configured")
    params = {
        "serviceKey": settings.public_shelter_api_key,
        "returnType": "json",
        "pageNo": 1,
        "numOfRows": min(limit, 1000),
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(settings.public_shelter_api_url, params=params)
        response.raise_for_status()
    payload = response.json()
    if payload.get("header", {}).get("resultCode") != "00":
        raise RuntimeError(payload.get("header", {}).get("resultMsg", "public shelter API failed"))
    items = payload.get("body", [])
    names = [str(item.get("RSTR_NM", "")).strip() for item in items if item.get("RSTR_NM")]
    existing = {
        spot.name: spot
        for spot in (await session.execute(select(CoolingSpot).where(CoolingSpot.name.in_(names)))).scalars().all()
    }
    synced = 0
    for item in items:
        name = str(item.get("RSTR_NM", "")).strip()
        latitude, longitude = item.get("LA"), item.get("LO")
        if not name or latitude is None or longitude is None:
            continue
        latitude, longitude = float(latitude), float(longitude)
        if not (SEOUL_BOUNDS[0] <= latitude <= SEOUL_BOUNDS[1] and SEOUL_BOUNDS[2] <= longitude <= SEOUL_BOUNDS[3]):
            continue
        values = {
            "name": name,
            "type": CoolingSpotType.PUBLIC,
            "address": str(item.get("RN_DTL_ADRES") or item.get("DTL_ADRES") or "주소 미상"),
            "latitude": latitude,
            "longitude": longitude,
            "open_time": _time(item.get("WKDAY_OPER_BEGIN_TIME")),
            "close_time": _time(item.get("WKDAY_OPER_END_TIME")),
            "operating_days": ["MON", "TUE", "WED", "THU", "FRI"],
            "facilities": {
                "air_conditioning": item.get("COLR_HOLD_ELEFN") not in (None, 0, "0"),
                "fan": item.get("COLR_HOLD_ARCNDTN") not in (None, 0, "0"),
                "capacity": item.get("USE_PSBL_NMPR"),
            },
            "source": "SAFETYDATA",
        }
        spot = existing.get(name)
        if spot is None:
            session.add(CoolingSpot(**values))
        else:
            for field, value in values.items():
                setattr(spot, field, value)
        synced += 1
    await session.flush()
    return synced
