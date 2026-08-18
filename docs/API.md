# 쉼표 MVP API 명세

> 구현된 기본 API의 Frontend 연동 기준이다. 실행 중인 최신 스키마는 FastAPI `/docs`를 우선 확인한다.

## 1. 공통 규칙

- 개발 Base URL: `http://localhost:8000`
- 요청·응답: JSON
- JSON 필드명: camelCase
- 날짜: `YYYY-MM-DD`
- 시간: `HH:MM:SS`
- 일시: ISO 8601, API 응답은 `Asia/Seoul` 오프셋 포함
- `404`: 요청한 데이터 없음
- `409`: 현재 상태 또는 중복 데이터 때문에 처리 불가
- `422`: 요청 형식 또는 값이 잘못됨
- `502`: 외부 API 호출 또는 응답 오류
- `503`: 필요한 환경변수 또는 서비스 연결 없음

## 2. 상태 확인

### `GET /health`

```json
{
  "status": "ok"
}
```

### `GET /health/db`

```json
{
  "status": "ok",
  "database": "connected"
}
```

## 3. 방문대상자

### `GET /visit-targets`

방문대상자 전체 목록을 반환한다.

### `GET /visit-targets/{visit_target_id}`

```json
{
  "visitTargetId": 1,
  "name": "김영희",
  "address": "서울특별시 종로구 창신동 데모 주소 1",
  "latitude": 37.57471,
  "longitude": 127.01142
}
```

없는 ID는 `404`를 반환한다.

## 4. 방문 일정

### 일정 응답

```json
{
  "scheduleId": 1,
  "workSessionId": 1,
  "scheduledTime": "09:00:00",
  "visitOrder": 1,
  "status": "PENDING",
  "plannedVisitMinutes": 40,
  "completedAt": null,
  "visitTarget": {
    "visitTargetId": 1,
    "name": "김영희",
    "address": "서울특별시 종로구 창신동 데모 주소 1",
    "latitude": 37.57471,
    "longitude": 127.01142
  }
}
```

### `GET /schedules/today`

한국 날짜 기준 오늘 일정을 방문 순서대로 반환한다.

### `GET /schedules/next`

```json
{
  "workSessionId": 1,
  "workCompleted": false,
  "nextSchedule": {
    "scheduleId": 1,
    "workSessionId": 1,
    "scheduledTime": "09:00:00",
    "visitOrder": 1,
    "status": "PENDING",
    "plannedVisitMinutes": 40,
    "completedAt": null,
    "visitTarget": {
      "visitTargetId": 1,
      "name": "김영희",
      "address": "서울특별시 종로구 창신동 데모 주소 1",
      "latitude": 37.57471,
      "longitude": 127.01142
    }
  }
}
```

남은 일정이 없으면 `workCompleted`는 `true`, `nextSchedule`은 `null`이다.

### `POST /schedules`

```json
{
  "visitTargetId": 5,
  "scheduleDate": "2026-08-18",
  "scheduledTime": "16:30:00",
  "visitOrder": 5,
  "plannedVisitMinutes": 30
}
```

- 성공: `201`, 생성된 일정 반환
- 방문대상자 없음: `404`
- 같은 업무의 방문 순서 중복: `409`
- 완료된 업무에 추가: `409`

### `PATCH /schedules/{schedule_id}`

필요한 필드만 보낸다.

```json
{
  "scheduledTime": "17:00:00",
  "plannedVisitMinutes": 45
}
```

수정 가능 필드:

- `scheduledTime`
- `visitOrder`
- `plannedVisitMinutes`

빈 요청은 `422`, 중복 방문 순서는 `409`를 반환한다.

### `DELETE /schedules/{schedule_id}`

- 성공: `204 No Content`
- 완료된 일정 또는 경로 데이터가 있는 일정: `409`
- 삭제 후 뒤의 방문 순서는 자동으로 1씩 당겨진다.

### `PATCH /schedules/{schedule_id}/complete`

- 업무가 `IN_PROGRESS`일 때만 방문 완료 가능
- 성공 시 상태가 `COMPLETED`로 변경되고 완료 시각을 반환
- `VISIT_COMPLETED` 활동 로그 생성
- 같은 요청을 반복해도 로그는 중복 생성하지 않음

