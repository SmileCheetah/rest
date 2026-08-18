"""규칙 기반, Ridge, GAM 폭염 위험도 비교 실험.

실제 의료 판단용 모델이 아니라 합성 데이터 기반 PoC입니다.
실행: python compare_models.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             mean_absolute_error, mean_squared_error, r2_score,
                             recall_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from pygam import LinearGAM, s
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pygam이 필요합니다. pip install -r requirements.txt") from exc

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "comparison-output"
FEATURES = ["temperature", "humidity", "wind_speed", "solar_radiation", "wbgt",
            "travel_time_min", "travel_distance_km", "walking_speed_kmh", "hour"]


def make_data(n=10_000, seed=42):
    rng = np.random.default_rng(seed)
    hour = rng.uniform(8, 19, n)
    temperature = np.clip(rng.normal(32, 3.5, n), 25, 40)
    humidity = rng.uniform(30, 90, n)
    solar = np.clip(900 * np.exp(-((hour - 14) / 4) ** 2) + rng.normal(0, 100, n), 0, 1000)
    wind = rng.uniform(0, 6, n)
    wbgt = np.clip(0.55 * temperature + 0.025 * humidity - 0.35 * wind + solar / 1800 + rng.normal(0, .7, n), 20, 35)
    distance = rng.uniform(.2, 5, n)
    speed = rng.uniform(2, 7, n)
    travel = np.clip(distance / speed * 60 + rng.normal(4, 5, n), 5, 60)
    frame = pd.DataFrame({
        "temperature": temperature, "humidity": humidity, "wind_speed": wind,
        "solar_radiation": solar, "wbgt": wbgt, "travel_time_min": travel,
        "travel_distance_km": distance, "walking_speed_kmh": speed, "hour": hour,
    })
    risk = (8 * np.maximum(wbgt - 24, 0) ** 1.35
            + 0.018 * np.maximum(humidity - 55, 0) ** 1.3
            + 0.018 * solar
            - 2.0 * wind
            + 0.018 * travel ** 1.55
            + 2.5 * np.maximum(speed - 4, 0)
            + 8 * np.exp(-((hour - 14.5) / 2.4) ** 2)
            + 0.035 * np.maximum(wbgt - 28, 0) * travel
            + rng.normal(0, 3, n))
    return frame, np.clip(risk, 0, 100)


def rule_based(x):
    score = (np.select([x.wbgt < 25, x.wbgt < 28, x.wbgt < 31], [10, 25, 45], 65)
             + np.select([x.travel_time_min <= 15, x.travel_time_min <= 30, x.travel_time_min <= 45], [0, 10, 20], 30)
             + np.select([x.solar_radiation < 400, x.solar_radiation < 750], [0, 8], 15)
             + np.select([x.hour < 12, x.hour < 16], [0, 8], 12)
             - np.minimum(x.wind_speed * 1.5, 8))
    return np.clip(score, 0, 100)


def labels(values, low, high):
    return np.where(values >= high, "HIGH", np.where(values >= low, "MEDIUM", "LOW"))


def main():
    OUT.mkdir(exist_ok=True)
    x, y = make_data()
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=.2, random_state=42)
    low, high = np.percentile(y_train, [33, 66])
    additive_terms = s(0, n_splines=10)
    for i in range(1, len(FEATURES)):
        additive_terms += s(i, n_splines=10)
    models = {
        "Rule": None,
        "Ridge": make_pipeline(StandardScaler(), Ridge(alpha=10)),
        "GAM": LinearGAM(additive_terms, max_iter=300),
        "GAM Interaction": LinearGAM(additive_terms + s(4, by=5, n_splines=8), max_iter=300),
    }
    predictions = {}
    rows = []
    for name, model in models.items():
        if name == "Rule": pred = rule_based(x_test)
        else:
            model.fit(x_train, y_train)
            pred = np.clip(model.predict(x_test), 0, 100)
        predictions[name] = pred
        actual_l, pred_l = labels(y_test, low, high), labels(pred, low, high)
        cm = confusion_matrix(actual_l, pred_l, labels=["LOW", "MEDIUM", "HIGH"])
        rows.append({"model": name, "MAE": mean_absolute_error(y_test, pred), "RMSE": mean_squared_error(y_test, pred) ** .5,
                     "R2": r2_score(y_test, pred), "Accuracy": accuracy_score(actual_l, pred_l),
                     "Macro_F1": f1_score(actual_l, pred_l, average="macro"),
                     "HIGH_Recall": recall_score(actual_l, pred_l, labels=["HIGH"], average="macro", zero_division=0),
                     "HIGH_to_MEDIUM": int(cm[2, 1]), "HIGH_to_LOW": int(cm[2, 0])})
    result = pd.DataFrame(rows).round(3)
    result.to_csv(OUT / "overall_metrics.csv", index=False)
    print("=== 모델 비교 결과 ===")
    print(result.to_string(index=False))
    print(f"라벨 기준: LOW < {low:.1f}, MEDIUM < {high:.1f}, HIGH >= {high:.1f}")
    print(f"결과 저장: {OUT}")

    # GAM 주요 효과 그래프
    gam = models["GAM"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, idx in zip(axes.flat, [4, 5, 3, 2]):
        grid = gam.generate_X_grid(term=idx)
        ax.plot(grid[:, idx], gam.predict(grid), color="#1766e8")
        ax.set_title(FEATURES[idx]); ax.set_ylabel("예상 위험점수"); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(OUT / "gam-effects.png", dpi=140); plt.close(fig)


if __name__ == "__main__":
    main()
