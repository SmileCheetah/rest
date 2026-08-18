# SVR 폭염 위험도 실험

실제 학습 데이터가 준비되기 전, 합성 데이터로 SVR(Support Vector Regression)이 폭염 위험점수(0~100)를 예측하는지 확인하는 실험 폴더입니다.

## 실행

```bash
cd ai-test
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python svr_risk_test.py
```

이 실험은 실제 의료·안전 판단 모델이 아닙니다. 합성 규칙으로 만든 예시 데이터이며, 실제 모델을 만들 때는 검증된 폭염·WBGT·노출시간 데이터로 교체해야 합니다.

## 입력값

- 체감온도(°C)
- 습도(%)
- 연속 야외 노출시간(분)
- 예상 도보시간(분)
- 폭염특보 여부(0/1)

출력 점수는 0~100으로 제한하고, 예시 화면을 위해 `SAFE`, `CAUTION`, `REST_REQUIRED` 3단계로 변환합니다.

실행하면 `output/svr-risk-graphs.png`에 변수별 그래프와 폭염특보 비교 그래프가 생성됩니다.
