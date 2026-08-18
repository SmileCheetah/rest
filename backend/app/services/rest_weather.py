from __future__ import annotations

from dataclasses import dataclass

from app.schemas.asos import AsosHourlyObservation
from app.schemas.rest_decision import RestDecisionRequest
from app.services.asos import (
    AsosConfigurationError,
    AsosDataNotFoundError,
    AsosProviderError,
    get_asos_hourly,
)
from app.services.weather_risk import calculate_weather_risk, station_coordinates


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
        return RestWeatherResult(request=request, source="REQUEST_FALLBACK", wbgt=request.wbgt)


def _nearest_observation(
    observations: list[AsosHourlyObservation],
    request: RestDecisionRequest,
) -> AsosHourlyObservation:
    if not observations:
        raise RestWeatherUnavailableError("ASOS observations are empty")
    target = request.observed_at
    return min(
        observations,
        key=lambda item: abs((item.observed_at - target).total_seconds()),
    )
