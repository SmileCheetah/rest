"""오늘의 mock 업무를 다시 시작할 수 있는 상태로 되돌립니다."""

import asyncio

from app.database import AsyncSessionLocal, engine
from app.services.work_sessions import build_work_session_response, reset_demo_work_session
from app.time_utils import seoul_today


async def main() -> None:
    try:
        async with AsyncSessionLocal() as session, session.begin():
            work_session = await reset_demo_work_session(session, seoul_today())
            if work_session is None:
                print("오늘 업무 세션이 없습니다.")
                return
            response = await build_work_session_response(session, work_session)
            print(f"demo reset: {response.completed_visit_count}/{response.total_visit_count} visits completed")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
