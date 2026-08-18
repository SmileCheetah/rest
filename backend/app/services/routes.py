from datetime import datetime, time, timedelta
from decimal import Decimal
from math import cos, radians

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CoolingSpot, RouteOption, RouteSegment, Schedule
from app.models.enums import RouteType, ScheduleStatus, WorkSessionStatus
from app.schemas.route import (
    Coordinate,
    NormalRouteResponse,
    RoutePathPoint,
    SafeRouteResponse,
    RouteSegmentResponse,
)
from app.schemas.cooling_spot import CoolingSpotResponse
from app.schemas.risk_analysis import RiskEvaluateRequest, RiskEvaluateResponse
from app.schemas.rest_decision import RestDecisionRequest
from app.schemas.weather import ForecastWeatherResponse
from app.services.asos import (
    AsosConfigurationError,
    AsosDataNotFoundError,
    AsosProviderError,
    get_asos_hourly,
)
from app.services.tmap import PedestrianRoute, get_pedestrian_route
from app.config import settings
from app.services.risk_analysis import evaluate_risk
from app.services.rest_decision import RestDecisionService
from app.services.rest_weather import resolve_rest_weather
from app.services.weather import (
    WeatherForecastNotFoundError,
    get_current_weather,
    get_forecast_weather,
)
from app.time_utils import to_utc_aware, to_utc_naive, utc_naive_to_seoul


class RouteSegmentNotFoundError(Exception):
    """이동구간을 찾을 수 없습니다."""


class RouteSegmentConflictError(Exception):
    """현재 일정 상태에서 이동구간을 만들 수 없습니다."""


class SafeRouteNotFoundError(Exception):
    """조건에 맞는 쿨링스팟 안전경로를 찾을 수 없습니다."""


async def recommend_route(
    session: AsyncSession,
    *,
    route_segment_id: int,
    current_continuous_exposure_minutes: int,
    planned_rest_minutes: int,
    max_additional_minutes: int,
) -> tuple[RiskEvaluateResponse, RouteSegmentResponse, SafeRouteResponse | None, str | None]:
    """정상 경로의 위험도를 판정하고 필요할 때만 안전경로를 추천합니다."""
    normal_route = await get_route_segment(session, route_segment_id)
    if normal_route.departure_time is None:
        raise RouteSegmentNotFoundError("route segment departure time is missing")
    try:
        weather = await get_forecast_weather(
            normal_route.destination.latitude,
            normal_route.destination.longitude,
            normal_route.departure_time,
        )
    except WeatherForecastNotFoundError:
        # 과거 일정 시각이나 예보 공백 구간에서도 데모 흐름이 멈추지 않도록
        # 목적지의 현재 관측값으로 위험 판단을 계속한다.
        weather = await get_current_weather(
            normal_route.destination.latitude,
            normal_route.destination.longitude,
        )
    model_weather = await _get_model_weather(normal_route.departure_time)
    expected_exposure = current_continuous_exposure_minutes + normal_route.walking_minutes
    risk = evaluate_risk(
        RiskEvaluateRequest(
            route_option_id=normal_route.route_option_id,
            temperature=weather.temperature,
            humidity=weather.humidity,
            observed_at=weather.forecast_at if hasattr(weather, "forecast_at") else weather.observed_at,
            walking_minutes=normal_route.walking_minutes,
            current_continuous_exposure_minutes=current_continuous_exposure_minutes,
            expected_continuous_exposure_minutes=expected_exposure,
            wind_speed=model_weather["wind_speed"],
            solar_radiation=model_weather["solar_radiation"],
            surface_pressure=model_weather["surface_pressure"],
        )
    )
    origin = normal_route.origin
    destination = normal_route.destination
    departure = normal_route.departure_time
    candidates = await _safe_route_candidates(
        session,
        cooling_spot_id=None,
        at=departure.time(),
        origin=origin,
        destination=destination,
    )
    nearest_distance = (
        int(round(_approximate_route_distance(origin, candidates[0])))
        if candidates
        else None
    )
    should_recommend_safe_route = await _should_recommend_safe_route(
        normal_route=normal_route,
        weather=weather,
        model_weather=model_weather,
        current_continuous_exposure_minutes=current_continuous_exposure_minutes,
        nearest_cooling_spot_distance_meters=nearest_distance,
    )
    if not should_recommend_safe_route:
        return risk, normal_route, None, None
    try:
        safe_route = await create_safe_route(
            session,
            route_segment_id=route_segment_id,
            cooling_spot_id=None,
            planned_rest_minutes=planned_rest_minutes,
            max_additional_minutes=max_additional_minutes,
        )
    except SafeRouteNotFoundError as exc:
        return risk, normal_route, None, str(exc)
    return risk, normal_route, safe_route, None


