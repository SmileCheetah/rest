from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import joblib
import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    make_scorer,
    recall_score,
)
from thermofeel import calculate_wbgt_liljegren

from app.schemas.risk_analysis import RiskLevel
from app.services.risk_analysis import classify_risk
from app.services.weather import calculate_apparent_temperature

SEOUL_TZ = ZoneInfo("Asia/Seoul")
LABEL_POLICY_VERSION = "wbgt-niosh-moderate-mvp-1"
FEATURE_SELECTION_TOLERANCE = 0.005
RISK_LABELS: tuple[RiskLevel, ...] = (
    "MOVE_POSSIBLE",
    "REST_RECOMMENDED",
    "REST_REQUIRED",
)
FEATURE_NAMES = (
    "temperature",
    "humidity",
    "wind_speed",
    "solar_radiation",
    "surface_pressure",
    "walking_minutes",
    "current_continuous_exposure_minutes",
    "expected_continuous_exposure_minutes",
    "current_daily_exposure_minutes",
    "expected_daily_exposure_minutes",
    "current_daily_rest_minutes",
    "shelter_accessibility",
)


@dataclass(frozen=True)
class RiskDataset:
    features: np.ndarray
    labels: np.ndarray
    weather_at: np.ndarray
    estimated_wbgt: np.ndarray
    apparent_temperature: np.ndarray


@dataclass(frozen=True)
class ModelComparison:
    report: dict[str, Any]
    best_model_name: str
    best_model: Any
    selected_feature_names: tuple[str, ...]


def moderate_work_limit_minutes(estimated_wbgt: float) -> int:
    """Return permitted work minutes per hour for the MVP moderate-work policy."""
    if estimated_wbgt < 25.0:
        return 120
    if estimated_wbgt < 26.7:
        return 60
    if estimated_wbgt < 28.0:
        return 45
    if estimated_wbgt < 29.4:
        return 30
    if estimated_wbgt < 31.1:
        return 15
    return 0


def cumulative_exposure_penalty_minutes(
    daily_exposure_minutes: int,
    daily_rest_minutes: int,
) -> int:
    """MVP policy adjustment; this is not a value published by NIOSH."""
    if daily_exposure_minutes >= 240 and daily_rest_minutes < 30:
        return 15
    if daily_exposure_minutes >= 120 and daily_rest_minutes < 20:
        return 10
    return 0


def create_synthetic_label(
    *,
    estimated_wbgt: float,
    current_continuous_exposure_minutes: int,
    expected_continuous_exposure_minutes: int,
    current_daily_exposure_minutes: int,
    current_daily_rest_minutes: int,
) -> RiskLevel:
    base_limit = moderate_work_limit_minutes(estimated_wbgt)
    penalty = cumulative_exposure_penalty_minutes(
        current_daily_exposure_minutes,
        current_daily_rest_minutes,
    )
    adjusted_limit = max(0, base_limit - penalty)

    if adjusted_limit == 0 or current_continuous_exposure_minutes >= adjusted_limit:
        return "REST_REQUIRED"
    if (
        estimated_wbgt >= 25.0
        or expected_continuous_exposure_minutes >= adjusted_limit
        or penalty > 0
    ):
        return "REST_RECOMMENDED"
    return "MOVE_POSSIBLE"


