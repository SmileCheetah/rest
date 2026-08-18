from fastapi import APIRouter, HTTPException, status

from app.schemas.weather_risk import WeatherRiskRequest, WeatherRiskResponse
from app.services.weather_risk import (
    WeatherRiskUnavailableError,
    calculate_weather_risk,
    resolve_weather,
    station_coordinates,
)

router = APIRouter(prefix="/weather-risk", tags=["weather-risk"])


@router.post("/score", response_model=WeatherRiskResponse)
async def calculate_weather_risk_score(
    request: WeatherRiskRequest,
) -> WeatherRiskResponse:
    try:
        weather = await resolve_weather(
            station_id=request.station_id,
            observed_at=request.observed_at,
            temperature=request.temperature,
            humidity=request.humidity,
            wind_speed=request.wind_speed,
            solar_radiation=request.solar_radiation,
            surface_pressure=request.surface_pressure,
        )
    except WeatherRiskUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    observation = weather.observation
    if observation.temperature is None or observation.humidity is None:
        raise HTTPException(status_code=503, detail="temperature and humidity are unavailable")
    coordinates = station_coordinates(request.station_id)
    latitude = request.latitude if request.latitude is not None else (
        coordinates[0] if coordinates else None
    )
    longitude = request.longitude if request.longitude is not None else (
        coordinates[1] if coordinates else None
    )
    score, level, basis, input_value, reference, explanation = calculate_weather_risk(
        temperature=observation.temperature,
        humidity=observation.humidity,
        wind_speed=observation.wind_speed,
        observed_at=observation.observed_at,
        wbgt=request.wbgt,
        solar_radiation=observation.solar_radiation,
        surface_pressure=observation.surface_pressure,
        latitude=latitude,
        longitude=longitude,
    )
    level_ko = {"LOW": "하", "MEDIUM": "중", "HIGH": "상"}[level]
    return WeatherRiskResponse(
        weatherRiskScore=score,
        weatherRiskLevel=level,
        weatherRiskLevelKo=level_ko,
        basis=basis,
        inputValue=round(input_value, 2),
        workIntensity="MODERATE",
        weatherSource=weather.source,
        reference=reference,
        explanation=explanation,
    )
