"""Three-class rest-status classifier trained from MVP synthetic labels.

The labels and 50/25/10/10/5 weighting are an internal MVP policy, not an
official NIOSH or OSHA classification. The classifier predicts rest status;
route and Cooling Spot selection remain outside this module.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

from app.ml.heat_risk import (
    FEATURES,
    TARGET,
    HeatRiskConfig,
    generate_synthetic_data,
)

STATUS_LABELS = (
    "MOVABLE",
    "REST_RECOMMENDED",
    "REST_BEFORE_NEXT_VISIT",
)
STATUS_MAX = {
    "MOVABLE": 39,
    "REST_RECOMMENDED": 69,
}


def assign_rest_status(score: float) -> str:
    """Map an MVP risk score to one of three operational statuses."""
    if score <= STATUS_MAX["MOVABLE"]:
        return "MOVABLE"
    if score <= STATUS_MAX["REST_RECOMMENDED"]:
        return "REST_RECOMMENDED"
    return "REST_BEFORE_NEXT_VISIT"


def generate_rest_status_data(config: HeatRiskConfig | None = None) -> pd.DataFrame:
    """Generate features, internal score labels, and three-class targets."""
    frame = generate_synthetic_data(config)
    frame["rest_status"] = frame[TARGET].map(assign_rest_status)
    return frame


def train_rest_status_classifier(
    frame: pd.DataFrame,
    *,
    seed: int = 42,
    test_fraction: float = 0.2,
) -> tuple[Any, dict[str, Any]]:
    """Train a stratified XGBClassifier and return evaluation metadata."""
    from xgboost import XGBClassifier

    x_train, x_test, y_train, y_test = train_test_split(
        frame[FEATURES],
        frame["rest_status"].map({label: i for i, label in enumerate(STATUS_LABELS)}),
        test_size=test_fraction,
        random_state=seed,
        stratify=frame["rest_status"],
    )
    model = XGBClassifier(
        objective="multi:softprob",
        num_class=len(STATUS_LABELS),
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="mlogloss",
        random_state=seed,
        n_jobs=2,
    )
    model.fit(x_train, y_train)
    train_prediction = model.predict(x_train)
    test_prediction = model.predict(x_test)
    report = {
        "model": "XGBClassifier",
        "features": FEATURES,
        "target": "rest_status",
        "classes": list(STATUS_LABELS),
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "class_distribution": frame["rest_status"].value_counts().to_dict(),
        "train": _classification_metrics(y_train, train_prediction),
        "test": _classification_metrics(y_test, test_prediction),
        "confusion_matrix": confusion_matrix(
            y_test, test_prediction, labels=range(len(STATUS_LABELS))
        ).tolist(),
        "feature_importance": {
            feature: round(float(value), 6)
            for feature, value in zip(FEATURES, model.feature_importances_)
        },
        "trained_at": datetime.now(UTC).isoformat(),
        "mvp_label_note": (
            "The 50/25/10/10/5 score weights and 0-39/40-69/70-100 thresholds "
            "are synthetic MVP policy values, not official NIOSH/OSHA outputs."
        ),
    }
    return model, report


def _classification_metrics(actual: Any, predicted: Any) -> dict[str, Any]:
    return {
        "accuracy": round(float(accuracy_score(actual, predicted)), 4),
        "macro_f1": round(float(f1_score(actual, predicted, average="macro")), 4),
        "classification_report": classification_report(
            actual,
            predicted,
            labels=range(len(STATUS_LABELS)),
            target_names=list(STATUS_LABELS),
            output_dict=True,
            zero_division=0,
        ),
    }


def save_classifier_artifacts(model: Any, report: dict[str, Any], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    model.get_booster().save_model(str(directory / "rest_status_classifier.json"))
    (directory / "rest_status_metadata.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_rest_status_classifier(path: Path) -> Any:
    from xgboost import XGBClassifier

    model = XGBClassifier()
    model.load_model(path)
    return model


def predict_rest_status(
    *,
    model: Any,
    wbgt: float,
    continuous_exposure_minutes: float,
    next_travel_minutes: float,
    time_since_rest_minutes: float,
    cooling_spot_distance_m: float,
) -> dict[str, Any]:
    """Return class probabilities and the highest-probability status."""
    features = pd.DataFrame(
        [
            [
                wbgt,
                continuous_exposure_minutes,
                next_travel_minutes,
                time_since_rest_minutes,
                cooling_spot_distance_m,
            ]
        ],
        columns=FEATURES,
    )
    raw_probabilities = model.predict_proba(features)[0]
    probability_map = {
        label: round(float(raw_probabilities[index]), 4)
        for index, label in enumerate(STATUS_LABELS)
    }
    # 표시용 반올림 값이 아니라 모델의 원본 확률로 최종 클래스를 고릅니다.
    # 경계에 아주 가까운 두 확률이 같은 값으로 반올림되는 경우에도 결과가
    # 클래스 선언 순서에 의해 바뀌지 않게 합니다.
    prediction = STATUS_LABELS[int(np.argmax(raw_probabilities))]
    return {"probabilities": probability_map, "decision": prediction}