def generate_synthetic_dataset(
    *,
    weather_samples: int = 2_000,
    scenarios_per_weather: int = 6,
    seed: int = 20260818,
) -> RiskDataset:
    if weather_samples < 10:
        raise ValueError("weather_samples must be at least 10")
    if scenarios_per_weather < 1:
        raise ValueError("scenarios_per_weather must be positive")

    rng = np.random.default_rng(seed)
    weather_at = _generate_weather_times(rng, weather_samples)
    day_of_year = np.array([item.timetuple().tm_yday for item in weather_at])
    local_hour = np.array([item.hour + item.minute / 60 for item in weather_at])
    cos_solar_zenith = _cosine_solar_zenith(day_of_year, local_hour)
    cloud_transmission = rng.beta(2.5, 1.8, weather_samples)

    seasonal_heat = np.sin(np.pi * (day_of_year - 121) / 153).clip(0, 1)
    afternoon_heat = np.exp(-((local_hour - 15.0) / 4.0) ** 2)
    temperature = np.clip(
        17.0
        + 11.0 * seasonal_heat
        + 5.0 * afternoon_heat
        + rng.normal(0, 2.8, weather_samples),
        12.0,
        42.0,
    )
    solar_radiation = np.clip(
        1_050.0 * cos_solar_zenith * cloud_transmission,
        0.0,
        1_050.0,
    )
    direct_fraction = np.clip(
        0.15 + 0.75 * cloud_transmission + rng.normal(0, 0.08, weather_samples),
        0.0,
        0.9,
    )
    direct_solar_radiation = solar_radiation * direct_fraction
    humidity = np.clip(
        82.0
        - 0.9 * (temperature - 20.0)
        - 22.0 * cloud_transmission
        + rng.normal(0, 9.0, weather_samples),
        20.0,
        100.0,
    )
    wind_speed = np.clip(rng.lognormal(0.35, 0.55, weather_samples), 0.2, 9.0)
    surface_pressure = np.clip(
        rng.normal(1_008.0, 8.0, weather_samples),
        975.0,
        1_035.0,
    )

    wbgt_kelvin = calculate_wbgt_liljegren(
        temperature + 273.15,
        humidity,
        surface_pressure,
        wind_speed,
        solar_radiation,
        direct_solar_radiation,
        cos_solar_zenith,
    )
    wbgt_celsius = np.asarray(wbgt_kelvin, dtype=float) - 273.15
    if np.isnan(wbgt_celsius).any():
        raise ValueError("Liljegren WBGT calculation did not converge")

    weather_index = np.repeat(np.arange(weather_samples), scenarios_per_weather)
    row_count = len(weather_index)
    walking_minutes = rng.integers(5, 61, row_count)
    current_continuous = rng.integers(0, 121, row_count)
    expected_continuous = current_continuous + walking_minutes
    current_daily_exposure = current_continuous + rng.integers(0, 241, row_count)
    expected_daily_exposure = current_daily_exposure + walking_minutes
    current_daily_rest = rng.integers(0, 91, row_count)
    shelter_accessibility = rng.uniform(0.0, 1.0, row_count)

    features = np.column_stack(
        (
            temperature[weather_index],
            humidity[weather_index],
            wind_speed[weather_index],
            solar_radiation[weather_index],
            surface_pressure[weather_index],
            walking_minutes,
            current_continuous,
            expected_continuous,
            current_daily_exposure,
            expected_daily_exposure,
            current_daily_rest,
            shelter_accessibility,
        )
    )
    labels = np.array(
        [
            create_synthetic_label(
                estimated_wbgt=float(wbgt_celsius[weather_idx]),
                current_continuous_exposure_minutes=int(current_continuous[row]),
                expected_continuous_exposure_minutes=int(expected_continuous[row]),
                current_daily_exposure_minutes=int(current_daily_exposure[row]),
                current_daily_rest_minutes=int(current_daily_rest[row]),
            )
            for row, weather_idx in enumerate(weather_index)
        ]
    )
    apparent_by_weather = np.array(
        [
            calculate_apparent_temperature(
                float(temperature[index]),
                float(humidity[index]),
                weather_at[index],
                float(wind_speed[index]),
            )
            for index in range(weather_samples)
        ]
    )

    return RiskDataset(
        features=features,
        labels=labels,
        weather_at=np.array(weather_at, dtype=object)[weather_index],
        estimated_wbgt=wbgt_celsius[weather_index],
        apparent_temperature=apparent_by_weather[weather_index],
    )


