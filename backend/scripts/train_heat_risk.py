"""Generate synthetic Heat Risk data, train XGBoost, and save artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.heat_risk import (
    HeatRiskConfig,
    example_scenarios,
    generate_synthetic_data,
    save_model_artifacts,
    train_model,
)

DATA_PATH = BACKEND_DIR / "data" / "synthetic_heat_risk.csv"
ARTIFACT_DIR = BACKEND_DIR / "artifacts" / "heat-risk-model"


def main() -> None:
    config = HeatRiskConfig()
    frame = generate_synthetic_data(config)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(DATA_PATH, index=False)
    model, report = train_model(frame, seed=config.seed, train_fraction=config.train_fraction)
    save_model_artifacts(model, report, ARTIFACT_DIR)
    (ARTIFACT_DIR / "example_scenarios.json").write_text(
        json.dumps(example_scenarios(model), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"data: {DATA_PATH} ({len(frame)} rows)")
    print(json.dumps({"train": report["train"], "test": report["test"]}, indent=2))
    print(json.dumps(report["feature_importance"], indent=2))
    print(f"model: {ARTIFACT_DIR / 'heat_risk_model.json'}")


if __name__ == "__main__":
    main()
