import argparse
from pathlib import Path

from app.ml.era5 import load_era5_netcdf
from app.ml.risk_modeling import (
    compare_models,
    generate_dataset_from_weather,
    generate_synthetic_dataset,
    save_comparison_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare risk classifiers on one synthetic-label dataset."
    )
    parser.add_argument("--weather-samples", type=int, default=1_000)
    parser.add_argument("--scenarios-per-weather", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260818)
    parser.add_argument(
        "--era5-netcdf",
        type=Path,
        help="ERA5 hourly single-level NetCDF file. Uses synthetic weather if omitted.",
    )
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument(
        "--accumulation-seconds",
        type=int,
        default=3_600,
        help="Accumulation period for ssrd/fdir in the ERA5 file.",
    )
    parser.add_argument(
        "--artifact-directory",
        type=Path,
        default=Path("artifacts/risk-model"),
    )
    args = parser.parse_args()

    if args.era5_netcdf:
        observations = load_era5_netcdf(
            args.era5_netcdf,
            latitude=args.latitude,
            longitude=args.longitude,
            accumulation_seconds=args.accumulation_seconds,
        )
        dataset = generate_dataset_from_weather(
            observations,
            scenarios_per_weather=args.scenarios_per_weather,
            seed=args.seed,
        )
        source = str(args.era5_netcdf)
    else:
        dataset = generate_synthetic_dataset(
            weather_samples=args.weather_samples,
            scenarios_per_weather=args.scenarios_per_weather,
            seed=args.seed,
        )
        source = "synthetic weather"
    comparison = compare_models(dataset, seed=args.seed)
    save_comparison_artifacts(comparison, args.artifact_directory)

    print(f"weather_source: {source}")
    print("model                    accuracy  balanced  macro_f1  required_recall")
    for model_name, metrics in comparison.report["models"].items():
        print(
            f"{model_name:<24} "
            f"{metrics['accuracy']:.4f}    "
            f"{metrics['balanced_accuracy']:.4f}    "
            f"{metrics['macro_f1']:.4f}    "
            f"{metrics['rest_required_recall']:.4f}"
        )
    print(f"final_model: {comparison.best_model_name}")
    print(f"report: {args.artifact_directory / 'comparison.json'}")
    print(f"model: {args.artifact_directory / 'risk_classifier.joblib'}")


if __name__ == "__main__":
    main()
