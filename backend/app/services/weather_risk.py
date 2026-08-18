from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np
from thermofeel import calculate_wbgt_liljegren
from thermofeel.approximations import approximate_fdir_erbs

from app.schemas.asos import AsosHourlyObservation
from app.schemas.weather_risk import (
    WeatherRiskBasis,
    WeatherRiskLevel,
    WeatherRiskReferencePoint,
)
from app.services.asos import (
    AsosConfigurationError,
    AsosDataNotFoundError,
    AsosProviderError,
    get_asos_hourly,
)
from app.services.weather import calculate_apparent_temperature
from earthkit.meteo.solar.array import cos_solar_zenith_angle_integrated

WORK_INTENSITY = "MODERATE"
# ASOS station metadata needed for the solar-geometry part of Liljegren WBGT.
# Add coordinates here when another station becomes a supported default.
ASOS_STATION_COORDINATES = {
    108: (37.5714, 126.9658),
}
WBGT_ANCHORS = ((18.0, 0), (21.0, 30), (25.0, 70), (28.0, 90), (30.0, 100))
APPARENT_TEMPERATURE_ANCHORS = (
    (28.0, 0),
    (31.0, 30),
    (33.0, 60),
    (35.0, 80),
    (38.0, 95),
    (40.0, 100),
)


class WeatherRiskUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class WeatherRiskWeather:
    observation: AsosHourlyObservation
    source: str


def calculate_weather_risk(
    *,
    temperature: float,
    humidity: float,
    wind_speed: float | None,
    observed_at: datetime,
    wbgt: float | None,
    solar_radiation: float | None,
    surface_pressure: float | None,
    latitude: float | None,
    longitude: float | None,
) -> tuple[int, WeatherRiskLevel, WeatherRiskBasis, float, dict | None, str]:
    calculated_wbgt = wbgt
    if calculated_wbgt is None and None not in (
        wind_speed,
        solar_radiation,
        surface_pressure,
        latitude,
        longitude,
    ):
        calculated_wbgt = _calculate_wbgt(
            temperature,
            humidity,
            wind_speed,
            solar_radiation,
            surface_pressure,
            observed_at,
            latitude,
            longitude,
        )

    if calculated_wbgt is not None:
        basis: WeatherRiskBasis = "WBGT"
        input_value = calculated_wbgt
        anchors = WBGT_ANCHORS
        explanation = _explain("WBGT", input_value, anchors)
    else:
        apparent = calculate_apparent_temperature(
            temperature,
            humidity,
            observed_at,
            wind_speed,
        )
        basis = "APPARENT_TEMPERATURE"
        input_value = apparent
        anchors = APPARENT_TEMPERATURE_ANCHORS
        explanation = _explain("체감온도", input_value, anchors)

    score, lower, upper = interpolate_score(input_value, anchors)
    return (
        score,
        classify_weather_risk(score),
        basis,
        input_value,
        {
            "lowerAnchor": WeatherRiskReferencePoint(value=lower[0], score=lower[1]),
            "upperAnchor": WeatherRiskReferencePoint(value=upper[0], score=upper[1]),
        },
        explanation,
    )


def interpolate_score(
    value: float,
    anchors: tuple[tuple[float, int], ...],
) -> tuple[int, tuple[float, int], tuple[float, int]]:
    if value <= anchors[0][0]:
        return anchors[0][1], anchors[0], anchors[0]
    if value >= anchors[-1][0]:
        return anchors[-1][1], anchors[-1], anchors[-1]
    for lower, upper in zip(anchors, anchors[1:]):
        if lower[0] <= value <= upper[0]:
            ratio = (value - lower[0]) / (upper[0] - lower[0])
            return round(lower[1] + ratio * (upper[1] - lower[1])), lower, upper
    raise ValueError("value did not fit an anchor interval")


def classify_weather_risk(score: int) -> WeatherRiskLevel:
    if score <= 39:
        return "LOW"
    if score <= 69:
        return "MEDIUM"
    return "HIGH"


async def resolve_weather(
    *,
    station_id: int,
    observed_at: datetime,
    temperature: float | None,
    humidity: float | None,
    wind_speed: float | None,
    solar_radiation: float | None,
    surface_pressure: float | None,
) -> WeatherRiskWeather:
    try:
        response = await get_asos_hourly(station_id, observed_at, observed_at)
        observation = min(
            response.observations,
            key=lambda item: abs((item.observed_at - observed_at).total_seconds()),
        )
        return WeatherRiskWeather(observation=observation, source="KMA_ASOS")
    except (
        AsosConfigurationError,
        AsosDataNotFoundError,
        AsosProviderError,
        ValueError,
    ) as exc:
        if temperature is None or humidity is None:
            raise WeatherRiskUnavailableError(
                "ASOS weather is unavailable and request fallback is incomplete"
            ) from exc
        return WeatherRiskWeather(
            observation=AsosHourlyObservation(
                station_id=station_id,
                station_name="request",
                observed_at=observed_at,
                temperature=temperature,
                humidity=humidity,
                wind_speed=wind_speed,
                solar_radiation=solar_radiation,
                surface_pressure=surface_pressure,
            ),
            source="REQUEST_FALLBACK",
        )


def station_coordinates(station_id: int) -> tuple[float, float] | None:
    return ASOS_STATION_COORDINATES.get(station_id)


def _calculate_wbgt(
    temperature: float,
    humidity: float,
    wind_speed: float,
    solar_radiation: float,
    surface_pressure: float,
    observed_at: datetime,
    latitude: float,
    longitude: float,
) -> float:
    end_at = observed_at.astimezone(UTC)
    cosine_zenith = cos_solar_zenith_angle_integrated(
        (end_at - timedelta(hours=1)).replace(tzinfo=None),
        end_at.replace(tzinfo=None),
        np.array([latitude]),
        np.array([longitude]),
    )
    cossza = float(np.asarray(cosine_zenith).reshape(-1)[0])
    direct = float(approximate_fdir_erbs(solar_radiation, cossza))
    fraction = max(0.0, min(0.9, direct / solar_radiation)) if solar_radiation > 0 else 0.0
    wbgt_kelvin = calculate_wbgt_liljegren(
        temperature + 273.15,
        humidity,
        surface_pressure,
        wind_speed,
        solar_radiation,
        fraction,
        cossza,
    )
    return float(np.asarray(wbgt_kelvin).reshape(-1)[0] - 273.15)


def _explain(
    label: str,
    value: float,
    anchors: tuple[tuple[float, int], ...],
) -> str:
    score, lower, upper = interpolate_score(value, anchors)
    if lower == upper:
        return f"{label} {value:.1f} 기준으로 {score}점입니다."
    return (
        f"{label} {value:.1f}은 {lower[0]:.1f}({lower[1]}점)과 "
        f"{upper[0]:.1f}({upper[1]}점) 사이이며, 보간 결과 {score}점입니다."
    )