async def _should_recommend_safe_route(
    *,
    normal_route: RouteSegmentResponse,
    weather: ForecastWeatherResponse,
    model_weather: dict[str, float | None],
    current_continuous_exposure_minutes: int,
    nearest_cooling_spot_distance_meters: int | None,
) -> bool:
    """동일한 XGBoost 휴식 판단으로 안전경로 생성 여부를 결정합니다."""
    observed_at = (
        weather.forecast_at
        if hasattr(weather, "forecast_at")
        else weather.observed_at
    )
    request = RestDecisionRequest(
        continuousWalkingMinutes=current_continuous_exposure_minutes,
        totalWalkingMinutes=(
            current_continuous_exposure_minutes + normal_route.walking_minutes
        ),
        minutesSinceLastRest=current_continuous_exposure_minutes,
        recentRestMinutes=0,
        stationId=settings.kma_asos_station_id,
        temperature=weather.temperature,
        humidity=weather.humidity,
        windSpeed=model_weather["wind_speed"],
        observedAt=observed_at,
        nextTravelMinutes=normal_route.walking_minutes,
        coolingSpotNearby=(
            nearest_cooling_spot_distance_meters is not None
            and nearest_cooling_spot_distance_meters <= 500
        ),
        distanceToCoolingSpotMeters=nearest_cooling_spot_distance_meters,
    )
    resolved_weather = await resolve_rest_weather(request)
    service = RestDecisionService()
    prediction = service.predict_model_status(
        resolved_weather.request,
        resolved_weather.wbgt,
    )
    decision, _ = await service.decide(
        resolved_weather.request,
        model_prediction=prediction,
    )
    return decision.should_rest


async def _get_model_weather(departure_time: datetime) -> dict[str, float | None]:
    """Load optional ASOS features required by the trained risk artifact.

    Forecast/current weather remains the source for the displayed route weather.
    ASOS is only an enrichment step for wind, solar radiation, and pressure; if
    it is unavailable, risk analysis safely falls back to the existing rules.
    """
    empty = {
        "wind_speed": None,
        "solar_radiation": None,
        "surface_pressure": None,
    }
    try:
        response = await get_asos_hourly(
            settings.kma_asos_station_id,
            departure_time,
            departure_time,
        )
    except (
        AsosConfigurationError,
        AsosDataNotFoundError,
        AsosProviderError,
        ValueError,
    ):
        return empty
    if not response.observations:
        return empty
    target_time = to_utc_aware(departure_time)
    observation = min(
        response.observations,
        key=lambda item: abs((to_utc_aware(item.observed_at) - target_time).total_seconds()),
    )
    return {
        "wind_speed": observation.wind_speed,
        "solar_radiation": observation.solar_radiation,
        "surface_pressure": observation.surface_pressure,
    }


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