def compare_models(
    dataset: RiskDataset,
    *,
    train_fraction: float = 0.8,
    seed: int = 20260818,
) -> ModelComparison:
    train_indices, test_indices, cutoff = chronological_group_split(
        dataset.weather_at,
        train_fraction=train_fraction,
    )
    x_train = dataset.features[train_indices]
    y_train = dataset.labels[train_indices]
    x_test = dataset.features[test_indices]
    y_test = dataset.labels[test_indices]

    predictions: dict[str, np.ndarray] = {
        "rule_classifier": _predict_with_rule_classifier(dataset, test_indices),
    }
    fitted_models: dict[str, Any] = {
        name: _build_model(name, parameters, seed)
        for name, parameters in _default_model_parameters().items()
    }
    for name, model in fitted_models.items():
        model.fit(x_train, y_train)
        predictions[name] = model.predict(x_test)

    model_metrics = {
        name: _classification_metrics(y_test, predicted)
        for name, predicted in predictions.items()
    }
    best_baseline_name = max(
        fitted_models,
        key=lambda name: (
            model_metrics[name]["macro_f1"],
            model_metrics[name]["rest_required_recall"],
        ),
    )
    _, tuning_report = _tune_model_family(
        best_baseline_name,
        dataset,
        train_indices,
        seed=seed,
    )
    selected_feature_indices, feature_selection_report = _select_feature_subset(
        best_baseline_name,
        tuning_report["selected_parameters"],
        dataset,
        train_indices,
        seed=seed,
    )
    selected_feature_names = tuple(
        FEATURE_NAMES[index] for index in selected_feature_indices
    )
    tuned_model = _build_model(
        best_baseline_name,
        tuning_report["selected_parameters"],
        seed,
    )
    tuned_model.fit(x_train[:, selected_feature_indices], y_train)
    final_model_name = f"{best_baseline_name}_tuned"
    tuned_predictions = tuned_model.predict(x_test[:, selected_feature_indices])
    model_metrics[final_model_name] = _classification_metrics(
        y_test,
        tuned_predictions,
    )
    tuning_report["test_metrics"] = model_metrics[final_model_name]
    tuning_report["permutation_importance"] = _feature_importance(
        tuned_model,
        x_test[:, selected_feature_indices],
        y_test,
        feature_names=selected_feature_names,
        seed=seed,
    )
    report = {
        "label_policy_version": LABEL_POLICY_VERSION,
        "feature_names": list(FEATURE_NAMES),
        "selection_metric": "macro_f1, then REST_REQUIRED recall",
        "best_baseline_ml_model": best_baseline_name,
        "final_model": final_model_name,
        "split": {
            "strategy": "chronological weather-time group split",
            "cutoff": cutoff.isoformat(),
            "train_rows": int(len(train_indices)),
            "test_rows": int(len(test_indices)),
        },
        "dataset": {
            "rows": int(len(dataset.labels)),
            "label_distribution": dict(sorted(Counter(dataset.labels).items())),
            "wbgt_min": round(float(dataset.estimated_wbgt.min()), 3),
            "wbgt_max": round(float(dataset.estimated_wbgt.max()), 3),
            "wbgt_mean": round(float(dataset.estimated_wbgt.mean()), 3),
            "limitation": (
                "Synthetic-label agreement only; this is not validated "
                "heat-illness outcome accuracy."
            ),
        },
        "models": model_metrics,
        "tuning": tuning_report,
        "feature_selection": feature_selection_report,
    }
    return ModelComparison(
        report=report,
        best_model_name=final_model_name,
        best_model=tuned_model,
        selected_feature_names=selected_feature_names,
    )


def chronological_group_split(
    weather_at: np.ndarray,
    *,
    train_fraction: float,
) -> tuple[np.ndarray, np.ndarray, datetime]:
    if not 0.5 <= train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0.5 and 1.0")
    unique_times = sorted(set(weather_at.tolist()))
    cutoff_index = min(int(len(unique_times) * train_fraction), len(unique_times) - 1)
    cutoff = unique_times[cutoff_index]
    train_mask = np.array([item < cutoff for item in weather_at])
    test_mask = ~train_mask
    return np.flatnonzero(train_mask), np.flatnonzero(test_mask), cutoff


def save_comparison_artifacts(
    comparison: ModelComparison,
    artifact_directory: Path,
) -> None:
    artifact_directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": comparison.best_model,
            "model_name": comparison.best_model_name,
            "feature_names": comparison.selected_feature_names,
            "risk_labels": RISK_LABELS,
            "label_policy_version": LABEL_POLICY_VERSION,
        },
        artifact_directory / "risk_classifier.joblib",
    )
    with (artifact_directory / "comparison.json").open("w", encoding="utf-8") as file:
        json.dump(comparison.report, file, ensure_ascii=False, indent=2)


def _classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    report = classification_report(
        y_true,
        y_pred,
        labels=RISK_LABELS,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "balanced_accuracy": round(
            float(balanced_accuracy_score(y_true, y_pred)),
            6,
        ),
        "macro_f1": round(
            float(f1_score(y_true, y_pred, labels=RISK_LABELS, average="macro")),
            6,
        ),
        "rest_required_recall": round(
            float(
                recall_score(
                    y_true,
                    y_pred,
                    labels=["REST_REQUIRED"],
                    average="macro",
                    zero_division=0,
                )
            ),
            6,
        ),
        "confusion_matrix": confusion_matrix(
            y_true,
            y_pred,
            labels=RISK_LABELS,
        ).tolist(),
        "per_class": {
            label: {
                key: round(float(report[label][key]), 6)
                for key in ("precision", "recall", "f1-score")
            }
            for label in RISK_LABELS
        },
    }


