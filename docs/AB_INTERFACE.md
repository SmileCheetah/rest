# A ↔ B 분석 인터페이스

> A와 B가 독립적으로 개발할 때 사용하는 데이터 계약이다. 지도 거리·시간 계산은 A, 위험판단과 추천 선정은 B가 책임진다.

## 1. 책임 경계

### A가 준비하는 값

- 업무, 일정, 이동구간 ID
- 출발지와 목적지 좌표
- 이동거리와 예상 도보시간
- 출발·도착 예정 시각
- 기온, 습도, 체감온도
- 지도 API가 계산한 쿨링스팟별 이탈거리와 추가시간

### B가 계산하는 값

- 현재 및 이동 후 예상 연속 야외노출시간
- 0~100 위험점수
- `SAFE`, `CAUTION`, `REST_REQUIRED` 위험 단계
- 휴식 필요 여부와 추천 휴식 횟수
- 판단 근거 코드
- 조건을 만족하는 최적 쿨링스팟 1곳

## 2. 위험판단 입력

Mock: `docs/mocks/risk-assessment-request.json`

```json
{
  "workSessionId": 1,
  "scheduleId": 2,
  "routeSegmentId": 2,
  "routeOptionId": 2,
  "distanceMeters": 1200,
  "walkingMinutes": 18,
  "departureTime": "2026-08-18T13:30:00+09:00",
  "estimatedArrivalTime": "2026-08-18T13:48:00+09:00",
  "temperature": 34.5,
  "humidity": 68.0,
  "apparentTemperature": 38.2,
  "currentContinuousExposureMinutes": 25,
  "plannedVisitMinutes": 40
}
```

`currentContinuousExposureMinutes`는 B의 노출시간 계산 함수가 먼저 계산한 값을 사용한다. HTTP API로 통합할 때는 B의 노출시간 계산과 위험판단을 한 Service 안에서 연결해도 된다.

## 3. 위험판단 출력

Mock: `docs/mocks/risk-assessment-response.json`

```json
{
  "routeOptionId": 2,
  "currentContinuousExposureMinutes": 25,
  "expectedContinuousExposureMinutes": 43,
  "riskScore": 82.0,
  "riskLevel": "REST_REQUIRED",
  "restRequired": true,
  "recommendedRestCount": 1,
  "reasonCodes": [
    "HIGH_APPARENT_TEMPERATURE",
    "LONG_CONTINUOUS_EXPOSURE"
  ],
  "modelVersion": "mvp-v1"
}
```

## 4. 쿨링스팟 추천 입력

Mock: `docs/mocks/cooling-recommendation-request.json`

A가 지도 API로 후보별 이동 값을 계산한 뒤 B에게 전달한다.

후보 필드:

- `coolingSpotId`: 쿨링스팟 ID
- `isOpen`: 방문 예정 시각에 운영 중인지
- `detourDistanceMeters`: 기존 경로에서 벗어나는 거리
- `additionalMinutes`: 일반경로보다 추가되는 시간
- `minutesToCoolingSpot`: 쿨링스팟까지 도보시간
- `facilities`: 편의시설 목록

## 5. 쿨링스팟 추천 출력

Mock: `docs/mocks/cooling-recommendation-response.json`

```json
{
  "routeSegmentId": 2,
  "recommendedCoolingSpot": {
    "coolingSpotId": 3,
    "reason": "추가시간이 2분 이내이고 편의시설이 더 많음"
  }
}
```

조건을 만족하는 곳이 없으면 `recommendedCoolingSpot`은 `null`이다.

## 6. 추천 규칙

1. 운영시간을 만족해야 한다.
2. 방문 예정시각에 5분 버퍼를 적용한다.
3. 경로 이탈거리 기준을 만족해야 한다.
4. 추가 이동시간 기준을 만족해야 한다.
5. 모든 조건은 AND로 적용한다.
6. 조건을 만족하는 후보 중 추가 이동시간이 가장 짧은 1곳을 선택한다.
7. 추가 이동시간 차이가 2분 이내면 편의시설이 많은 곳을 선택한다.

지도 API 호출과 실제 거리 계산은 A가 담당하며 B는 전달된 계산값만 사용한다.

## 7. 변경 규칙

- 필드 이름이나 타입을 바꾸기 전에 A/B가 먼저 합의한다.
- 계약 변경 시 이 문서와 관련 mock JSON을 함께 수정한다.
- Backend 구현 전에도 B는 mock JSON으로 순수 Python 함수와 테스트를 작성할 수 있다.
