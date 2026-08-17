from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import VisitTarget
from app.schemas.visit_target import VisitTargetResponse

router = APIRouter(prefix="/visit-targets", tags=["visit-targets"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get(
    "",
    response_model=list[VisitTargetResponse],
    summary="방문대상자 전체 조회",
)
async def get_visit_targets(session: DbSession) -> list[VisitTarget]:
    """MVP에서 일정에 등록할 수 있는 방문대상자 목록을 반환합니다."""
    result = await session.execute(select(VisitTarget).order_by(VisitTarget.id))
    return list(result.scalars().all())


@router.get(
    "/{visit_target_id}",
    response_model=VisitTargetResponse,
    summary="방문대상자 상세 조회",
    responses={status.HTTP_404_NOT_FOUND: {"description": "방문대상자 없음"}},
)
async def get_visit_target(
    visit_target_id: int,
    session: DbSession,
) -> VisitTarget:
    """ID와 일치하는 방문대상자 한 명을 반환합니다."""
    visit_target = await session.get(VisitTarget, visit_target_id)
    if visit_target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="visit target not found",
        )
    return visit_target

