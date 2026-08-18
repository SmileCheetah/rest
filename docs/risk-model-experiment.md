# 위험 분류 모델 비교 실험

이 실험은 동일한 합성 라벨 데이터와 동일한 시간 분할에서 다음 세 분류기를 비교한다.

- 현재 규칙 분류기
- `RandomForestClassifier`
- `HistGradientBoostingClassifier`

## 라벨 생성

기상 입력으로 ECMWF `thermofeel`의 Liljegren WBGT 구현을 실행한다. 보통 걷기를 중간 강도 작업으로 가정하고, WBGT 구간별 작업 가능시간과 현재·예상 연속노출시간을 비교해 다음 라벨을 만든다.

- `MOVE_POSSIBLE`
- `REST_RECOMMENDED`
- `REST_REQUIRED`

WBGT 25℃ 미만은 보수적으로 연속노출 120분까지 허용하는 MVP 정책을 사용한다. 누적노출 120분 또는 240분 이상이고 휴식이 부족할 때 작업 가능시간을 각각 10분 또는 15분 줄이는 보정도 MVP 정책이다. 이 보정값은 NIOSH가 발표한 수치가 아니며 실제 지침 또는 실증 데이터가 확보되면 교체해야 한다.

합성 라벨은 정상 보행, 기본 작업복, 더위에 적응되지 않은 사용자를 보수적으로 가정한다. 개인 건강상태를 판단하지 않는다.

참고 기준:

- [ECMWF thermofeel Liljegren WBGT 구현](https://github.com/ecmwf/thermofeel)
- [NIOSH Occupational Exposure to Heat and Hot Environments](https://www.cdc.gov/niosh/docs/2016-106/default.html)
- [OSHA Technical Manual Table II:4-2](https://www.osha.gov/enforcement/directives/ted-115-ch-1)

## 데이터 분할과 평가

같은 기상시각에서 생성된 노출 시나리오가 학습과 테스트에 동시에 들어가지 않도록 기상시각 그룹을 기준으로 과거 80%와 최근 20%를 분리한다.

비교 지표는 accuracy, balanced accuracy, macro F1, `REST_REQUIRED` recall, confusion matrix다. 최적 ML 모델은 macro F1을 우선하고 동률이면 `REST_REQUIRED` recall로 선택한다.

기본 모델을 비교한 뒤 우수한 모델 계열만 학습 구간 내부의 시간순 검증 데이터로 파라미터를 조정한다. 이어서 전체 피처, 라벨에서 사용하지 않는 피처 제외, 중복 피처 제외 구성을 같은 검증 구간에서 비교한다. 최고 macro F1과 차이가 0.005 이내면 더 작은 피처 집합을 선택해 합성 데이터의 우연한 상관관계에 대한 과적합을 줄인다. 최종 테스트 데이터는 파라미터나 피처 선택에 사용하지 않는다. 최종 모델에는 permutation importance를 적용해 피처별 macro F1 기여도를 기록한다.

이 결과는 합성 라벨 생성 규칙을 얼마나 잘 재현하는지만 보여준다. 실제 열질환이나 건강 결과에 대한 정확도를 의미하지 않는다.

## 실행

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.ml.compare_risk_models
```

결과는 기본적으로 `backend/artifacts/risk-model/`에 저장되며 Git에는 포함되지 않는다.
