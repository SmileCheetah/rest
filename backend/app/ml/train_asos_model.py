from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from app.ml.era5 import asos_to_weather_observations
from app.ml.risk_modeling import (
    compare_models,
    generate_dataset_from_weather,
    save_comparison_artifacts,
)
from app.services.asos import get_asos_hourly


async def _fetch_chunks(station_id: int, start_at: datetime, end_at: datetime):
    current = start_at
    while current <= end_at:
        chunk_end = min(current + timedelta(days=31), end_at)
        response = await get_asos_hourly(station_id, current, chunk_end)
        yield response
        current = chunk_end + timedelta(hours=1)


async def _run(args: argparse.Namespace) -> None:
    responses = [
        response
        async for response in _fetch_chunks(
            args.station_id, args.start_at, args.end_at
        )
    ]
    observations = [
        asos_to_weather_observations(
            response,
            latitude=args.latitude,
            longitude=args.longitude,
        )
        for response in responses
    ]
    import numpy as np
    from app.ml.era5 import WeatherObservations

    combined = WeatherObservations(
        observed_at=np.concatenate([item.observed_at for item in observations]),
        temperature=np.concatenate([item.temperature for item in observations]),
        humidity=np.concatenate([item.humidity for item in observations]),
        wind_speed=np.concatenate([item.wind_speed for item in observations]),
        solar_radiation=np.concatenate([item.solar_radiation for item in observations]),
        direct_solar_fraction=np.concatenate(
            [item.direct_solar_fraction for item in observations]
        ),
        surface_pressure=np.concatenate(
            [item.surface_pressure for item in observations]
        ),
        cosine_solar_zenith=np.concatenate(
            [item.cosine_solar_zenith for item in observations]
        ),
    )
    dataset = generate_dataset_from_weather(
        combined,
        scenarios_per_weather=args.scenarios_per_weather,
        seed=args.seed,
        source="kma_asos_hourly_with_erbs_direct_radiation_estimate",
    )
    comparison = compare_models(dataset, seed=args.seed)
    save_comparison_artifacts(comparison, args.artifact_directory)
    print(f"observations: {len(combined.observed_at)}")
    print(f"rows: {len(dataset.labels)}")
    print(f"final_model: {comparison.best_model_name}")
    print(f"model: {args.artifact_directory / 'risk_classifier.joblib'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the risk classifier from KMA ASOS data.")
    parser.add_argument("--station-id", type=int, required=True)
    parser.add_argument("--start-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--end-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--scenarios-per-weather", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260818)
    parser.add_argument("--artifact-directory", type=Path, default=Path("artifacts/risk-model"))
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
