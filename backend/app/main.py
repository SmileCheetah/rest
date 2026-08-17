from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import engine
from app.routers.schedules import router as schedules_router
from app.routers.visit_targets import router as visit_targets_router
from app.routers.work_sessions import router as work_sessions_router

app = FastAPI(
    title="폭염 이동 안전 지원 API",
    description="생활지원사의 안전한 이동을 지원하는 서비스의 백엔드 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(visit_targets_router)
app.include_router(schedules_router)
app.include_router(work_sessions_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """서버의 실행 상태를 확인합니다."""
    return {"status": "ok"}


@app.get("/health/db", tags=["system"])
async def database_health_check() -> dict[str, str]:
    """MySQL 연결 상태를 확인합니다."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc

    return {"status": "ok", "database": "connected"}
