"""로컬 개발용 MVP mock 데이터를 생성합니다."""

import asyncio
from datetime import date, time
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.database import AsyncSessionLocal, engine
from app.models import CoolingSpot, Schedule, VisitTarget, WorkSession
from app.models.enums import CoolingSpotType, WorkSessionStatus

VISIT_TARGETS: tuple[dict[str, Any], ...] = (
    {
        "name": "김영희",
        "address": "서울특별시 종로구 창신동 데모 주소 1",
        "latitude": Decimal("37.5747100"),
        "longitude": Decimal("127.0114200"),
    },
    {
        "name": "이정수",
        "address": "서울특별시 종로구 창신동 데모 주소 2",
        "latitude": Decimal("37.5751800"),
        "longitude": Decimal("127.0122600"),
    },
    {
        "name": "박순자",
        "address": "서울특별시 종로구 창신동 데모 주소 3",
        "latitude": Decimal("37.5739200"),
        "longitude": Decimal("127.0130500"),
    },
    {
        "name": "최동호",
        "address": "서울특별시 종로구 창신동 데모 주소 4",
        "latitude": Decimal("37.5729800"),
        "longitude": Decimal("127.0118900"),
    },
    {
        "name": "정미숙",
        "address": "서울특별시 종로구 창신동 데모 주소 5",
        "latitude": Decimal("37.5761200"),
        "longitude": Decimal("127.0107600"),
    },
    {
        "name": "강병철",
        "address": "서울특별시 종로구 창신동 데모 주소 6",
        "latitude": Decimal("37.5743600"),
        "longitude": Decimal("127.0099300"),
    },
    {
        "name": "윤정희",
        "address": "서울특별시 종로구 창신동 데모 주소 7",
        "latitude": Decimal("37.5734100"),
        "longitude": Decimal("127.0105200"),
    },
    {
        "name": "한기수",
        "address": "서울특별시 종로구 창신동 데모 주소 8",
        "latitude": Decimal("37.5756200"),
        "longitude": Decimal("127.0134800"),
    },
)

WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"]
EVERY_DAY = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

COOLING_SPOTS: tuple[dict[str, Any], ...] = (
    {
        "name": "창신동 공공 무더위쉼터",
        "type": CoolingSpotType.PUBLIC,
        "address": "서울특별시 종로구 창신동 공공쉼터 데모",
        "latitude": Decimal("37.5749500"),
        "longitude": Decimal("127.0120100"),
        "open_time": time(9, 0),
        "close_time": time(18, 0),
        "operating_days": WEEKDAYS,
        "facilities": {
            "air_conditioning": True,
            "water": True,
            "restroom": True,
        },
        "source": "MVP_MOCK",
    },
    {
        "name": "동대문역 공공 쉼터",
        "type": CoolingSpotType.PUBLIC,
        "address": "서울특별시 종로구 동대문역 인근 공공쉼터 데모",
        "latitude": Decimal("37.5718600"),
        "longitude": Decimal("127.0107800"),
        "open_time": time(9, 0),
        "close_time": time(20, 0),
        "operating_days": EVERY_DAY,
        "facilities": {
            "air_conditioning": True,
            "water": True,
            "restroom": False,
        },
        "source": "MVP_MOCK",
    },
    {
        "name": "쉼표 카페 창신점",
        "type": CoolingSpotType.COMPANY,
        "address": "서울특별시 종로구 창신길 기업 쿨링스팟 데모 1",
        "latitude": Decimal("37.5737600"),
        "longitude": Decimal("127.0126200"),
        "open_time": time(8, 0),
        "close_time": time(21, 0),
        "operating_days": EVERY_DAY,
        "facilities": {
            "air_conditioning": True,
            "water": True,
            "restroom": True,
            "charging": True,
        },
        "source": "MVP_MOCK",
    },
    {
        "name": "창신 편의점 쿨링스팟",
        "type": CoolingSpotType.COMPANY,
        "address": "서울특별시 종로구 창신길 기업 쿨링스팟 데모 2",
        "latitude": Decimal("37.5754100"),
        "longitude": Decimal("127.0113100"),
        "open_time": time(0, 0),
        "close_time": time(23, 59, 59),
        "operating_days": EVERY_DAY,
        "facilities": {
            "air_conditioning": True,
            "water": True,
            "restroom": False,
        },
        "source": "MVP_MOCK",
    },
    {
        "name": "종로 기업 휴게라운지",
        "type": CoolingSpotType.COMPANY,
        "address": "서울특별시 종로구 창신동 기업 쿨링스팟 데모 3",
        "latitude": Decimal("37.5731800"),
        "longitude": Decimal("127.0098700"),
        "open_time": time(10, 0),
        "close_time": time(19, 0),
        "operating_days": WEEKDAYS,
        "facilities": {
            "air_conditioning": True,
            "water": True,
            "restroom": True,
            "charging": True,
        },
        "source": "MVP_MOCK",
    },
)

