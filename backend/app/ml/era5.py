from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from earthkit.meteo.solar.array import cos_solar_zenith_angle_integrated
from thermofeel import calculate_relative_humidity_percent
from thermofeel.approximations import approximate_fdir_erbs

from app.schemas.asos import AsosHourlyResponse


ERA5_VARIABLE_ALIASES = {
    "temperature": ("t2m", "2m_temperature"),
    "dew_point": ("d2m", "2m_dewpoint_temperature"),
    "eastward_wind": ("u10", "10m_u_component_of_wind"),
    "northward_wind": ("v10", "10m_v_component_of_wind"),
    "surface_pressure": ("sp", "surface_pressure"),
    "solar_radiation": ("ssrd", "surface_solar_radiation_downwards"),
    "direct_solar_radiation": (
        "fdir",
        "total_sky_direct_solar_radiation_at_surface",
    ),
}


@dataclass(frozen=True)
class WeatherObservations:
    observed_at: np.ndarray
    temperature: np.ndarray
    humidity: np.ndarray
    wind_speed: np.ndarray
    solar_radiation: np.ndarray
    direct_solar_fraction: np.ndarray
    surface_pressure: np.ndarray
    cosine_solar_zenith: np.ndarray

    def __post_init__(self) -> None:
        lengths = {
            len(getattr(self, field_name))
            for field_name in self.__dataclass_fields__
        }
        if lengths == {0}:
            raise ValueError("weather observations cannot be empty")
        if len(lengths) != 1:
            raise ValueError("weather observation columns must have equal lengths")


def load_era5_netcdf(
    path: Path,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    accumulation_seconds: int = 3_600,
) -> WeatherObservations:
    """Load one ERA5 grid point and convert it to Liljegren input units."""
    if accumulation_seconds <= 0:
        raise ValueError("accumulation_seconds must be positive")
    if (latitude is None) != (longitude is None):
        raise ValueError("latitude and longitude must be provided together")

    import xarray as xr

    with xr.open_dataset(path) as source:
        dataset = source
        latitude_name = _coordinate_name(dataset, ("latitude", "lat"))
        longitude_name = _coordinate_name(dataset, ("longitude", "lon"))
        if latitude is not None and longitude is not None:
            dataset = dataset.sel(
                {latitude_name: latitude, longitude_name: longitude},
                method="nearest",
            )
        else:
            _require_single_grid_point(dataset, latitude_name, longitude_name)
            dataset = dataset.isel({latitude_name: 0, longitude_name: 0})

        time_name = _coordinate_name(dataset, ("valid_time", "time"))
        observed_at = _utc_datetimes(dataset[time_name].values)
        t2m_kelvin = _one_dimensional_values(dataset, "temperature", time_name)
        d2m_kelvin = _one_dimensional_values(dataset, "dew_point", time_name)
        u10 = _one_dimensional_values(dataset, "eastward_wind", time_name)
        v10 = _one_dimensional_values(dataset, "northward_wind", time_name)
        pressure_pa = _one_dimensional_values(dataset, "surface_pressure", time_name)
        ssrd_joules = _one_dimensional_values(dataset, "solar_radiation", time_name)
        fdir_joules = _one_dimensional_values(
            dataset,
            "direct_solar_radiation",
            time_name,
        )
        selected_latitude = float(dataset[latitude_name].values)
        selected_longitude = float(dataset[longitude_name].values)

    solar_radiation = np.clip(ssrd_joules / accumulation_seconds, 0.0, None)
    direct_radiation = np.clip(fdir_joules / accumulation_seconds, 0.0, None)
    direct_fraction = np.divide(
        direct_radiation,
        solar_radiation,
        out=np.zeros_like(direct_radiation),
        where=solar_radiation > 0,
    )
    direct_fraction = np.clip(direct_fraction, 0.0, 0.9)
    humidity = np.clip(
        calculate_relative_humidity_percent(t2m_kelvin, d2m_kelvin),
        0.0,
        100.0,
    )
    cosine_solar_zenith = np.array(
        [
            _hourly_cosine_solar_zenith(
                value,
                selected_latitude,
                selected_longitude,
            )
            for value in observed_at
        ],
        dtype=float,
    )

    result = WeatherObservations(
        observed_at=np.array(observed_at, dtype=object),
        temperature=t2m_kelvin - 273.15,
        humidity=np.asarray(humidity, dtype=float),
        wind_speed=np.hypot(u10, v10),
        solar_radiation=solar_radiation,
        direct_solar_fraction=direct_fraction,
        surface_pressure=pressure_pa / 100.0,
        cosine_solar_zenith=cosine_solar_zenith,
    )
    _validate_observations(result)
    return result


