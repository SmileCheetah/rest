"""MVP Heat Risk Score pipeline.

This module is intentionally separate from route planning. It predicts only
heat-related rest risk; a different service decides which route or shelter to
use.

The 0-100 score and the 50/25/10/10/5 weights are an MVP labeling policy. They
are not an official NIOSH or OSHA 0-100 score. WBGT bands are informed by heat
stress guidance, but the resulting synthetic labels must be validated against
real support-worker outcomes before production use.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

FEATURES = [
    "wbgt",
    "continuous_exposure_minutes",
    "next_travel_minutes",
    "time_since_rest_minutes",
    "cooling_spot_distance_m",
]
TARGET = "heat_risk_score"
DEFAULT_SEED = 42


@dataclass(frozen=True)
class HeatRiskConfig:
    """Adjustable MVP policy and synthetic-data settings."""

    seed: int = DEFAULT_SEED
    sample_count: int = 10_000
    add_noise: bool = True
    noise_std: float = 3.0
    train_fraction: float = 0.8
    max_downward_noise: float = 3.0


def _band_score(value: float, bands: tuple[tuple[float, int], ...]) -> int:
    for minimum, score in reversed(bands):
        if value >= minimum:
            return score
    return 0


def calculate_initial_risk_score(
    *,
    wbgt: float,
    continuous_exposure_minutes: float,
    next_travel_minutes: float,
    time_since_rest_minutes: float,
    cooling_spot_distance_m: float,
    add_noise: bool = False,
    rng: np.random.Generator | None = None,
    config: HeatRiskConfig | None = None,
) -> float:
    """Calculate the deterministic MVP label before optional training noise."""
    settings = config or HeatRiskConfig()
    wbgt_score = (
        0
        if wbgt < 21
        else 10
        if wbgt < 23
        else 20
        if wbgt < 25
        else 35
        if wbgt < 28
        else 50
    )
    base_score = sum(
        (
            wbgt_score,
            _band_score(
                continuous_exposure_minutes,
                ((30, 8), (60, 17), (90, 25)),
            ),
            _band_score(next_travel_minutes, ((10, 3), (20, 7), (30, 10))),
            _band_score(time_since_rest_minutes, ((30, 3), (60, 7), (90, 10))),
            _band_score(cooling_spot_distance_m, ((300, 2), (500, 3), (1000, 5))),
        )
    )
    if add_noise:
        if rng is None:
            rng = np.random.default_rng(settings.seed)
        score = base_score + float(rng.normal(0, settings.noise_std))
        # Keep noise from turning a high-risk rule label into an implausibly
        # low training target. This is still synthetic data, not a clinical rule.
        score = max(score, base_score - settings.max_downward_noise)
    else:
        score = base_score
    return round(float(np.clip(score, 0, 100)), 2)


def get_risk_level(score: float) -> str:
    if score < 30:
        return "LOW"
    if score < 50:
        return "CAUTION"
    if score < 70:
        return "REST_RECOMMENDED"
    if score < 85:
        return "REST_REQUIRED"
    return "IMMEDIATE_REST"


def generate_synthetic_data(config: HeatRiskConfig | None = None) -> pd.DataFrame:
    """Generate reproducible, non-uniform synthetic work situations."""
    settings = config or HeatRiskConfig()
    rng = np.random.default_rng(settings.seed)
    count = settings.sample_count
    # Beta distributions concentrate values around ordinary working conditions
    # while retaining enough tail cases for dangerous scenarios.
    wbgt = np.clip(15 + rng.beta(2.2, 2.0, count) * 20, 15, 35)
    exposure = np.clip(rng.beta(2.0, 3.0, count) * 180, 0, 180)
    next_travel = np.clip(rng.beta(2.0, 3.0, count) * 60, 0, 60)
    since_rest = np.clip(rng.beta(2.0, 2.5, count) * 180, 0, 180)
    cooling_distance = np.clip(rng.beta(1.5, 3.0, count) * 3000, 0, 3000)

    frame = pd.DataFrame(
        {
            "wbgt": np.round(wbgt, 2),
            "continuous_exposure_minutes": np.round(exposure, 2),
            "next_travel_minutes": np.round(next_travel, 2),
            "time_since_rest_minutes": np.round(since_rest, 2),
            "cooling_spot_distance_m": np.round(cooling_distance, 2),
        }
    )
    frame[TARGET] = [
        calculate_initial_risk_score(
            wbgt=row.wbgt,
            continuous_exposure_minutes=row.continuous_exposure_minutes,
            next_travel_minutes=row.next_travel_minutes,
            time_since_rest_minutes=row.time_since_rest_minutes,
            cooling_spot_distance_m=row.cooling_spot_distance_m,
            add_noise=settings.add_noise,
            rng=rng,
            config=settings,
        )
        for row in frame.itertuples()
    ]
    frame["risk_level"] = frame[TARGET].map(get_risk_level)
    return frame


def _metrics(model: Any, features: pd.DataFrame, target: pd.Series) -> dict[str, float]:
    predicted = np.clip(model.predict(features), 0, 100)
    return {
        "mae": round(float(mean_absolute_error(target, predicted)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(target, predicted))), 4),
        "r2": round(float(r2_score(target, predicted)), 4),
    }


def train_model(
    frame: pd.DataFrame,
    *,
    seed: int = DEFAULT_SEED,
    train_fraction: float = 0.8,
) -> tuple[Any, dict[str, Any]]:
    """Train XGBRegressor and return the model plus train/test report."""
    from xgboost import XGBRegressor

    if not 0.5 <= train_fraction < 1:
        raise ValueError("train_fraction must be between 0.5 and 1")
    x_train, x_test, y_train, y_test = train_test_split(
        frame[FEATURES], frame[TARGET], test_size=1 - train_fraction, random_state=seed
    )
    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=seed,
        n_jobs=2,
    )
    model.fit(x_train, y_train)
    report = {
        "model": "XGBRegressor",
        "features": FEATURES,
        "target": TARGET,
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "train": _metrics(model, x_train, y_train),
        "test": _metrics(model, x_test, y_test),
        "feature_importance": {
            feature: round(float(importance), 6)
            for feature, importance in zip(FEATURES, model.feature_importances_)
        },
        "trained_at": datetime.now(UTC).isoformat(),
        "synthetic_mvp_label_note": (
            "Labels use an MVP 50/25/10/10/5 rule informed by heat-stress guidance; "
            "they are not an official NIOSH/OSHA 0-100 score."
        ),
    }
    return model, report


def save_model_artifacts(model: Any, report: dict[str, Any], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    # Save the underlying booster to avoid sklearn-wrapper compatibility
    # differences between XGBoost and newer scikit-learn releases.
    model.get_booster().save_model(str(directory / "heat_risk_model.json"))
    (directory / "heat_risk_metadata.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_model(path: Path) -> Any:
    from xgboost import XGBRegressor

    model = XGBRegressor()
    model.load_model(path)
    return model


def predict_heat_risk(
    *,
    model: Any,
    wbgt: float,
    continuous_exposure_minutes: float,
    next_travel_minutes: float,
    time_since_rest_minutes: float,
    cooling_spot_distance_m: float,
) -> dict[str, Any]:
    """Predict only heat risk; route and shelter selection remain separate."""
    features = pd.DataFrame(
        [
            {
                "wbgt": wbgt,
                "continuous_exposure_minutes": continuous_exposure_minutes,
                "next_travel_minutes": next_travel_minutes,
                "time_since_rest_minutes": time_since_rest_minutes,
                "cooling_spot_distance_m": cooling_spot_distance_m,
            }
        ],
        columns=FEATURES,
    )
    score = float(np.clip(model.predict(features)[0], 0, 100))
    return {"heat_risk_score": round(score, 2), "risk_level": get_risk_level(score)}


def example_scenarios(model: Any) -> list[dict[str, Any]]:
    """Return five comparison scenarios for manual model verification."""
    scenarios = [
        ("cool_short", 18, 10, 5, 10, 100),
        ("moderate_long_exposure", 24, 120, 23, 80, 350),
        ("hot_near_shelter", 30, 45, 10, 40, 100),
        ("hot_long_exposure", 30, 120, 35, 120, 1200),
        ("extreme", 35, 180, 60, 180, 3000),
    ]
    rows = []
    for name, wbgt, exposure, travel, rest, distance in scenarios:
        rule_score = calculate_initial_risk_score(
            wbgt=wbgt,
            continuous_exposure_minutes=exposure,
            next_travel_minutes=travel,
            time_since_rest_minutes=rest,
            cooling_spot_distance_m=distance,
        )
        rows.append(
            {
                "scenario": name,
                "input": {
                    "wbgt": wbgt,
                    "continuous_exposure_minutes": exposure,
                    "next_travel_minutes": travel,
                    "time_since_rest_minutes": rest,
                    "cooling_spot_distance_m": distance,
                },
                "rule_score": rule_score,
                "ai_prediction": predict_heat_risk(
                    model=model,
                    wbgt=wbgt,
                    continuous_exposure_minutes=exposure,
                    next_travel_minutes=travel,
                    time_since_rest_minutes=rest,
                    cooling_spot_distance_m=distance,
                ),
            }
        )
    return rows
