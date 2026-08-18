from datetime import date, time

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ActivityLog, RouteSegment, Schedule, VisitTarget, WorkSession
from app.models.base import utc_now
from app.models.enums import ActivityType, ScheduleStatus, WorkSessionStatus


class ScheduleNotFoundError(Exception):
    """일정을 찾을 수 없습니다."""


class VisitTargetNotFoundError(Exception):
    """방문대상자를 찾을 수 없습니다."""


class WorkSessionNotFoundError(Exception):
    """업무 세션을 찾을 수 없습니다."""


class ScheduleConflictError(Exception):
    """현재 상태 또는 방문 순서 때문에 요청을 처리할 수 없습니다."""


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


async def create_schedule(
    session: AsyncSession,
    *,
    visit_target_id: int,
    schedule_date: date,
    scheduled_time: time,
    visit_order: int,
    planned_visit_minutes: int | None,
) -> Schedule:
    work_session = await _get_or_create_work_session(session, schedule_date)
    visit_target = await session.get(VisitTarget, visit_target_id)
    if visit_target is None:
        raise VisitTargetNotFoundError("visit target not found")

    await _ensure_visit_order_available(
        session,
        work_session.id,
        visit_order,
    )
    schedule = Schedule(
        work_session=work_session,
        visit_target=visit_target,
        scheduled_time=scheduled_time,
        visit_order=visit_order,
        planned_visit_minutes=planned_visit_minutes,
    )
    session.add(schedule)
    await session.flush()
    return schedule


async def update_schedule(
    session: AsyncSession,
    schedule_id: int,
    updates: dict[str, object],
) -> Schedule:
    schedule = await _get_schedule(session, schedule_id, for_update=True)
    if schedule is None:
        raise ScheduleNotFoundError("schedule not found")
    await _ensure_schedule_editable(session, schedule)

    new_visit_order = updates.get("visit_order")
    if isinstance(new_visit_order, int) and new_visit_order != schedule.visit_order:
        await _ensure_visit_order_available(
            session,
            schedule.work_session_id,
            new_visit_order,
            exclude_schedule_id=schedule.id,
        )

    for field_name, value in updates.items():
        setattr(schedule, field_name, value)
    await session.flush()
    return schedule


async def delete_schedule(
    session: AsyncSession,
    schedule_id: int,
) -> None:
    schedule = await _get_schedule(session, schedule_id, for_update=True)
    if schedule is None:
        raise ScheduleNotFoundError("schedule not found")
    await _ensure_schedule_editable(session, schedule)

    route_count = await session.scalar(
        select(func.count(RouteSegment.id)).where(
            RouteSegment.schedule_id == schedule.id
        )
    )
    if route_count:
        raise ScheduleConflictError("schedule with route data cannot be deleted")

    work_session_id = schedule.work_session_id
    deleted_order = schedule.visit_order
    await session.delete(schedule)
    await session.flush()
    await session.execute(
        update(Schedule)
        .where(
            Schedule.work_session_id == work_session_id,
            Schedule.visit_order > deleted_order,
        )
        .values(visit_order=Schedule.visit_order - 1)
    )


async def get_next_schedule(
    session: AsyncSession,
    work_date: date,
) -> tuple[WorkSession, Schedule | None]:
    work_session = (
        await session.execute(
            select(WorkSession)
            .where(WorkSession.work_date == work_date)
            .order_by(WorkSession.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if work_session is None:
        raise WorkSessionNotFoundError("current work session not found")

    schedule = (
        await session.execute(
            select(Schedule)
            .options(selectinload(Schedule.visit_target))
            .where(
                Schedule.work_session_id == work_session.id,
                Schedule.status == ScheduleStatus.PENDING,
            )
            .order_by(Schedule.visit_order)
            .limit(1)
        )
    ).scalar_one_or_none()
    return work_session, schedule


async def complete_schedule(
    session: AsyncSession,
    schedule_id: int,
) -> Schedule:
    schedule = await _get_schedule(session, schedule_id, for_update=True)
    if schedule is None:
        raise ScheduleNotFoundError("schedule not found")
    if schedule.status == ScheduleStatus.COMPLETED:
        return schedule

    work_session = await session.get(WorkSession, schedule.work_session_id)
    if work_session is None:
        raise WorkSessionNotFoundError("work session not found")
    if work_session.status != WorkSessionStatus.IN_PROGRESS:
        raise ScheduleConflictError("work session is not in progress")

    schedule.status = ScheduleStatus.COMPLETED
    schedule.completed_at = utc_now()
    session.add(
        ActivityLog(
            work_session_id=schedule.work_session_id,
            schedule_id=schedule.id,
            activity_type=ActivityType.VISIT_COMPLETED,
            occurred_at=schedule.completed_at,
        )
    )
    await session.flush()
    return schedule


async def start_schedule(
    session: AsyncSession,
    schedule_id: int,
) -> Schedule:
    schedule = await _get_schedule(session, schedule_id, for_update=True)
    if schedule is None:
        raise ScheduleNotFoundError("schedule not found")
    if schedule.status == ScheduleStatus.COMPLETED:
        raise ScheduleConflictError("completed schedule cannot be started")
    if schedule.status == ScheduleStatus.IN_PROGRESS:
        return schedule
    work_session = await session.get(WorkSession, schedule.work_session_id)
    if work_session is None:
        raise WorkSessionNotFoundError("work session not found")
    if work_session.status != WorkSessionStatus.IN_PROGRESS:
        raise ScheduleConflictError("work session is not in progress")
    schedule.status = ScheduleStatus.IN_PROGRESS
    await session.flush()
    return schedule


async def _get_or_create_work_session(
    session: AsyncSession,
    work_date: date,
) -> WorkSession:
    work_session = (
        await session.execute(
            select(WorkSession)
            .where(WorkSession.work_date == work_date)
            .order_by(WorkSession.id.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if work_session is not None:
        if work_session.status == WorkSessionStatus.COMPLETED:
            raise ScheduleConflictError("completed work session cannot be changed")
        return work_session

    work_session = WorkSession(
        work_date=work_date,
        status=WorkSessionStatus.READY,
    )
    session.add(work_session)
    await session.flush()
    return work_session


async def _get_schedule(
    session: AsyncSession,
    schedule_id: int,
    *,
    for_update: bool = False,
) -> Schedule | None:
    query = (
        select(Schedule)
        .options(selectinload(Schedule.visit_target))
        .where(Schedule.id == schedule_id)
    )
    if for_update:
        query = query.with_for_update()
    return (await session.execute(query)).scalar_one_or_none()


async def _ensure_visit_order_available(
    session: AsyncSession,
    work_session_id: int,
    visit_order: int,
    *,
    exclude_schedule_id: int | None = None,
) -> None:
    query = select(Schedule.id).where(
        Schedule.work_session_id == work_session_id,
        Schedule.visit_order == visit_order,
    )
    if exclude_schedule_id is not None:
        query = query.where(Schedule.id != exclude_schedule_id)
    if (await session.execute(query.limit(1))).scalar_one_or_none() is not None:
        raise ScheduleConflictError("visit order already exists")


async def _ensure_schedule_editable(
    session: AsyncSession,
    schedule: Schedule,
) -> None:
    if schedule.status == ScheduleStatus.COMPLETED:
        raise ScheduleConflictError("completed schedule cannot be changed")
    work_session = await session.get(WorkSession, schedule.work_session_id)
    if work_session is None:
        raise WorkSessionNotFoundError("work session not found")
    if work_session.status == WorkSessionStatus.COMPLETED:
        raise ScheduleConflictError("completed work session cannot be changed")
