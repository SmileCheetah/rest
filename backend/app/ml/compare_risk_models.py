import argparse
from pathlib import Path

from app.ml.risk_modeling import (
    compare_models,
    generate_synthetic_dataset,
    save_comparison_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare risk classifiers on one synthetic-label dataset."
    )
    parser.add_argument("--weather-samples", type=int, default=2_000)
    parser.add_argument("--scenarios-per-weather", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260818)
    parser.add_argument(
        "--artifact-directory",
        type=Path,
        default=Path("artifacts/risk-model"),
    )
    args = parser.parse_args()

    dataset = generate_synthetic_dataset(
        weather_samples=args.weather_samples,
        scenarios_per_weather=args.scenarios_per_weather,
        seed=args.seed,
    )
    comparison = compare_models(dataset, seed=args.seed)
    save_comparison_artifacts(comparison, args.artifact_directory)

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
