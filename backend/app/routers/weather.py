from datetime import date, datetime
from typing import Annotated, Awaitable, Callable, TypeVar

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.weather import (
    CurrentWeatherResponse,
    ForecastWeatherResponse,
    HourlyWeatherResponse,
)
from app.schemas.living_index import LivingIndexResponse
from app.services.living_index import (
    LivingIndexConfigurationError,
    LivingIndexProviderError,
    get_living_weather_index,
)
from app.services.weather import (
    WeatherConfigurationError,
    WeatherForecastNotFoundError,
    WeatherProviderError,
    get_current_weather,
    get_forecast_weather,
    get_hourly_weather,
)

router = APIRouter(prefix="/weather", tags=["weather"])

Latitude = Annotated[float, Query(ge=33.0, le=39.0)]
Longitude = Annotated[float, Query(ge=124.0, le=132.0)]
ResponseT = TypeVar("ResponseT")


@router.get(
    "/living-index",
    response_model=LivingIndexResponse,
    summary="생활기상지수 조회",
)
async def living_index(
    area_no: Annotated[str, Query(alias="areaNo", pattern=r"^\d{10}$")] = "1100000000",
) -> LivingIndexResponse:
    try:
        return await get_living_weather_index(area_no)
    except LivingIndexConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LivingIndexProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get(
    "/current",
    response_model=CurrentWeatherResponse,
    summary="현재 날씨 조회",
)
async def current_weather(
    latitude: Latitude,
    longitude: Longitude,
) -> CurrentWeatherResponse:
    return await _handle_weather_request(
        lambda: get_current_weather(latitude, longitude)
    )


@router.get(
    "/hourly",
    response_model=HourlyWeatherResponse,
    summary="시간대별 날씨 조회",
)
async def hourly_weather(
    latitude: Latitude,
    longitude: Longitude,
    forecast_date: Annotated[date, Query(alias="date")],
) -> HourlyWeatherResponse:
    return await _handle_weather_request(
        lambda: get_hourly_weather(latitude, longitude, forecast_date)
    )


@router.get(
    "/forecast",
    response_model=ForecastWeatherResponse,
    summary="방문 예정 시각 날씨 조회",
)
async def forecast_weather(
    latitude: Latitude,
    longitude: Longitude,
    forecast_at: Annotated[datetime, Query(alias="datetime")],
) -> ForecastWeatherResponse:
    return await _handle_weather_request(
        lambda: get_forecast_weather(latitude, longitude, forecast_at)
    )


async def _handle_weather_request(
    request: Callable[[], Awaitable[ResponseT]],
) -> ResponseT:
    try:
        return await request()
    except WeatherConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except WeatherForecastNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except WeatherProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
