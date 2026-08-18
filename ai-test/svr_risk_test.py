"""합성 데이터로 SVR 폭염 위험점수를 시험하는 독립 실행 예제."""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
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
    heat_alert = rng.integers(0, 2, size)
    # 실제 기준이 아니라, 위험도가 올라가는 방향을 보여주기 위한 임시 라벨입니다.
    risk = (
        (apparent - 24) * 3.2
        + np.maximum(humidity - 60, 0) * 0.25
        + exposure * 0.28
        + walking * 0.18
        + heat_alert * 15
        + rng.normal(0, 3, size)
    )
    return np.column_stack([apparent, humidity, exposure, walking, heat_alert]), np.clip(risk, 0, 100)


def risk_label(score: float) -> str:
    if score >= 66:
        return "REST_REQUIRED"
    if score >= 33:
        return "CAUTION"
    return "SAFE"


def save_graphs(model) -> Path:
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)
    base = np.array([32, 70, 30, 20, 0], dtype=float)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    variables = [("야외노출 시간(분)", 2, np.arange(0, 151, 5)), ("체감온도(°C)", 0, np.arange(24, 43)), ("습도(%)", 1, np.arange(35, 96, 2))]
    for axis, (title, column, values) in zip(axes.flat, variables):
        samples = np.repeat(base[None, :], len(values), axis=0)
        samples[:, column] = values
        scores = np.clip(model.predict(samples), 0, 100)
        axis.plot(values, scores, color="#1766e8", linewidth=2.5)
        axis.axhline(33, color="#d9a900", linestyle="--", linewidth=1)
        axis.axhline(66, color="#d52241", linestyle="--", linewidth=1)
        axis.set_title(title)
        axis.set_ylim(0, 100)
        axis.set_ylabel("위험점수")
        axis.grid(alpha=0.25)
    alert_samples = np.array([[32, 70, 30, 20, 0], [32, 70, 30, 20, 1]], dtype=float)
    alert_scores = np.clip(model.predict(alert_samples), 0, 100)
    axes.flat[3].bar(["특보 없음", "폭염특보"], alert_scores, color=["#18a994", "#d52241"])
    axes.flat[3].set_title("폭염특보 영향")
    axes.flat[3].set_ylim(0, 100)
    axes.flat[3].set_ylabel("위험점수")
    for index, score in enumerate(alert_scores):
        axes.flat[3].text(index, score + 2, f"{score:.1f}", ha="center")
    fig.tight_layout()
    output_path = output_dir / "svr-risk-graphs.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


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

    examples = [
        ("선선한 오전", [27, 55, 10, 10, 0]),
        ("습하고 긴 이동", [32, 75, 55, 25, 0]),
        ("폭염특보·장시간 노출", [38, 85, 110, 40, 1]),
        ("높은 체감온도지만 특보 없음", [35, 70, 20, 15, 0]),
    ]
    for name, values in examples:
        score = float(np.clip(model.predict([values])[0], 0, 100))
        print(
            f"{name}: 체감온도 {values[0]:.0f}°C / 습도 {values[1]:.0f}% / "
            f"노출 {values[2]:.0f}분 / 도보 {values[3]:.0f}분 / "
            f"폭염특보 {'있음' if values[4] else '없음'} "
            f"→ 위험점수 {score:.1f}, {risk_label(score)}"
        )
    output_path = save_graphs(model)
    print(f"그래프 저장: {output_path}")


if __name__ == "__main__":
    main()