async def create_safe_route(
    session: AsyncSession,
    *,
    route_segment_id: int,
    cooling_spot_id: int | None,
    planned_rest_minutes: int,
    max_additional_minutes: int,
) -> SafeRouteResponse:
    """운영 중인 쿨링스팟을 경유하는 보행 안전경로를 생성하고 저장합니다."""
    segment = (
        await session.execute(
            select(RouteSegment)
            .options(selectinload(RouteSegment.route_options))
            .where(RouteSegment.id == route_segment_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if segment is None:
        raise RouteSegmentNotFoundError("route segment not found")
    normal = next((item for item in segment.route_options if item.route_type == RouteType.NORMAL), None)
    if normal is None:
        raise RouteSegmentNotFoundError("normal route option not found")

    origin = Coordinate(latitude=float(segment.origin_latitude), longitude=float(segment.origin_longitude), name="현재 위치")
    destination = Coordinate(latitude=float(segment.destination_latitude), longitude=float(segment.destination_longitude), name="방문지")
    departure = utc_naive_to_seoul(segment.departure_time) or datetime.now().astimezone()
    candidates = await _safe_route_candidates(session, cooling_spot_id, departure.time(), origin, destination)
    if not candidates:
        raise SafeRouteNotFoundError("운영 중인 쿨링스팟이 없습니다")

    best: tuple[CoolingSpot, PedestrianRoute, PedestrianRoute, int] | None = None
    # 공공 쉼터와 기업 쿨링스팟을 구분하지 않고, 현재 위치에서 가장
    # 가까운 후보 하나를 우선 경유지로 사용한다. 방문지까지의 거리까지
    # 합산하면 출발지 바로 옆 쉼터보다 먼 후보가 선택될 수 있다.
    for spot in candidates[:1]:
        waypoint = Coordinate(latitude=float(spot.latitude), longitude=float(spot.longitude), name=spot.name)
        to_spot = await get_pedestrian_route(origin, waypoint)
        from_spot = await get_pedestrian_route(waypoint, destination)
        walking_minutes = to_spot.walking_minutes + from_spot.walking_minutes
        additional = max(0, walking_minutes - normal.walking_minutes)
        if best is None or walking_minutes < best[3]:
            best = (spot, to_spot, from_spot, walking_minutes)
    if best is None:
        raise SafeRouteNotFoundError(f"추가 이동 {max_additional_minutes}분 이내의 쿨링스팟이 없습니다")

    spot, to_spot, from_spot, walking_minutes = best
    additional = max(0, walking_minutes - normal.walking_minutes)
    arrival_utc = (segment.departure_time or datetime.utcnow()) + timedelta(minutes=walking_minutes + planned_rest_minutes)
    spot_arrival_utc = (segment.departure_time or datetime.utcnow()) + timedelta(minutes=to_spot.walking_minutes)
    path = _combine_paths(to_spot.path, from_spot.path)
    option = RouteOption(
        route_segment_id=segment.id,
        cooling_spot_id=spot.id,
        route_type=RouteType.SAFE,
        total_distance_meters=to_spot.distance_meters + from_spot.distance_meters,
        walking_minutes=walking_minutes,
        total_travel_minutes=walking_minutes + planned_rest_minutes,
        estimated_arrival_time=arrival_utc,
        detour_distance_meters=max(0, to_spot.distance_meters + from_spot.distance_meters - normal.total_distance_meters),
        additional_minutes=additional,
        detour_ratio=Decimal(str((to_spot.distance_meters + from_spot.distance_meters) / normal.total_distance_meters)),
        minutes_to_cooling_spot=to_spot.walking_minutes,
        planned_rest_minutes=planned_rest_minutes,
        minutes_from_cooling_spot=from_spot.walking_minutes,
        cooling_spot_arrival_time=spot_arrival_utc,
        path=[point.model_dump() for point in path],
        selected=False,
    )
    session.add(option)
    await session.flush()
    return SafeRouteResponse(
        route_segment_id=segment.id,
        route_option_id=option.id,
        route_type=RouteType.SAFE,
        cooling_spot=CoolingSpotResponse.model_validate(spot),
        distance_meters=option.total_distance_meters,
        walking_minutes=walking_minutes,
        total_travel_minutes=option.total_travel_minutes,
        additional_minutes=additional,
        planned_rest_minutes=planned_rest_minutes,
        estimated_arrival_time=utc_naive_to_seoul(arrival_utc) or arrival_utc,
        path=path,
    )


async def _safe_route_candidates(
    session: AsyncSession,
    cooling_spot_id: int | None,
    at: time,
    origin: Coordinate,
    destination: Coordinate,
) -> list[CoolingSpot]:
    statement = select(CoolingSpot)
    if cooling_spot_id is not None:
        statement = statement.where(CoolingSpot.id == cooling_spot_id)
    spots = list((await session.execute(statement)).scalars().all())
    open_spots = [
        spot
        for spot in spots
        if _is_open(spot, at)
        and (
            _approximate_route_distance(origin, spot)
            <= settings.cooling_spot_search_radius_meters
            or _approximate_route_distance(destination, spot)
            <= settings.cooling_spot_search_radius_meters
        )
    ]
    # 현재 위치에서 가까운 순서로 정렬한다. 안전경로는 "현재 위치 →
    # 쿨링스팟 → 방문지" 흐름이므로, 경유지 접근성이 최우선이다.
    return sorted(
        open_spots,
        key=lambda spot: _approximate_route_distance(origin, spot),
    )


def _approximate_route_distance(point: Coordinate, spot: CoolingSpot) -> float:
    latitude_delta = (point.latitude - float(spot.latitude)) * 111_000
    longitude_delta = (point.longitude - float(spot.longitude)) * 111_000 * cos(radians(point.latitude))
    return (latitude_delta**2 + longitude_delta**2) ** 0.5


def _is_open(spot: CoolingSpot, at: time) -> bool:
    if spot.open_time is None or spot.close_time is None:
        return True
    if spot.open_time <= spot.close_time:
        return spot.open_time <= at <= spot.close_time
    return at >= spot.open_time or at <= spot.close_time


def _combine_paths(first: list[RoutePathPoint], second: list[RoutePathPoint]) -> list[RoutePathPoint]:
    return first + (second[1:] if first and second and first[-1] == second[0] else second)


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
