from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Schedule, WorkSession


async def get_schedules_by_work_date(
    session: AsyncSession,
    work_date: date,
) -> list[Schedule]:
    """해당 날짜의 최신 업무 세션에 포함된 일정을 순서대로 조회합니다."""
    work_session_id = (
        await session.execute(
            select(WorkSession.id)
            .where(WorkSession.work_date == work_date)
            .order_by(WorkSession.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if work_session_id is None:
        return []

    schedules = (
        await session.execute(
            select(Schedule)
            .options(selectinload(Schedule.visit_target))
            .where(Schedule.work_session_id == work_session_id)
            .order_by(Schedule.visit_order)
        )
    ).scalars()
    return list(schedules.all())

