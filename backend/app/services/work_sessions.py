from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog, Schedule, WorkSession
from app.models.base import utc_now
from app.models.enums import ActivityType, ScheduleStatus, WorkSessionStatus
from app.schemas.work_session import WorkSessionResponse


async def find_work_session_by_date(
    session: AsyncSession,
    work_date: date,
    *,
    for_update: bool = False,
) -> WorkSession | None:
    query = (
        select(WorkSession)
        .where(WorkSession.work_date == work_date)
        .order_by(WorkSession.id.desc())
        .limit(1)
    )
    if for_update:
        query = query.with_for_update()
    return (await session.execute(query)).scalar_one_or_none()


async def start_work_session(
    session: AsyncSession,
    work_date: date,
) -> tuple[WorkSession, bool]:
    """업무 세션을 시작하고 새로 시작했는지 함께 반환합니다."""
    work_session = await find_work_session_by_date(
        session,
        work_date,
        for_update=True,
    )
    if work_session is not None and work_session.status == WorkSessionStatus.COMPLETED:
        raise ValueError("work session already completed")

    started = False
    if work_session is None:
        work_session = WorkSession(
            work_date=work_date,
            status=WorkSessionStatus.IN_PROGRESS,
            started_at=utc_now(),
        )
        session.add(work_session)
        await session.flush()
        started = True
    elif work_session.status == WorkSessionStatus.READY:
        work_session.status = WorkSessionStatus.IN_PROGRESS
        work_session.started_at = work_session.started_at or utc_now()
        started = True

    if started:
        session.add(
            ActivityLog(
                work_session_id=work_session.id,
                activity_type=ActivityType.WORK_STARTED,
                occurred_at=work_session.started_at,
            )
        )

    return work_session, started


async def complete_work_session(
    session: AsyncSession,
    work_session_id: int,
) -> tuple[WorkSession | None, str | None]:
    """업무 세션을 완료하고 처리할 수 없으면 사유를 반환합니다."""
    work_session = (
        await session.execute(
            select(WorkSession)
            .where(WorkSession.id == work_session_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if work_session is None:
        return None, "not_found"
    if work_session.status == WorkSessionStatus.READY:
        return work_session, "not_started"
    if work_session.status == WorkSessionStatus.COMPLETED:
        return work_session, None

    completed_count, total_count = await get_visit_counts(
        session,
        work_session.id,
    )
    if completed_count < total_count:
        return work_session, "incomplete_schedules"

    work_session.status = WorkSessionStatus.COMPLETED
    work_session.completed_at = utc_now()
    session.add(
        ActivityLog(
            work_session_id=work_session.id,
            activity_type=ActivityType.WORK_COMPLETED,
            occurred_at=work_session.completed_at,
        )
    )
    return work_session, None


async def get_visit_counts(
    session: AsyncSession,
    work_session_id: int,
) -> tuple[int, int]:
    completed_count, total_count = (
        await session.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (Schedule.status == ScheduleStatus.COMPLETED, 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.count(Schedule.id),
            ).where(Schedule.work_session_id == work_session_id)
        )
    ).one()
    return int(completed_count), int(total_count)


async def build_work_session_response(
    session: AsyncSession,
    work_session: WorkSession,
) -> WorkSessionResponse:
    completed_count, total_count = await get_visit_counts(
        session,
        work_session.id,
    )
    return WorkSessionResponse(
        work_session_id=work_session.id,
        work_date=work_session.work_date,
        status=work_session.status,
        started_at=work_session.started_at,
        completed_at=work_session.completed_at,
        completed_visit_count=completed_count,
        total_visit_count=total_count,
        total_exposure_minutes=work_session.total_exposure_minutes,
        max_continuous_exposure_minutes=(
            work_session.max_continuous_exposure_minutes
        ),
        total_rest_minutes=work_session.total_rest_minutes,
        rest_count=work_session.rest_count,
    )

