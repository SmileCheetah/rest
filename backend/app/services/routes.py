from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import RouteOption, RouteSegment, Schedule
from app.models.enums import RouteType, ScheduleStatus, WorkSessionStatus
from app.schemas.route import (
    Coordinate,
    NormalRouteResponse,
    RoutePathPoint,
    RouteSegmentResponse,
)
from app.schemas.weather import ForecastWeatherResponse
from app.services.tmap import PedestrianRoute, get_pedestrian_route
from app.services.weather import get_forecast_weather
from app.time_utils import to_utc_naive


class RouteSegmentNotFoundError(Exception):
    """이동구간을 찾을 수 없습니다."""


class RouteSegmentConflictError(Exception):
    """현재 일정 상태에서 이동구간을 만들 수 없습니다."""


async def calculate_normal_route(
    origin: Coordinate,
    destination: Coordinate,
    departure_time: datetime,
) -> NormalRouteResponse:
    route = await get_pedestrian_route(origin, destination)
    estimated_arrival_time = departure_time + timedelta(
        minutes=route.walking_minutes
    )
    return NormalRouteResponse(
        origin=origin,
        destination=destination,
        distance_meters=route.distance_meters,
        walking_minutes=route.walking_minutes,
        estimated_arrival_time=estimated_arrival_time,
        path=route.path,
    )


async def create_route_segment(
    session: AsyncSession,
    *,
    work_session_id: int,
    schedule_id: int,
    origin: Coordinate,
    destination: Coordinate,
    departure_time: datetime,
) -> RouteSegmentResponse:
    schedule = (
        await session.execute(
            select(Schedule)
            .options(selectinload(Schedule.work_session))
            .where(Schedule.id == schedule_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if schedule is None:
        raise RouteSegmentNotFoundError("schedule not found")
    if schedule.work_session_id != work_session_id:
        raise RouteSegmentConflictError("schedule does not belong to work session")
    if schedule.work_session.status != WorkSessionStatus.IN_PROGRESS:
        raise RouteSegmentConflictError("work session is not in progress")
    if schedule.status != ScheduleStatus.PENDING:
        raise RouteSegmentConflictError("schedule is already completed")

    route, weather = await _get_route_and_weather(
        origin,
        destination,
        departure_time,
    )
    departure_utc = to_utc_naive(departure_time)
    arrival_utc = departure_utc + timedelta(minutes=route.walking_minutes)

    segment = RouteSegment(
        schedule=schedule,
        origin_latitude=Decimal(str(origin.latitude)),
        origin_longitude=Decimal(str(origin.longitude)),
        destination_latitude=Decimal(str(destination.latitude)),
        destination_longitude=Decimal(str(destination.longitude)),
        departure_time=departure_utc,
    )
    session.add(segment)
    await session.flush()

    option = RouteOption(
        route_segment_id=segment.id,
        route_type=RouteType.NORMAL,
        total_distance_meters=route.distance_meters,
        walking_minutes=route.walking_minutes,
        total_travel_minutes=route.walking_minutes,
        estimated_arrival_time=arrival_utc,
        path=[point.model_dump() for point in route.path],
        selected=False,
    )
    session.add(option)
    await session.flush()

    return _build_route_segment_response(segment, option, weather=weather)


async def get_route_segment(
    session: AsyncSession,
    route_segment_id: int,
) -> RouteSegmentResponse:
    segment = (
        await session.execute(
            select(RouteSegment)
            .options(
                selectinload(RouteSegment.schedule),
                selectinload(RouteSegment.route_options),
            )
            .where(RouteSegment.id == route_segment_id)
        )
    ).scalar_one_or_none()
    if segment is None:
        raise RouteSegmentNotFoundError("route segment not found")

    normal_option = next(
        (
            option
            for option in segment.route_options
            if option.route_type == RouteType.NORMAL
        ),
        None,
    )
    if normal_option is None:
        raise RouteSegmentNotFoundError("normal route option not found")
    return _build_route_segment_response(segment, normal_option)


async def _get_route_and_weather(
    origin: Coordinate,
    destination: Coordinate,
    departure_time: datetime,
) -> tuple[PedestrianRoute, ForecastWeatherResponse]:
    route = await get_pedestrian_route(origin, destination)
    weather = await get_forecast_weather(
        destination.latitude,
        destination.longitude,
        departure_time,
    )
    return route, weather


def _build_route_segment_response(
    segment: RouteSegment,
    option: RouteOption,
    *,
    weather: ForecastWeatherResponse | None = None,
) -> RouteSegmentResponse:
    path = [RoutePathPoint.model_validate(point) for point in option.path or []]
    return RouteSegmentResponse(
        route_segment_id=segment.id,
        route_option_id=option.id,
        work_session_id=segment.schedule.work_session_id,
        schedule_id=segment.schedule_id,
        route_type=option.route_type,
        origin=Coordinate(
            latitude=float(segment.origin_latitude),
            longitude=float(segment.origin_longitude),
        ),
        destination=Coordinate(
            latitude=float(segment.destination_latitude),
            longitude=float(segment.destination_longitude),
        ),
        departure_time=segment.departure_time,
        distance_meters=option.total_distance_meters,
        walking_minutes=option.walking_minutes,
        estimated_arrival_time=option.estimated_arrival_time,
        path=path,
        weather=weather,
    )
