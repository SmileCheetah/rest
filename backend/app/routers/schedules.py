from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import Schedule
from app.schemas.schedule import ScheduleResponse
from app.services.schedules import get_schedules_by_work_date
from app.time_utils import seoul_today

router = APIRouter(prefix="/schedules", tags=["schedules"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get(
    "/today",
    response_model=list[ScheduleResponse],
    summary="오늘 방문 일정 조회",
)
async def get_today_schedules(session: DbSession) -> list[Schedule]:
    """한국 시간 기준 오늘의 방문 일정을 방문 순서대로 반환합니다."""
    return await get_schedules_by_work_date(session, seoul_today())