TODAY_SCHEDULES: tuple[dict[str, Any], ...] = (
    {
        "visit_target_name": "김영희",
        "scheduled_time": time(9, 0),
        "visit_order": 1,
        "planned_visit_minutes": 40,
    },
    {
        "visit_target_name": "이정수",
        "scheduled_time": time(10, 30),
        "visit_order": 2,
        "planned_visit_minutes": 40,
    },
    {
        "visit_target_name": "박순자",
        "scheduled_time": time(13, 0),
        "visit_order": 3,
        "planned_visit_minutes": 40,
    },
    {
        "visit_target_name": "최동호",
        "scheduled_time": time(15, 0),
        "visit_order": 4,
        "planned_visit_minutes": 40,
    },
)


async def seed_visit_targets() -> tuple[int, int]:
    async with AsyncSessionLocal() as session, session.begin():
        names = [item["name"] for item in VISIT_TARGETS]
        existing_names = set(
            (await session.execute(select(VisitTarget.name).where(VisitTarget.name.in_(names))))
            .scalars()
            .all()
        )
        new_items = [
            VisitTarget(**item)
            for item in VISIT_TARGETS
            if item["name"] not in existing_names
        ]
        session.add_all(new_items)
        return len(new_items), len(VISIT_TARGETS) - len(new_items)


async def seed_cooling_spots() -> tuple[int, int]:
    async with AsyncSessionLocal() as session, session.begin():
        names = [item["name"] for item in COOLING_SPOTS]
        existing_names = set(
            (
                await session.execute(
                    select(CoolingSpot.name).where(CoolingSpot.name.in_(names))
                )
            )
            .scalars()
            .all()
        )
        new_items = [
            CoolingSpot(**item)
            for item in COOLING_SPOTS
            if item["name"] not in existing_names
        ]
        session.add_all(new_items)
        return len(new_items), len(COOLING_SPOTS) - len(new_items)


async def seed_today_schedules() -> tuple[int, int, int, int, int]:
    """오늘 업무 세션 1개와 방문 일정 4개를 중복 없이 생성합니다."""
    work_date = date.today()

    async with AsyncSessionLocal() as session, session.begin():
        work_session = (
            await session.execute(
                select(WorkSession)
                .where(WorkSession.work_date == work_date)
                .order_by(WorkSession.id)
                .limit(1)
            )
        ).scalar_one_or_none()

        work_session_inserted = 0
        if work_session is None:
            work_session = WorkSession(
                work_date=work_date,
                status=WorkSessionStatus.READY,
            )
            session.add(work_session)
            await session.flush()
            work_session_inserted = 1

        target_names = [item["visit_target_name"] for item in TODAY_SCHEDULES]
        targets = (
            await session.execute(
                select(VisitTarget).where(VisitTarget.name.in_(target_names))
            )
        ).scalars()
        target_ids_by_name = {target.name: target.id for target in targets}
        missing_target_names = set(target_names) - target_ids_by_name.keys()
        if missing_target_names:
            missing = ", ".join(sorted(missing_target_names))
            raise RuntimeError(f"visit targets must be seeded first: {missing}")

        existing_orders = set(
            (
                await session.execute(
                    select(Schedule.visit_order).where(
                        Schedule.work_session_id == work_session.id
                    )
                )
            )
            .scalars()
            .all()
        )
        new_schedules = [
            Schedule(
                work_session_id=work_session.id,
                visit_target_id=target_ids_by_name[item["visit_target_name"]],
                scheduled_time=item["scheduled_time"],
                visit_order=item["visit_order"],
                planned_visit_minutes=item["planned_visit_minutes"],
            )
            for item in TODAY_SCHEDULES
            if item["visit_order"] not in existing_orders
        ]
        session.add_all(new_schedules)

        return (
            work_session.id,
            work_session_inserted,
            1 - work_session_inserted,
            len(new_schedules),
            len(TODAY_SCHEDULES) - len(new_schedules),
        )


async def main() -> None:
    try:
        target_inserted, target_skipped = await seed_visit_targets()
        spot_inserted, spot_skipped = await seed_cooling_spots()
        (
            work_session_id,
            work_session_inserted,
            work_session_skipped,
            schedule_inserted,
            schedule_skipped,
        ) = await seed_today_schedules()
        print(
            "visit_targets: "
            f"inserted={target_inserted}, skipped={target_skipped}"
        )
        print(
            "cooling_spots: "
            f"inserted={spot_inserted}, skipped={spot_skipped}"
        )
        print(
            "work_sessions: "
            f"inserted={work_session_inserted}, skipped={work_session_skipped}, "
            f"id={work_session_id}, work_date={date.today().isoformat()}"
        )
        print(
            "schedules: "
            f"inserted={schedule_inserted}, skipped={schedule_skipped}"
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