## 5. 업무 세션

### 업무 세션 응답

```json
{
  "workSessionId": 1,
  "workDate": "2026-08-18",
  "status": "IN_PROGRESS",
  "startedAt": "2026-08-18T09:00:00+09:00",
  "completedAt": null,
  "completedVisitCount": 0,
  "totalVisitCount": 4,
  "totalExposureMinutes": 0,
  "maxContinuousExposureMinutes": 0,
  "totalRestMinutes": 0,
  "restCount": 0
}
```

### `POST /work-sessions/start`

```json
{
  "workDate": "2026-08-18"
}
```

상태를 `READY`에서 `IN_PROGRESS`로 변경하고 `WORK_STARTED` 활동 로그를 기록한다.

### `GET /work-sessions/current`

한국 날짜 기준 오늘 업무 상태와 방문 진행률을 반환한다.

### `PATCH /work-sessions/{work_session_id}/complete`

- 모든 일정이 완료되어야 처리 가능
- 성공 시 상태를 `COMPLETED`로 변경
- `WORK_COMPLETED` 활동 로그 생성
- 미완료 일정이 있거나 업무 시작 전이면 `409`

## 6. 기상

기상청 단기예보 조회서비스를 사용한다. 위·경도는 Backend에서 기상청 격자로 변환한다.

### `GET /weather/current`

```text
/weather/current?latitude=37.57471&longitude=127.01142
```

기상청 초단기실황의 기온과 습도를 반환한다. 체감온도는 기상청 공식 계절별 산식으로 계산한다.

```json
{
  "latitude": 37.57471,
  "longitude": 127.01142,
  "gridX": 60,
  "gridY": 127,
  "observedAt": "2026-08-18T14:00:00+09:00",
  "temperature": 34.0,
  "humidity": 72.0,
  "apparentTemperature": 36.8,
  "source": "KMA"
}
```

### `GET /weather/hourly`

```text
/weather/hourly?latitude=37.57471&longitude=127.01142&date=2026-08-18
```

해당 날짜에 제공되는 시간대별 기온, 습도, 체감온도를 반환한다.

### `GET /weather/forecast`

```text
/weather/forecast?latitude=37.57471&longitude=127.01142&datetime=2026-08-18T15:00:00%2B09:00
```

방문 예정 시각에서 가장 가까운 1시간 단위 단기예보를 반환한다.

환경변수 `KMA_API_KEY`가 없으면 `503`, 기상청 호출에 실패하면 `502`, 제공 범위 밖의 예보는 `404`를 반환한다.

### `GET /weather/asos/hourly`

기상청 지상 종관관측(ASOS)의 과거 시간자료를 지점번호로 조회한다. `stationId`는 ASOS 관측지점 번호이며, 시간은 한국시간 기준으로 전달한다.

```text
/weather/asos/hourly?stationId=108&startAt=2026-08-18T13:00:00%2B09:00&endAt=2026-08-18T14:00:00%2B09:00
```

응답의 `solarRadiation`은 ASOS `icsr` 시간 일사량(MJ/m²)을 모델 입력에 맞춰 W/m²로 변환한 값이고, `surfacePressure`는 ASOS `pa` 현지기압(hPa)이다. ASOS 원자료에는 직접일사 비율이 없으므로 이 응답만으로 Liljegren WBGT 라벨을 완성할 때는 직접일사 추정 또는 별도 일사 자료가 추가로 필요하다.

ASOS API 키는 `KMA_ASOS_API_KEY`를 우선 사용하고, 비어 있으면 `KMA_API_KEY`를 재사용한다. API가 아직 제공하지 않는 최신 시간은 조회할 수 없다.

### `GET /heatwave/current`

서울 지역의 기상청 공식 폭염 영향예보를 반환한다. 영향예보는 관심 단계 이상이 예상될 때만 발표되므로 자료가 없는 경우도 정상 응답이다.

