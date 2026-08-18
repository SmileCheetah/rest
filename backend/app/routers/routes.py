from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.route import (
    NormalRouteRequest,
    NormalRouteResponse,
    RouteSegmentCreateRequest,
    RouteSegmentResponse,
    RouteRecommendationRequest,
    RouteRecommendationResponse,
    SafeRouteRequest,
    SafeRouteResponse,
)
from app.services.routes import (
    RouteSegmentConflictError,
    RouteSegmentNotFoundError,
    SafeRouteNotFoundError,
    calculate_normal_route,
    create_safe_route,
    create_route_segment,
    get_route_segment,
    recommend_route,
)
from app.services.tmap import TmapConfigurationError, TmapProviderError
from app.services.weather import (
    WeatherConfigurationError,
    WeatherForecastNotFoundError,
    WeatherProviderError,
)

routes_router = APIRouter(prefix="/routes", tags=["routes"])
route_segments_router = APIRouter(prefix="/route-segments", tags=["route-segments"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@routes_router.post(
    "/normal",
    response_model=NormalRouteResponse,
    summary="일반 보행 경로 생성",
)
async def normal_route(request: NormalRouteRequest) -> NormalRouteResponse:
    try:
        return await calculate_normal_route(
            request.origin,
            request.destination,
            request.departureTime,
        )
    except (TmapConfigurationError, WeatherConfigurationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (TmapProviderError, WeatherProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@routes_router.post("/safe", response_model=SafeRouteResponse, summary="쿨링스팟 경유 안전경로 생성")
async def safe_route(request: SafeRouteRequest, session: DbSession) -> SafeRouteResponse:
    try:
        async with session.begin():
            return await create_safe_route(
                session,
                route_segment_id=request.routeSegmentId,
                cooling_spot_id=request.coolingSpotId,
                planned_rest_minutes=request.plannedRestMinutes,
                max_additional_minutes=request.maxAdditionalMinutes,
            )
    except RouteSegmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SafeRouteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except TmapConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except TmapProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@routes_router.post(
    "/recommendation",
    response_model=RouteRecommendationResponse,
    summary="위험 판단 기반 안전경로 추천",
)
async def route_recommendation(
    request: RouteRecommendationRequest,
    session: DbSession,
) -> RouteRecommendationResponse:
    try:
        async with session.begin():
            risk, normal_route, safe_route, message = await recommend_route(
                session,
                route_segment_id=request.routeSegmentId,
                current_continuous_exposure_minutes=request.currentContinuousExposureMinutes,
                planned_rest_minutes=request.plannedRestMinutes,
                max_additional_minutes=request.maxAdditionalMinutes,
            )
        return RouteRecommendationResponse(
            risk=risk,
            normal_route=normal_route,
            safe_route=safe_route,
            shelter_recommendation_message=message,
        )
    except RouteSegmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (TmapConfigurationError, WeatherConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except (TmapProviderError, WeatherProviderError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except WeatherForecastNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@route_segments_router.post(
    "",
    response_model=RouteSegmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="이동구간 생성",
)
async def add_route_segment(
    request: RouteSegmentCreateRequest,
    session: DbSession,
) -> RouteSegmentResponse:
    try:
        async with session.begin():
            return await create_route_segment(
                session,
                work_session_id=request.workSessionId,
                schedule_id=request.scheduleId,
                origin=request.origin,
                destination=request.destination,
                departure_time=request.departureTime,
            )
    except RouteSegmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except WeatherForecastNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RouteSegmentConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (TmapConfigurationError, WeatherConfigurationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (TmapProviderError, WeatherProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@route_segments_router.get(
    "/{route_segment_id}",
    response_model=RouteSegmentResponse,
    summary="이동구간 조회",
)
async def route_segment_detail(
    route_segment_id: int,
    session: DbSession,
) -> RouteSegmentResponse:
    try:
        return await get_route_segment(session, route_segment_id)
    except RouteSegmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
