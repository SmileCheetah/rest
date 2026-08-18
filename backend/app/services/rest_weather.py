from __future__ import annotations

from dataclasses import dataclass
from math import exp

from app.schemas.asos import AsosHourlyObservation
from app.schemas.rest_decision import RestDecisionRequest
from app.services.asos import (
    AsosConfigurationError,
    AsosDataNotFoundError,
    AsosProviderError,
    get_asos_hourly,
)
from app.services.weather_risk import calculate_weather_risk, station_coordinates
from app.time_utils import to_utc_aware


class RestWeatherUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class RestWeatherResult:
    request: RestDecisionRequest
    source: str
    wbgt: float | None = None


async def resolve_rest_weather(request: RestDecisionRequest) -> RestWeatherResult:
    try:
        response = await get_asos_hourly(
            request.station_id,
            request.observed_at,
            request.observed_at,
        )
        observation = _nearest_observation(response.observations, request)
        if observation.temperature is None or observation.humidity is None:
            raise RestWeatherUnavailableError(
                "ASOS observation is missing temperature or humidity"
            )
        coordinates = station_coordinates(request.station_id)
        # A caller-provided WBGT is an explicit fallback; ASOS-derived WBGT
        # replaces it whenever the required observation fields are available.
        wbgt = request.wbgt
        if (
            observation.wind_speed is not None
            and observation.solar_radiation is not None
            and observation.surface_pressure is not None
            and coordinates is not None
        ):
            try:
                _, _, basis, input_value, _, _ = calculate_weather_risk(
                    temperature=observation.temperature,
                    humidity=observation.humidity,
                    wind_speed=observation.wind_speed,
                    observed_at=observation.observed_at,
                    wbgt=None,
                    solar_radiation=observation.solar_radiation,
                    surface_pressure=observation.surface_pressure,
                    latitude=coordinates[0],
                    longitude=coordinates[1],
                )
                if basis == "WBGT":
                    wbgt = input_value
            except (ValueError, TypeError, OverflowError):
                wbgt = None
        return RestWeatherResult(
            request=request.model_copy(
                update={
                    "temperature": observation.temperature,
                    "humidity": observation.humidity,
                    "wind_speed": observation.wind_speed,
                    "observed_at": observation.observed_at,
                }
            ),
            source="KMA_ASOS",
            wbgt=wbgt,
        )
    except (
        AsosConfigurationError,
        AsosDataNotFoundError,
        AsosProviderError,
        ValueError,
    ) as exc:
        if request.temperature is None or request.humidity is None:
            raise RestWeatherUnavailableError(
                "ASOS weather is unavailable and request weather fallback is incomplete"
            ) from exc
        return RestWeatherResult(
            request=request,
            source="REQUEST_FALLBACK",
            # ASOS가 일시적으로 실패해도 프론트가 보낸 현재 기온·습도로
            # 간이 WBGT를 만들어 AI 판단 흐름을 멈추지 않습니다.
            wbgt=request.wbgt
            if request.wbgt is not None
            else _estimate_wbgt(request.temperature, request.humidity),
        )


def _nearest_observation(
    observations: list[AsosHourlyObservation],
    request: RestDecisionRequest,
) -> AsosHourlyObservation:
    if not observations:
        raise RestWeatherUnavailableError("ASOS observations are empty")
    target = to_utc_aware(request.observed_at)
    return min(
        observations,
        key=lambda item: abs((to_utc_aware(item.observed_at) - target).total_seconds()),
    )


def _estimate_wbgt(temperature: float, humidity: float) -> float:
    """기온·습도만 있을 때 쓰는 간이 WBGT 추정값(그늘 기준)입니다."""
    saturation_vapor_pressure = 6.105 * exp((17.27 * temperature) / (237.7 + temperature))
    vapor_pressure = (humidity / 100) * saturation_vapor_pressure
    estimated = 0.567 * temperature + 0.393 * vapor_pressure + 3.94
    return round(max(-20, min(60, estimated)), 2)
