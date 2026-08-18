"""Train and evaluate the three-class rest-status XGBoost classifier."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.heat_risk import HeatRiskConfig
from app.ml.rest_status_classifier import (
    generate_rest_status_data,
    predict_rest_status,
    save_classifier_artifacts,
    train_rest_status_classifier,
)


DATA_PATH = BACKEND_DIR / "data" / "synthetic_rest_status.csv"
ARTIFACT_DIR = BACKEND_DIR / "artifacts" / "rest-status-model"


def main() -> None:
    config = HeatRiskConfig()
    frame = generate_rest_status_data(config)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(DATA_PATH, index=False)
    model, report = train_rest_status_classifier(frame, seed=config.seed)
    save_classifier_artifacts(model, report, ARTIFACT_DIR)
    example = predict_rest_status(
        model=model,
        wbgt=27,
        continuous_exposure_minutes=72,
        next_travel_minutes=23,
        time_since_rest_minutes=80,
        cooling_spot_distance_m=350,
    )
    (ARTIFACT_DIR / "example_prediction.json").write_text(
        json.dumps(example, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"data: {DATA_PATH} ({len(frame)} rows)")
    print(json.dumps({"train": report["train"], "test": report["test"]}, indent=2))
    print(json.dumps(report["class_distribution"], ensure_ascii=False, indent=2))
    print(json.dumps(example, ensure_ascii=False, indent=2))
    print(f"model: {ARTIFACT_DIR / 'rest_status_classifier.json'}")


if __name__ == "__main__":
    main()