```json
{
  "regionId": "11B10101",
  "regionName": "서울",
  "announcedAt": "2026-08-17T11:30:00+09:00",
  "effectiveDate": null,
  "level": "NONE",
  "label": "발표 없음",
  "hasAnnouncement": false,
  "forecasts": [],
  "source": "KMA"
}
```

위험 단계는 `NONE`, `INTEREST`, `CAUTION`, `WARNING`, `DANGER`를 사용한다. 환경변수는 `KMA_IMPACT_API_KEY`다.

### `GET /weather/living-index`

```text
/weather/living-index?areaNo=1100000000
```

기상청 생활기상지수의 현재 시각과 가장 가까운 자외선지수와 대기정체지수를 반환한다. `areaNo` 기본값은 서울 `1100000000`이다.

```json
{
  "areaNo": "1100000000",
  "publishedAt": "2026-08-17T18:00:00+09:00",
  "ultraviolet": {
    "value": 0.0,
    "label": "낮음",
    "forecastAt": "2026-08-18T00:00:00+09:00"
  },
  "airDiffusion": {
    "value": 75.0,
    "label": "높음",
    "forecastAt": "2026-08-18T00:00:00+09:00"
  },
  "source": "KMA"
}
```

환경변수는 `KMA_LIVING_INDEX_API_KEY`다.

## 7. 지도와 이동구간

TMAP 보행자 경로안내 API를 사용한다. 환경변수는 `MAP_API_KEY`다.

### `POST /routes/normal`

DB에 저장하지 않고 일반 보행 경로만 계산한다.

```json
{
  "origin": {
    "latitude": 37.5739,
    "longitude": 127.0105,
    "name": "현재 위치"
  },
  "destination": {
    "latitude": 37.57471,
    "longitude": 127.01142,
    "name": "김영희"
  },
  "departureTime": "2026-08-18T10:00:00+09:00"
}
```

응답에는 `distanceMeters`, `walkingMinutes`, `estimatedArrivalTime`, 지도 표시용 `path`가 포함된다.

### `POST /route-segments`

업무가 `IN_PROGRESS`이고 일정이 `PENDING`일 때 일반경로와 방문 예정 시각의 날씨를 결합해 DB에 저장한다.

```json
{
  "workSessionId": 1,
  "scheduleId": 1,
  "origin": {
    "latitude": 37.5739,
    "longitude": 127.0105,
    "name": "현재 위치"
  },
  "destination": {
    "latitude": 37.57471,
    "longitude": 127.01142,
    "name": "김영희"
  },
  "departureTime": "2026-08-18T10:00:00+09:00"
}
```

```json
{
  "routeSegmentId": 1,
  "routeOptionId": 1,
  "workSessionId": 1,
  "scheduleId": 1,
  "routeType": "NORMAL",
  "distanceMeters": 615,
  "walkingMinutes": 9,
  "estimatedArrivalTime": "2026-08-18T10:09:00+09:00",
  "path": [
    { "latitude": 37.5739, "longitude": 127.0105 },
    { "latitude": 37.57471, "longitude": 127.01142 }
  ],
  "weather": {
    "forecastAt": "2026-08-18T10:00:00+09:00",
    "temperature": 33.0,
    "humidity": 60.0,
    "apparentTemperature": 34.5,
    "source": "KMA"
  }
}
```

실제 응답에는 `origin`, `destination`, 날씨 좌표도 포함된다. 업무·일정 관계가 맞지 않으면 `409`, TMAP 권한 또는 호출 오류는 `502`를 반환한다.

### `GET /route-segments/{route_segment_id}`

저장된 이동구간과 일반경로를 조회한다. 날씨는 현재 별도 컬럼에 저장하지 않으므로 조회 응답의 `weather`는 `null`이다.

## 8. 기본 사용자 흐름

```text
GET /schedules/today
→ POST /work-sessions/start
→ GET /schedules/next
→ POST /route-segments
→ PATCH /schedules/{id}/complete 반복
→ GET /schedules/next에서 workCompleted=true 확인
→ PATCH /work-sessions/{id}/complete
```

## 9. A/B 분석 계약

위험판단과 쿨링스팟 추천의 입력·출력은 `docs/AB_INTERFACE.md`와 `docs/mocks/`를 확인한다.
