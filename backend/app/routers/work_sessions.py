from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.work_session import WorkSessionResponse, WorkSessionStartRequest
from app.services.work_sessions import (
    build_work_session_response,
    complete_work_session,
    find_work_session_by_date,
    start_work_session,
)
from app.time_utils import seoul_today

router = APIRouter(prefix="/work-sessions", tags=["work-sessions"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/start",
    response_model=WorkSessionResponse,
    summary="업무 시작",
    responses={status.HTTP_409_CONFLICT: {"description": "완료된 업무"}},
)
async def start_today_work(
    request: WorkSessionStartRequest,
    session: DbSession,
) -> WorkSessionResponse:
    try:
        async with session.begin():
            work_session, _ = await start_work_session(session, request.workDate)
            response = await build_work_session_response(session, work_session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return response


@router.get(
    "/current",
    response_model=WorkSessionResponse,
    summary="현재 업무 상태 조회",
    responses={status.HTTP_404_NOT_FOUND: {"description": "오늘 업무 없음"}},
)
async def get_current_work(session: DbSession) -> WorkSessionResponse:
    work_session = await find_work_session_by_date(session, seoul_today())
    if work_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="current work session not found",
        )
    return await build_work_session_response(session, work_session)


@router.patch(
    "/{work_session_id}/complete",
    response_model=WorkSessionResponse,
    summary="업무 완료",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "업무 세션 없음"},
        status.HTTP_409_CONFLICT: {"description": "완료할 수 없는 상태"},
    },
)
async def complete_current_work(
    work_session_id: int,
    session: DbSession,
) -> WorkSessionResponse:
    async with session.begin():
        work_session, error = await complete_work_session(session, work_session_id)
        if work_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="work session not found",
            )
        if error == "not_started":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="work session has not started",
            )
        if error == "incomplete_schedules":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="all schedules must be completed first",
            )
        response = await build_work_session_response(session, work_session)
    return response
