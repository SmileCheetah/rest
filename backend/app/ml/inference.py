from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

import joblib
import numpy as np

from app.schemas.risk_analysis import RiskLevel


SUPPORTED_RISK_LABELS = {
    "MOVE_POSSIBLE",
    "REST_RECOMMENDED",
    "REST_REQUIRED",
}
SUPPORTED_WORK_LIMIT_LABELS = {
    "WORK_60",
    "WORK_45",
    "WORK_30",
    "WORK_15",
    "REST_REQUIRED",
}


class RiskModelArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelPrediction:
    risk_level: RiskLevel
    model_version: str


@dataclass(frozen=True)
class WorkLimitPrediction:
    work_limit_label: str
    model_version: str


def predict_risk(
    feature_values: Mapping[str, float | int | None],
    model_path: Path | None,
) -> ModelPrediction | None:
    """Predict when a compatible artifact and all of its inputs are available."""
    if model_path is None or not model_path.is_file():
        return None

    resolved_path = model_path.resolve()
    artifact = _load_artifact(str(resolved_path), resolved_path.stat().st_mtime_ns)
    feature_names = artifact["feature_names"]
    if any(feature_values.get(name) is None for name in feature_names):
        return None

    row = np.array(
        [[float(feature_values[name]) for name in feature_names]],
        dtype=float,
    )
    if not np.isfinite(row).all():
        return None

    try:
        predicted = str(artifact["model"].predict(row)[0])
    except Exception as exc:
        raise RiskModelArtifactError("risk model prediction failed") from exc
    if predicted not in SUPPORTED_RISK_LABELS:
        raise RiskModelArtifactError(f"model returned unsupported label {predicted!r}")
    return ModelPrediction(
        risk_level=predicted,  # type: ignore[arg-type]
        model_version=(
            f"{artifact['model_name']}:{artifact['label_policy_version']}"
        ),
    )


def predict_work_limit(
    feature_values: Mapping[str, float | int | None],
    model_path: Path | None,
) -> WorkLimitPrediction | None:
    """Predict the permitted work interval from weather-only features."""
    if model_path is None or not model_path.is_file():
        return None

    resolved_path = model_path.resolve()
    artifact = _load_artifact(str(resolved_path), resolved_path.stat().st_mtime_ns)
    feature_names = artifact["feature_names"]
    if any(feature_values.get(name) is None for name in feature_names):
        return None
    row = np.array(
        [[float(feature_values[name]) for name in feature_names]],
        dtype=float,
    )
    if not np.isfinite(row).all():
        return None
    try:
        predicted = str(artifact["model"].predict(row)[0])
    except Exception as exc:
        raise RiskModelArtifactError("work limit model prediction failed") from exc
    if predicted not in SUPPORTED_WORK_LIMIT_LABELS:
        raise RiskModelArtifactError(
            f"work limit model returned unsupported label {predicted!r}"
        )
    return WorkLimitPrediction(
        work_limit_label=predicted,
        model_version=f"{artifact['model_name']}:{artifact['label_policy_version']}",
    )


@lru_cache(maxsize=4)
def _load_artifact(path: str, modified_at_ns: int) -> dict[str, object]:
    del modified_at_ns
    try:
        payload = joblib.load(path)
    except Exception as exc:
        raise RiskModelArtifactError("risk model artifact could not be loaded") from exc
    if not isinstance(payload, dict):
        raise RiskModelArtifactError("risk model artifact must be a dictionary")

    required_keys = {
        "artifact_format_version",
        "model",
        "model_name",
        "feature_names",
        "risk_labels",
        "label_policy_version",
        "training_data_source",
    }
    missing = required_keys.difference(payload)
    if missing:
        raise RiskModelArtifactError(
            f"risk model artifact is missing keys: {sorted(missing)}"
        )
    if payload["artifact_format_version"] != 1:
        raise RiskModelArtifactError("unsupported risk model artifact format")
    if not hasattr(payload["model"], "predict"):
        raise RiskModelArtifactError("risk model artifact has no predictor")

    feature_names = payload["feature_names"]
    if not isinstance(feature_names, (list, tuple)) or not feature_names:
        raise RiskModelArtifactError("risk model feature_names must be non-empty")
    if not all(isinstance(name, str) for name in feature_names):
        raise RiskModelArtifactError("risk model feature_names must be strings")
    return payload
