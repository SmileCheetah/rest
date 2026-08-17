# 쉼표 MVP 작업 현황

> 마지막 갱신: 2026-08-18  
> 목적: 사람 또는 AI가 이 문서만 읽어도 현재 상태를 파악하고 다음 작업을 이어갈 수 있게 한다.

## 1. 현재 상태 요약

- 저장소: `https://github.com/SmileCheetah/rest`
- 로컬 경로: `/Users/m3air/Desktop/Code/Project/rest`
- 현재 브랜치: `feat/core-integration`
- 현재 브랜치는 로컬 전용이며 아직 원격에 push하지 않았다.
- `feat/backend-schedule`에서 분기한 stacked branch다.
- 열린 PR: [#4 업무 세션 API 및 폭염 안전 이동 화면 구현](https://github.com/SmileCheetah/rest/pull/4)
- PR 대상: `dev`
- `dev`에 병합된 기준 커밋: `05a4aa7`
- 현재 브랜치의 주요 커밋:
  - `b191134 feat: 업무 세션 API 추가`
  - `81c5789 feat: 폭염 안전 이동 프론트 화면 구현`
  - `a0338f2 docs: 현재 작업 현황 및 다음 계획 정리`
  - `bba62bd feat: 일정 관리 및 방문 완료 API 추가`
  - `3accab7 docs: 일정 API 작업 현황 갱신`
  - `71687f4 chore: Frontend CORS 설정 추가`
  - `76ddd33 docs: API 및 A/B 분석 인터페이스 정의`
  - `44ee162 feat: 일정 및 업무 API 프론트 연결`
- `main`에는 아직 최신 Backend 기능이 병합되지 않았다.

## 2. 프로젝트 목표

폭염 상황에서 생활지원사의 안전한 이동을 지원하는 서비스다.

핵심 흐름:

```text
오늘 일정 확인
→ 업무 시작
→ 다음 방문지와 이동구간 생성
→ 폭염 위험판단
→ 필요하면 쿨링스팟 추천
→ 일반경로와 안전경로 비교
→ 방문 및 휴식 기록
→ 하루 업무 결과 확인
```

## 3. 역할 분담

### A

- Frontend 전체
- MySQL과 DB 설계
- 일정, 기상, 지도, 경로 API
- 외부 API 연동
- A/B 기능 통합과 통합 테스트

### B

- 데이터 분석과 AI 위험점수
- 연속 야외노출시간 계산
- 휴식 필요 여부 판단
- 쿨링스팟 필터링과 최적 1곳 선정
- 방문·휴식 기록 집계 로직

상세 기준은 `docs/role-responsibilities.md`를 확인한다.

## 4. 기술 스택과 로컬 환경

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- Backend: FastAPI, Python, Uvicorn
- ORM: SQLAlchemy Async
- Migration: Alembic
- Database: MySQL 8.4, InnoDB, `utf8mb4`, UTC
- MySQL Database: `comma`
- 로컬 MySQL 주소: `127.0.0.1:3307`

MySQL이 기본 포트 `3306`이 아닌 `3307`을 사용하는 이유는 로컬에 설치된 MySQL과 충돌을 피하기 위해서다.

비밀번호와 API Key는 `backend/.env`에만 작성한다. 실제 `.env`는 Git에서 제외되어 있다.

## 5. 주요 폴더

```text
rest/
├── frontend/
│   ├── src/app/                  # 실제 Next.js 화면
│   └── example/                  # Figma import용 HTML 화면
├── backend/
│   ├── app/
│   │   ├── models/               # SQLAlchemy 테이블 모델
│   │   ├── routers/              # API 주소와 HTTP 처리
│   │   ├── schemas/              # 요청·응답 형식
│   │   ├── services/             # 조회 및 업무 로직
│   │   ├── config.py             # 환경변수
│   │   ├── database.py           # MySQL 연결과 세션
│   │   ├── main.py               # FastAPI 생성과 Router 등록
│   │   └── time_utils.py         # UTC와 한국 시간 처리
│   ├── migrations/               # Alembic 변경 기록
│   └── scripts/seed.py           # 로컬 mock 데이터
└── docs/
```

Backend 요청 흐름:

```text
Frontend 요청
→ Router
→ Schema 검증
→ Service 로직
→ SQLAlchemy Model
→ MySQL
→ JSON 응답
```

## 6. 완료된 Backend 기반 작업

### Docker와 환경변수

- `docker-compose.yml`로 MySQL 8.4 실행
- Database `comma`, 문자셋 `utf8mb4`, 시간대 UTC
- `backend/.env.example`에 MySQL과 외부 API 변수 작성
- 실제 `.env` Git 제외 확인

### SQLAlchemy 모델

다음 8개 테이블을 구현했다.

| 테이블 | 역할 |
| --- | --- |
| `visit_targets` | 방문대상자 |
| `work_sessions` | 하루 업무 상태와 집계 |
| `schedules` | 방문 일정 |
| `cooling_spots` | 공공·기업 쿨링스팟 |
| `route_segments` | 이동구간 |
| `route_options` | 일반·안전경로 후보 |
| `risk_assessments` | 위험판단 결과 |
| `activity_logs` | 업무·방문·경로·휴식 기록 |

ERD의 FK, Unique, Check Constraint, 기본값, Nullable, 문자열 길이와 숫자 정밀도를 반영했다.

### Alembic

- 초기 migration: `69b16d4208ea_create_initial_tables.py`
- `alembic downgrade base` 후 `alembic upgrade head` 재실행 검증 완료
- `alembic check` 결과 ORM과 migration 사이에 누락된 변경 없음
- 테이블 구조가 바뀔 때만 새 migration이 필요하다.

### Seed

`python -m scripts.seed`로 다음 mock 데이터를 생성한다.

- 방문대상자 8명
- 공공 쿨링스팟 2곳
- 기업 쿨링스팟 3곳
- 실행 날짜의 업무 세션 1개
- 해당 업무 세션의 방문 일정 4개

같은 날짜에 다시 실행해도 중복 생성되지 않는다. 날짜가 바뀐 뒤 실행하면 새 날짜의 업무 세션과 일정이 생성된다.

## 7. 구현된 API

| Method | Endpoint | 상태 | 역할 |
| --- | --- | --- | --- |
| `GET` | `/health` | 완료 | FastAPI 실행 확인 |
| `GET` | `/health/db` | 완료 | MySQL 연결 확인 |
| `GET` | `/visit-targets` | 완료 | 방문대상자 전체 조회 |
| `GET` | `/visit-targets/{visit_target_id}` | 완료 | 방문대상자 상세 조회 |
| `GET` | `/schedules/today` | 완료 | 한국 날짜 기준 오늘 일정 조회 |
| `GET` | `/schedules/next` | 완료 | 다음 미완료 방문지와 전체 완료 여부 조회 |
| `POST` | `/schedules` | 완료 | 방문 일정 생성 |
| `PATCH` | `/schedules/{schedule_id}` | 완료 | 방문 시간·순서·체류시간 수정 |
| `DELETE` | `/schedules/{schedule_id}` | 완료 | 미완료 방문 일정 삭제 |
| `PATCH` | `/schedules/{schedule_id}/complete` | 완료 | 방문 완료와 활동 로그 기록 |
| `POST` | `/work-sessions/start` | 완료 | 업무 시작 |
| `GET` | `/work-sessions/current` | 완료 | 오늘 업무 상태와 방문 진행률 조회 |
| `PATCH` | `/work-sessions/{work_session_id}/complete` | 완료 | 하루 업무 완료 |

Swagger: `http://localhost:8000/docs`

API JSON은 Frontend에서 사용하기 쉽도록 `workSessionId`, `scheduleId`, `visitTargetId` 같은 camelCase를 사용한다.

연동 기준 문서:

- `docs/API.md`: 구현된 공통·일정·업무 API 명세
- `docs/AB_INTERFACE.md`: A가 B에게 전달할 위험분석·쿨링스팟 데이터 계약
- `docs/mocks/`: A/B 요청·응답 예시 JSON

### 업무 시작 요청

```json
{
  "workDate": "2026-08-18"
}
```

### 업무 세션 핵심 규칙

```text
READY → IN_PROGRESS → COMPLETED
```

- 시작 시 `WORK_STARTED` 활동 로그를 기록한다.
- 시작 요청을 반복해도 시작 로그는 중복 생성하지 않는다.
- 모든 일정이 `COMPLETED`여야 업무를 완료할 수 있다.
- 완료 시 `WORK_COMPLETED` 활동 로그를 기록한다.
- 완료 요청을 반복해도 완료 로그는 중복 생성하지 않는다.
- 존재하지 않는 업무는 `404`, 잘못된 상태 전환은 `409`를 반환한다.
- DB에는 UTC로 저장하고 시간 응답은 `Asia/Seoul`로 반환한다.

### 일정 핵심 규칙

- 방문 순서는 같은 업무 세션 안에서 중복될 수 없다.
- 빈 수정 요청은 `422`, 중복 순서는 `409`를 반환한다.
- 완료된 일정과 완료된 업무의 일정은 수정·삭제할 수 없다.
- 일정 삭제 시 뒤의 방문 순서를 1씩 당긴다.
- 방문 완료는 업무가 `IN_PROGRESS`일 때만 가능하다.
- 방문 완료 시 `VISIT_COMPLETED` 활동 로그를 기록한다.
- 완료 요청을 반복해도 완료 로그는 중복 생성하지 않는다.
- 남은 일정이 없으면 `/schedules/next`가 `workCompleted: true`를 반환한다.

## 8. Frontend 현재 상태

현재 브랜치에 폭염 안전 이동 화면과 Backend 기본 API 연동이 구현되어 있다.

화면:

- 오늘 방문 일정
- 방문대상자 추가 Bottom Sheet
- 일정 삭제 메뉴
- 일반경로와 안전경로 비교
- AI 판단 근거
- 고위험 일반경로 경고
- 쿨링스팟 상세
- 이동 안내
- 쉼터 건너뛰기
- 업무 완료 결과

주요 파일:

- `frontend/src/app/page.tsx`: 화면 상태와 API 호출을 연결한 메인 화면
- `frontend/src/app/globals.css`: 화면 스타일
- `frontend/src/lib/api.ts`: Backend API 요청 함수
- `frontend/src/types/api.ts`: API 요청·응답 TypeScript 타입
- `frontend/example/`: Figma import용 HTML, CSS, 개별 화면

실제 API와 연결된 기능:

- 오늘 일정과 방문대상자 조회
- 오늘 업무 상태와 방문 완료 수 조회
- 일정 추가와 삭제
- 업무 시작과 다음 방문지 조회
- 방문 완료와 모든 방문 완료 후 업무 완료
- Backend 연결 실패 시 mock 화면 표시와 재시도 안내

아직 mock인 기능:

- 지도는 실제 지도 API가 아닌 SVG mock이다.
- 날씨, 경로 거리·시간, 위험도, 쿨링스팟 추천은 mock 값이다.
- 노출 감소량과 이용한 쿨링스팟은 mock 값이다.
- 일정 추가 시간은 현재 `14:30` 고정이며 시간 입력 UI 연결이 필요하다.

## 9. 검증 완료 항목

2026-08-18 최신 브랜치 기준:

- Backend Python compile 통과
- Alembic revision `69b16d4208ea (head)` 확인
- `alembic check` 통과
- MySQL 연결 및 `/health/db` 응답 확인
- Seed 2회 실행 시 중복 방지 확인
- 방문대상자 8명 조회 확인
- 오늘 일정 4개 순서 조회 확인
- 업무 `READY → IN_PROGRESS → COMPLETED` 상태 전환 확인
- 미완료 일정이 있을 때 업무 완료 `409` 확인
- 없는 업무 세션 `404` 확인
- 시작·완료 활동 로그가 각각 1개만 생성되는 것 확인
- 일정 생성·수정·삭제와 순서 재정렬 확인
- 잘못된 일정 요청의 `404`, `409`, `422` 응답 확인
- 다음 일정이 방문 완료 순서에 맞게 변경되는 것 확인
- 방문 완료 로그 4개가 중복 없이 생성되는 것 확인
- 업무 시작 → 방문 4건 완료 → 업무 완료 전체 흐름 확인
- Frontend 서버 `200 OK` 확인
- `localhost:3000` CORS preflight 성공 확인
- Frontend가 사용하는 일정 추가·삭제 → 업무 시작 → 방문 4건 완료 → 업무 완료 API 흐름 확인
- Frontend ESLint 통과
- Frontend production build 통과
- 통합 테스트 후 migration과 seed로 DB 초기 상태 복구 확인
- 실제 `.env`가 Git에 포함되지 않는 것 확인

## 10. 아직 구현하지 않은 기능

### 우선순위가 높은 기본 기능

- 일정 추가 시간 입력 UI 연결
- 기상 API를 연결하고 날씨 mock 교체
- 지도 API와 일반경로 생성
- 이동구간 생성 후 B 위험판단 API 연결

### 이후 기능

- 쿨링스팟 필터링과 최적 추천
- 쿨링스팟 경유 안전경로
- 방문·휴식 기록과 일일 집계
- 배포 환경과 운영용 Secret 설정

## 11. 다음 작업 권장 순서

1. GitHub 점검이 끝나면 `feat/backend-work-session`의 문서 커밋을 push한다.
2. PR #4의 변경사항을 확인하고 `dev`에 병합한다.
3. 현재 `feat/backend-schedule` 브랜치를 최신 `dev` 기준으로 정리한다.
4. 일정 API 변경사항을 push하고 별도 `dev` PR을 만든다.
5. `feat/core-integration` 변경사항을 push하고 `dev` PR을 만든다.
6. 기상 API를 연결해 현재 날씨와 시간대별 예보를 실제 데이터로 교체한다.
7. 지도 API로 일반경로와 이동구간을 생성한다.
8. B가 `docs/AB_INTERFACE.md`와 `docs/mocks/`를 기준으로 위험판단을 구현한다.
9. 위험판단 결과와 쿨링스팟 추천을 연결해 안전경로를 생성한다.
10. 방문·휴식 기록과 하루 집계를 연결한다.

현재 로컬 작업 브랜치:

```text
feat/core-integration
```

## 12. 실행 방법

프로젝트 루트에서:

```bash
cp backend/.env.example backend/.env
docker compose up -d mysql
```

`backend/.env`에서 `MYSQL_PASSWORD`와 `DATABASE_URL` 안의 비밀번호를 동일하게 설정한다.

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

확인 주소:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000/health`
- DB 연결: `http://localhost:8000/health/db`
- Swagger: `http://localhost:8000/docs`

## 13. 협업 및 안전 규칙

- 기본 개발 흐름은 `기능 브랜치 → dev PR → dev 테스트 → main PR`이다.
- 가능한 한 `main`과 `dev`에 직접 push하지 않는다.
- 실제 `.env`, 비밀번호, API Key를 커밋하지 않는다.
- 환경변수를 추가하면 `.env.example`도 수정한다.
- DB 모델 구조를 변경하면 Alembic migration을 생성한다.
- Seed 데이터나 API 로직만 변경하면 migration이 필요하지 않다.
- 이미 공유한 migration을 수정하기보다 새 migration을 추가한다.
- 공통 문서나 설정을 수정할 때 팀원에게 알린다.

## 14. AI에게 작업을 다시 요청할 때

AI에게 먼저 다음 문서를 읽게 한다.

```text
docs/WORK_STATUS.md
docs/database-erd.md
docs/role-responsibilities.md
docs/DEVELOPMENT.md
```

그다음 아래처럼 요청한다.

```text
현재 저장소의 docs/WORK_STATUS.md를 먼저 읽고 Git 상태와 실제 코드를 확인해줘.
기존 변경사항을 보존하고 다음 미완료 작업부터 이어서 진행해줘.
작업 후 테스트하고 기능 단위로 커밋하되 push나 PR 병합은 내가 요청할 때만 해줘.
```

AI가 작업을 시작하기 전에 반드시 확인할 항목:

- `git status`
- 현재 브랜치와 원격 추적 상태
- 열린 PR과 `dev` 병합 여부
- 기존 사용자 변경사항
- Docker MySQL 상태
- Alembic 현재 revision
- 해당 날짜의 seed 데이터 존재 여부