def _default_model_parameters() -> dict[str, dict[str, Any]]:
    return {
        "random_forest": {
            "n_estimators": 300,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
            "max_depth": None,
        },
        "hist_gradient_boosting": {
            "learning_rate": 0.08,
            "max_iter": 200,
            "max_leaf_nodes": 31,
            "min_samples_leaf": 20,
            "l2_regularization": 0.1,
        },
    }


def _tuning_candidates(model_name: str) -> list[dict[str, Any]]:
    if model_name == "random_forest":
        return [
            _default_model_parameters()[model_name],
            {
                "n_estimators": 500,
                "min_samples_leaf": 1,
                "max_features": "sqrt",
                "max_depth": None,
            },
            {
                "n_estimators": 400,
                "min_samples_leaf": 3,
                "max_features": 0.8,
                "max_depth": 18,
            },
        ]
    if model_name == "hist_gradient_boosting":
        return [
            _default_model_parameters()[model_name],
            {
                "learning_rate": 0.05,
                "max_iter": 300,
                "max_leaf_nodes": 31,
                "min_samples_leaf": 15,
                "l2_regularization": 0.2,
            },
            {
                "learning_rate": 0.08,
                "max_iter": 250,
                "max_leaf_nodes": 15,
                "min_samples_leaf": 15,
                "l2_regularization": 0.5,
            },
            {
                "learning_rate": 0.06,
                "max_iter": 300,
                "max_leaf_nodes": 63,
                "min_samples_leaf": 25,
                "l2_regularization": 0.5,
            },
        ]
    raise ValueError(f"unsupported model family: {model_name}")


def _build_model(
    model_name: str,
    parameters: dict[str, Any],
    seed: int,
) -> Any:
    if model_name == "random_forest":
        return RandomForestClassifier(
            **parameters,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=seed,
        )
    if model_name == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            **parameters,
            class_weight="balanced",
            random_state=seed,
        )
    raise ValueError(f"unsupported model family: {model_name}")


def _tune_model_family(
    model_name: str,
    dataset: RiskDataset,
    outer_train_indices: np.ndarray,
    *,
    seed: int,
) -> tuple[Any, dict[str, Any]]:
    relative_train, relative_validation, cutoff = chronological_group_split(
        dataset.weather_at[outer_train_indices],
        train_fraction=0.8,
    )
    train_indices = outer_train_indices[relative_train]
    validation_indices = outer_train_indices[relative_validation]
    candidates: list[dict[str, Any]] = []
    best_parameters: dict[str, Any] | None = None
    best_key = (-1.0, -1.0)

    for parameters in _tuning_candidates(model_name):
        model = _build_model(model_name, parameters, seed)
        model.fit(dataset.features[train_indices], dataset.labels[train_indices])
        predicted = model.predict(dataset.features[validation_indices])
        metrics = _classification_metrics(dataset.labels[validation_indices], predicted)
        candidates.append({"parameters": parameters, "validation_metrics": metrics})
        candidate_key = (metrics["macro_f1"], metrics["rest_required_recall"])
        if candidate_key > best_key:
            best_key = candidate_key
            best_parameters = parameters

    if best_parameters is None:
        raise RuntimeError("no tuning candidate was evaluated")
    return _build_model(model_name, best_parameters, seed), {
        "model_family": model_name,
        "strategy": "chronological inner train/validation split",
        "validation_cutoff": cutoff.isoformat(),
        "train_rows": int(len(train_indices)),
        "validation_rows": int(len(validation_indices)),
        "selected_parameters": best_parameters,
        "candidates": candidates,
    }


def _feature_importance(
    model: Any,
    features: np.ndarray,
    labels: np.ndarray,
    *,
    feature_names: tuple[str, ...],
    seed: int,
) -> list[dict[str, Any]]:
    scorer = make_scorer(
        f1_score,
        labels=RISK_LABELS,
        average="macro",
        zero_division=0,
    )
    result = permutation_importance(
        model,
        features,
        labels,
        scoring=scorer,
        n_repeats=3,
        random_state=seed,
        n_jobs=1,
    )
    order = np.argsort(result.importances_mean)[::-1]
    return [
        {
            "feature": feature_names[index],
            "importance_mean": round(float(result.importances_mean[index]), 6),
            "importance_std": round(float(result.importances_std[index]), 6),
        }
        for index in order
    ]