def asos_to_weather_observations(
    response: AsosHourlyResponse,
    *,
    latitude: float,
    longitude: float,
) -> WeatherObservations:
    """Convert KMA ASOS hourly data into Liljegren input columns.

    ASOS provides global hourly radiation (icsr), not direct radiation. The
    direct component is therefore estimated with the Erbs model for labels.
    """
    rows = [
        item
        for item in response.observations
        if None not in (
            item.temperature,
            item.humidity,
            item.wind_speed,
            item.solar_radiation,
            item.surface_pressure,
        )
    ]
    if len(rows) < 10:
        raise ValueError("at least 10 complete ASOS observations are required")

    observed_at = np.array([item.observed_at for item in rows], dtype=object)
    solar_radiation = np.array([item.solar_radiation for item in rows], dtype=float)
    utc_times = [value.astimezone(UTC) for value in observed_at]
    cosine_solar_zenith = np.array(
        [
            _hourly_cosine_solar_zenith(value, latitude, longitude)
            for value in utc_times
        ],
        dtype=float,
    )
    direct_radiation = np.where(
        solar_radiation > 0,
        np.asarray(approximate_fdir_erbs(solar_radiation, cosine_solar_zenith)),
        0.0,
    )
    direct_fraction = np.clip(
        np.divide(
            direct_radiation,
            solar_radiation,
            out=np.zeros_like(solar_radiation),
            where=solar_radiation > 0,
        ),
        0.0,
        0.9,
    )
    result = WeatherObservations(
        observed_at=observed_at,
        temperature=np.array([item.temperature for item in rows], dtype=float),
        humidity=np.array([item.humidity for item in rows], dtype=float),
        wind_speed=np.array([item.wind_speed for item in rows], dtype=float),
        solar_radiation=solar_radiation,
        direct_solar_fraction=direct_fraction,
        surface_pressure=np.array([item.surface_pressure for item in rows], dtype=float),
        cosine_solar_zenith=cosine_solar_zenith,
    )
    _validate_observations(result)
    return result


def _coordinate_name(dataset: Any, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in dataset.coords or name in dataset.dims:
            return name
    raise ValueError(f"ERA5 coordinate is missing; expected one of {candidates}")


def _require_single_grid_point(
    dataset: Any,
    latitude_name: str,
    longitude_name: str,
) -> None:
    if dataset.sizes.get(latitude_name, 1) != 1 or dataset.sizes.get(
        longitude_name,
        1,
    ) != 1:
        raise ValueError(
            "ERA5 file contains multiple grid points; provide latitude and longitude"
        )


def _one_dimensional_values(
    dataset: Any,
    canonical_name: str,
    time_name: str,
) -> np.ndarray:
    variable_name = next(
        (
            name
            for name in ERA5_VARIABLE_ALIASES[canonical_name]
            if name in dataset.data_vars
        ),
        None,
    )
    if variable_name is None:
        raise ValueError(
            f"ERA5 variable {canonical_name!r} is missing; expected one of "
            f"{ERA5_VARIABLE_ALIASES[canonical_name]}"
        )
    values = dataset[variable_name]
    for dimension, size in tuple(values.sizes.items()):
        if dimension != time_name and size == 1:
            values = values.isel({dimension: 0})
    if values.dims != (time_name,):
        raise ValueError(
            f"ERA5 variable {variable_name!r} must contain only the time dimension"
        )
    return np.asarray(values.values, dtype=float)


def _utc_datetimes(values: Any) -> list[datetime]:
    timestamps = np.asarray(values).astype("datetime64[ns]").astype(np.int64)
    return [datetime.fromtimestamp(value / 1_000_000_000, UTC) for value in timestamps]


def _hourly_cosine_solar_zenith(
    end_at: datetime,
    latitude: float,
    longitude: float,
) -> float:
    begin_at = end_at - timedelta(hours=1)
    value = cos_solar_zenith_angle_integrated(
        begin_at.replace(tzinfo=None),
        end_at.replace(tzinfo=None),
        np.array([latitude]),
        np.array([longitude]),
    )
    return float(np.asarray(value).reshape(-1)[0])


def _validate_observations(observations: WeatherObservations) -> None:
    numeric_fields = (
        "temperature",
        "humidity",
        "wind_speed",
        "solar_radiation",
        "direct_solar_fraction",
        "surface_pressure",
        "cosine_solar_zenith",
    )
    for field_name in numeric_fields:
        if not np.isfinite(getattr(observations, field_name)).all():
            raise ValueError(f"ERA5 field {field_name!r} contains non-finite values")
