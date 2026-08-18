# 위험 분류 모델 비교 실험

이 실험은 동일한 합성 라벨 데이터와 동일한 시간 분할에서 다음 세 분류기를 비교한다.

- 현재 규칙 분류기
- `RandomForestClassifier`
- `HistGradientBoostingClassifier`

## 라벨 생성

기상 입력으로 ECMWF `thermofeel`의 Liljegren WBGT 구현을 오프라인에서만 실행한다. 보통 걷기를 중간 강도 작업으로 가정하고, OSHA Technical Manual Table II:4-2의 중간 강도 작업/휴식 구간과 현재·예상 연속노출시간을 비교해 다음 라벨을 만든다.

- `MOVE_POSSIBLE`
- `REST_RECOMMENDED`
- `REST_REQUIRED`

중간 강도 기준은 WBGT 26.7℃ 미만이면 이 표에 따른 휴식 제한을 적용하지 않고, 26.7/28.0/29.4/31.1℃ 구간에서 시간당 작업 가능시간을 각각 45/30/15/0분으로 변환한다. 현재 연속노출이 한계에 도달하면 `REST_REQUIRED`, 현재는 한계 전이지만 이동 후 예상 연속노출이 한계에 도달하면 `REST_RECOMMENDED`, 그 외에는 `MOVE_POSSIBLE`로 라벨링한다.

일 누적노출과 일 누적휴식은 활동 상태 기록에는 유지하지만 근거 있는 보정식을 확보하지 못했으므로 학습 피처와 라벨 생성에서 제외한다. 이 모델은 WBGT와 연속노출에 대한 합성 라벨을 재현하며 열질환을 진단하지 않는다.

OSHA 표는 건강하고 더위에 적응된 작업자가 가벼운 여름 작업복을 입고 수분과 염분을 충분히 섭취한다는 전제를 가진다. 현재 모델은 이 중간 강도 작업 기준을 일반 보행의 MVP 대리 기준으로 사용하므로, 실제 사용자 실증 데이터가 확보되면 라벨 경계를 다시 검증해야 한다. 개인 건강상태를 판단하지 않는다.

참고 기준:

- [ECMWF thermofeel Liljegren WBGT 구현](https://github.com/ecmwf/thermofeel)
- [NIOSH Occupational Exposure to Heat and Hot Environments](https://www.cdc.gov/niosh/docs/2016-106/default.html)
- [OSHA Technical Manual Table II:4-2](https://www.osha.gov/enforcement/directives/ted-115-ch-1)

## ERA5 입력

`app.ml.era5.load_era5_netcdf`는 ERA5 hourly single-level NetCDF의 한 격자점을 다음 단위로 변환한다.

- `t2m`: K → ℃
- `d2m`: `t2m`과 함께 상대습도(%) 산출
- `u10`, `v10`: 10m 풍속(m/s) 합성
- `sp`: Pa → hPa
- `ssrd`, `fdir`: 시간 누적 J/m² → W/m², 이후 `fdir / ssrd`로 직접일사 비율 산출
- 유효시각·위경도: 해당 1시간의 평균 태양천정각 코사인 산출

ERA5 hourly reanalysis의 `ssrd`와 `fdir`는 기본적으로 유효시각 직전 1시간 누적값이므로 3,600초로 나눈다. 다른 처리 주기의 파일은 `--accumulation-seconds`를 명시해야 한다.

학습 피처는 기온, 습도, 풍속, 일사량, 기압, 이동시간, 현재 연속노출시간, 이동 후 예상 연속노출시간이다. WBGT, 직접일사 비율, 태양천정각은 오프라인 정답 라벨 생성에만 쓰며 런타임 모델 입력에는 포함하지 않는다.

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

ERA5 NetCDF로 실행:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.ml.compare_risk_models `
  --era5-netcdf data/era5-seoul.nc `
  --latitude 37.5665 `
  --longitude 126.9780
```

결과는 기본적으로 `backend/artifacts/risk-model/`에 저장되며 Git에는 포함되지 않는다. 비교 보고서와 모델 아티팩트에는 `training_data_source`를 기록해 합성 기상 검증 모델과 ERA5 기반 모델을 구분한다.

API 요청에 `wind_speed`, `solar_radiation`, `surface_pressure`가 있고 모델 파일이 유효하면 저장 모델을 사용한다. 필요한 값이나 모델이 없으면 `rule-classifier-mvp-1` 규칙 분류기로 폴백하며, 응답의 `model_version`으로 실제 사용 경로를 확인할 수 있다. `joblib` 파일은 코드 실행 권한을 가질 수 있으므로 신뢰할 수 있는 학습 파이프라인에서 생성한 파일만 배포한다.
