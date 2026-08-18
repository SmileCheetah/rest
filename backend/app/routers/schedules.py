from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import Schedule
from app.schemas.schedule import (
    NextScheduleResponse,
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from app.services.schedules import (
    ScheduleConflictError,
    ScheduleNotFoundError,
    VisitTargetNotFoundError,
    WorkSessionNotFoundError,
    complete_schedule,
    create_schedule,
    delete_schedule,
    get_next_schedule,
    get_schedules_by_work_date,
    update_schedule,
    start_schedule,
)
from app.time_utils import seoul_today

router = APIRouter(prefix="/schedules", tags=["schedules"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.patch(
    "/{schedule_id}/start",
    response_model=ScheduleResponse,
    summary="방문 이동 시작",
)
async def mark_schedule_started(schedule_id: int, session: DbSession) -> Schedule:
    try:
        async with session.begin():
            schedule = await start_schedule(session, schedule_id)
    except ScheduleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ScheduleConflictError, WorkSessionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return schedule


@router.get(
    "/today",
    response_model=list[ScheduleResponse],
    summary="오늘 방문 일정 조회",
)
async def get_today_schedules(session: DbSession) -> list[Schedule]:
    """한국 시간 기준 오늘의 방문 일정을 방문 순서대로 반환합니다."""
    return await get_schedules_by_work_date(session, seoul_today())


@router.get(
    "/next",
    response_model=NextScheduleResponse,
    summary="다음 방문지 조회",
    responses={status.HTTP_404_NOT_FOUND: {"description": "오늘 업무 없음"}},
)
async def get_next_visit(session: DbSession) -> NextScheduleResponse:
    try:
        work_session, schedule = await get_next_schedule(session, seoul_today())
    except WorkSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return NextScheduleResponse(
        work_session_id=work_session.id,
        work_completed=schedule is None,
        next_schedule=schedule,
    )


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="방문 일정 생성",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "방문대상자 없음"},
        status.HTTP_409_CONFLICT: {"description": "일정 생성 충돌"},
    },
)
async def add_schedule(
    request: ScheduleCreateRequest,
    session: DbSession,
) -> Schedule:
    try:
        async with session.begin():
            schedule = await create_schedule(
                session,
                visit_target_id=request.visitTargetId,
                schedule_date=request.scheduleDate,
                scheduled_time=request.scheduledTime,
                visit_order=request.visitOrder,
                planned_visit_minutes=request.plannedVisitMinutes,
            )
    except VisitTargetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ScheduleConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return schedule


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="방문 일정 수정",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "일정 없음"},
        status.HTTP_409_CONFLICT: {"description": "일정 수정 충돌"},
    },
)
async def edit_schedule(
    schedule_id: int,
    request: ScheduleUpdateRequest,
    session: DbSession,
) -> Schedule:
    field_mapping = {
        "scheduledTime": "scheduled_time",
        "visitOrder": "visit_order",
        "plannedVisitMinutes": "planned_visit_minutes",
    }
    updates = {
        field_mapping[field_name]: value
        for field_name, value in request.model_dump(exclude_unset=True).items()
    }
    try:
        async with session.begin():
            schedule = await update_schedule(session, schedule_id, updates)
    except ScheduleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ScheduleConflictError, WorkSessionNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return schedule


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="방문 일정 삭제",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "일정 없음"},
        status.HTTP_409_CONFLICT: {"description": "일정 삭제 충돌"},
    },
)
async def remove_schedule(
    schedule_id: int,
    session: DbSession,
) -> Response:
    try:
        async with session.begin():
            await delete_schedule(session, schedule_id)
    except ScheduleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ScheduleConflictError, WorkSessionNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{schedule_id}/complete",
    response_model=ScheduleResponse,
    summary="방문 완료",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "일정 없음"},
        status.HTTP_409_CONFLICT: {"description": "방문 완료 불가"},
    },
)
async def mark_schedule_complete(
    schedule_id: int,
    session: DbSession,
) -> Schedule:
    try:
        async with session.begin():
            schedule = await complete_schedule(session, schedule_id)
    except ScheduleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ScheduleConflictError, WorkSessionNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return schedule
