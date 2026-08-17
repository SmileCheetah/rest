from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """모든 SQLAlchemy 모델이 상속할 기본 클래스입니다."""


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """요청 단위 비동기 DB 세션을 제공합니다."""
    async with AsyncSessionLocal() as session:
        yield session
