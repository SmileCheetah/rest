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


class RestWeatherUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class RestWeatherResult:
    request: RestDecisionRequest
    source: str


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
        return RestWeatherResult(request=request, source="REQUEST_FALLBACK")


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