def _select_feature_subset(
    model_name: str,
    parameters: dict[str, Any],
    dataset: RiskDataset,
    outer_train_indices: np.ndarray,
    *,
    seed: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    relative_train, relative_validation, cutoff = chronological_group_split(
        dataset.weather_at[outer_train_indices],
        train_fraction=0.8,
    )
    train_indices = outer_train_indices[relative_train]
    validation_indices = outer_train_indices[relative_validation]
    candidate_names = {
        "all_features": FEATURE_NAMES,
        "drop_label_unused": tuple(
            name
            for name in FEATURE_NAMES
            if name not in {"expected_daily_exposure_minutes", "shelter_accessibility"}
        ),
        "compact": tuple(
            name
            for name in FEATURE_NAMES
            if name
            not in {
                "walking_minutes",
                "expected_daily_exposure_minutes",
                "shelter_accessibility",
            }
        ),
    }
    candidates: list[dict[str, Any]] = []
    evaluated: list[tuple[np.ndarray, dict[str, Any]]] = []

    for candidate_name, names in candidate_names.items():
        indices = np.array([FEATURE_NAMES.index(name) for name in names])
        model = _build_model(model_name, parameters, seed)
        model.fit(
            dataset.features[train_indices][:, indices],
            dataset.labels[train_indices],
        )
        predicted = model.predict(dataset.features[validation_indices][:, indices])
        metrics = _classification_metrics(dataset.labels[validation_indices], predicted)
        candidates.append(
            {
                "name": candidate_name,
                "features": list(names),
                "validation_metrics": metrics,
            }
        )
        evaluated.append((indices, metrics))

    if not evaluated:
        raise RuntimeError("no feature subset was evaluated")
    best_macro_f1 = max(metrics["macro_f1"] for _, metrics in evaluated)
    eligible = [
        (indices, metrics)
        for indices, metrics in evaluated
        if metrics["macro_f1"] >= best_macro_f1 - FEATURE_SELECTION_TOLERANCE
    ]
    best_indices, _ = min(
        eligible,
        key=lambda item: (
            len(item[0]),
            -item[1]["rest_required_recall"],
            -item[1]["macro_f1"],
        ),
    )
    selected_names = [FEATURE_NAMES[index] for index in best_indices]
    return best_indices, {
        "strategy": "chronological validation feature ablation",
        "selection_rule": (
            "smallest subset within 0.005 macro F1 of the best candidate"
        ),
        "macro_f1_tolerance": FEATURE_SELECTION_TOLERANCE,
        "validation_cutoff": cutoff.isoformat(),
        "selected_features": selected_names,
        "candidates": candidates,
    }


def _predict_with_rule_classifier(
    dataset: RiskDataset,
    indices: np.ndarray,
) -> np.ndarray:
    walking = FEATURE_NAMES.index("walking_minutes")
    current = FEATURE_NAMES.index("current_continuous_exposure_minutes")
    expected = FEATURE_NAMES.index("expected_continuous_exposure_minutes")
    shelter = FEATURE_NAMES.index("shelter_accessibility")
    return np.array(
        [
            classify_risk(
                apparent_temperature=float(dataset.apparent_temperature[index]),
                walking_minutes=int(dataset.features[index, walking]),
                current_continuous_exposure_minutes=int(
                    dataset.features[index, current]
                ),
                expected_continuous_exposure_minutes=int(
                    dataset.features[index, expected]
                ),
                shelter_accessibility=float(dataset.features[index, shelter]),
            )
            for index in indices
        ]
    )


def _generate_weather_times(
    rng: np.random.Generator,
    count: int,
) -> list[datetime]:
    times: list[datetime] = []
    for _ in range(count):
        year = int(rng.integers(2021, 2026))
        day_offset = int(rng.integers(0, 153))
        hour = int(rng.integers(8, 19))
        minute = int(rng.choice((0, 30)))
        times.append(
            datetime(year, 5, 1, hour, minute, tzinfo=SEOUL_TZ)
            + timedelta(days=day_offset)
        )
    return sorted(times)


def _cosine_solar_zenith(
    day_of_year: np.ndarray,
    local_hour: np.ndarray,
) -> np.ndarray:
    latitude = math.radians(37.5665)
    declination = np.radians(
        23.44 * np.sin(2 * np.pi * (284 + day_of_year) / 365.0)
    )
    hour_angle = np.radians(15.0 * (local_hour - 12.5))
    cosine = (
        math.sin(latitude) * np.sin(declination)
        + math.cos(latitude) * np.cos(declination) * np.cos(hour_angle)
    )
    return np.clip(cosine, 0.01, 1.0)
