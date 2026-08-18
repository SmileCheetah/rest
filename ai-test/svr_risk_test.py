"""합성 데이터로 SVR 폭염 위험점수를 시험하는 독립 실행 예제."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


def make_synthetic_data(size: int = 300, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """실제 데이터가 없을 때 사용할 교육용 합성 데이터입니다."""
    rng = np.random.default_rng(seed)
    apparent = rng.uniform(24, 42, size)
    humidity = rng.uniform(35, 95, size)
    exposure = rng.uniform(0, 150, size)
    walking = rng.uniform(0, 60, size)
    # 실제 기준이 아니라, 위험도가 올라가는 방향을 보여주기 위한 임시 라벨입니다.
    risk = (
        (apparent - 24) * 3.2
        + np.maximum(humidity - 60, 0) * 0.25
        + exposure * 0.28
        + walking * 0.18
        + rng.normal(0, 3, size)
    )
    return np.column_stack([apparent, humidity, exposure, walking]), np.clip(risk, 0, 100)


def risk_label(score: float) -> str:
    if score >= 66:
        return "REST_REQUIRED"
    if score >= 33:
        return "CAUTION"
    return "SAFE"


def main() -> None:
    features, labels = make_synthetic_data()
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42
    )
    model = make_pipeline(StandardScaler(), SVR(kernel="rbf", C=40, epsilon=2.0, gamma="scale"))
    model.fit(x_train, y_train)
    predictions = np.clip(model.predict(x_test), 0, 100)

    print("=== SVR 폭염 위험도 테스트 ===")
    print(f"학습 데이터: {len(x_train)}건 / 테스트 데이터: {len(x_test)}건")
    print(f"MAE(평균 오차): {mean_absolute_error(y_test, predictions):.2f}")
    print(f"R²(설명력): {r2_score(y_test, predictions):.2f}")

    examples = np.array([
        [27, 55, 10, 10],
        [32, 75, 55, 25],
        [38, 85, 110, 40],
    ])
    for values, score in zip(examples, model.predict(examples)):
        score = float(np.clip(score, 0, 100))
        print(
            f"체감온도 {values[0]:.0f}°C / 습도 {values[1]:.0f}% / "
            f"노출 {values[2]:.0f}분 / 도보 {values[3]:.0f}분 "
            f"→ 위험점수 {score:.1f}, {risk_label(score)}"
        )


if __name__ == "__main__":
    main()
