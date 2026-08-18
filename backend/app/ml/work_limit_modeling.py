from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)

from app.ml.risk_modeling import (
    FEATURE_NAMES,
    RiskDataset,
    _build_model,
    _default_model_parameters,
    chronological_group_split,
    moderate_work_limit_minutes,
)

WORK_LIMIT_LABELS = (
    "WORK_60",
    "WORK_45",
    "WORK_30",
    "WORK_15",
    "REST_REQUIRED",
)
WEATHER_FEATURE_NAMES = FEATURE_NAMES[:5]
WORK_LIMIT_LABEL_POLICY_VERSION = "wbgt-osha-moderate-work-limit-1"


@dataclass(frozen=True)
class WorkLimitComparison:
    report: dict[str, Any]
    best_model_name: str
    best_model: Any


def work_limit_label(estimated_wbgt: float) -> str:
    limit = moderate_work_limit_minutes(estimated_wbgt)
    if limit is None:
        return "WORK_60"
    if limit == 45:
        return "WORK_45"
    if limit == 30:
        return "WORK_30"
    if limit == 15:
        return "WORK_15"
    return "REST_REQUIRED"


def compare_work_limit_models(
    dataset: RiskDataset,
    *,
    train_fraction: float = 0.8,
    seed: int = 20260818,
) -> WorkLimitComparison:
    train_indices, test_indices, cutoff = chronological_group_split(
        dataset.weather_at,
        train_fraction=train_fraction,
    )
    labels = np.array([work_limit_label(value) for value in dataset.estimated_wbgt])
    feature_indices = np.arange(len(WEATHER_FEATURE_NAMES))
    x_train = dataset.features[train_indices][:, feature_indices]
    x_test = dataset.features[test_indices][:, feature_indices]
    y_train = labels[train_indices]
    y_test = labels[test_indices]

    models: dict[str, Any] = {}
    predictions: dict[str, np.ndarray] = {}
    for name, parameters in _default_model_parameters().items():
        model = _build_model(name, parameters, seed)
        model.fit(x_train, y_train)
        models[name] = model
        predictions[name] = model.predict(x_test)

    metrics = {
        name: _metrics(y_test, prediction)
        for name, prediction in predictions.items()
    }
    best_name = max(
        models,
        key=lambda name: (
            metrics[name]["macro_f1"],
            metrics[name]["rest_required_recall"],
        ),
    )
    report = {
        "label_policy_version": WORK_LIMIT_LABEL_POLICY_VERSION,
        "feature_names": list(WEATHER_FEATURE_NAMES),
        "selection_metric": "macro_f1, then REST_REQUIRED recall",
        "best_model": best_name,
        "split": {
            "strategy": "chronological weather-time group split",
            "cutoff": cutoff.isoformat(),
            "train_rows": int(len(train_indices)),
            "test_rows": int(len(test_indices)),
        },
        "dataset": {
            "source": dataset.source,
            "rows": int(len(labels)),
            "label_distribution": dict(sorted(Counter(labels).items())),
            "limitation": (
                "Labels are generated from WBGT and the configured work/rest table; "
                "they are not observed heat-illness outcomes."
            ),
        },
        "models": metrics,
    }
    return WorkLimitComparison(report, best_name, models[best_name])


def save_work_limit_artifacts(
    comparison: WorkLimitComparison,
    artifact_directory: Path,
) -> None:
    artifact_directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "artifact_format_version": 1,
            "model": comparison.best_model,
            "model_name": comparison.best_model_name,
            "feature_names": WEATHER_FEATURE_NAMES,
            "risk_labels": WORK_LIMIT_LABELS,
            "label_policy_version": WORK_LIMIT_LABEL_POLICY_VERSION,
            "training_data_source": comparison.report["dataset"]["source"],
        },
        artifact_directory / "work_limit_classifier.joblib",
    )
    with (artifact_directory / "work_limit_comparison.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(comparison.report, file, ensure_ascii=False, indent=2)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    report = classification_report(
        y_true,
        y_pred,
        labels=WORK_LIMIT_LABELS,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 6),
        "macro_f1": round(
            float(f1_score(y_true, y_pred, labels=WORK_LIMIT_LABELS, average="macro")),
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
            y_true, y_pred, labels=WORK_LIMIT_LABELS
        ).tolist(),
        "per_class": {
            label: {
                key: round(float(report[label][key]), 6)
                for key in ("precision", "recall", "f1-score")
            }
            for label in WORK_LIMIT_LABELS
        },
    }
