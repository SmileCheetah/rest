# 개발 방식

이 문서는 2명이 참여하는 해커톤 프로젝트에서 빠르게 개발하면서 충돌을 줄이기 위한 최소 협업 규칙을 정의합니다.

## 브랜치 전략

기본 브랜치는 `main`이며, 실제 기능을 합치고 테스트하는 통합 브랜치는 `dev`입니다.

- `main`: 시연하거나 배포할 수 있는 안정된 코드만 유지합니다.
- `dev`: 완료된 기능을 모아 Frontend/Backend 연동과 통합 테스트를 진행합니다.
- `feat/*`, `fix/*`: 기능 또는 수정 단위의 짧은 작업 브랜치입니다.

```text
feat/frontend-schedule
feat/frontend-map
feat/backend-schedule
feat/backend-weather
feat/backend-route
fix/map-location
```

기능 구현이 끝나면 `dev`를 대상으로 Pull Request를 생성합니다. `dev`에서 기능 및 연동 테스트를 마친 뒤 `dev`에서 `main`으로 Pull Request를 생성합니다. `main`과 `dev`에 직접 push하지 않고 PR을 통해 병합하는 것을 원칙으로 합니다. 해커톤 속도를 위해 별도의 release 브랜치나 복잡한 Git Flow는 사용하지 않습니다.

```text
feat/* 또는 fix/*
        ↓ PR 및 팀원 확인
       dev
        ↓ 통합 테스트 후 PR
       main
```

## 커밋 컨벤션

```text
feat: 새로운 기능
fix: 버그 수정
refactor: 코드 구조 개선
docs: 문서 수정
chore: 설정 및 기타 작업
test: 테스트 코드
```

예시:

```text
feat: 방문 일정 조회 API 추가
feat: 현재 위치 지도 표시 구현
fix: 경로 조회 좌표 오류 수정
docs: 개발 방식 문서 추가
```

## 개발 순서

작업 전에 최신 `dev`에서 브랜치를 생성합니다.

```bash
git checkout dev
git pull origin dev
git checkout -b feat/기능명
```

작업 완료 후 변경 사항을 커밋하고 push합니다.

```bash
git add .
git commit -m "feat: 기능 설명"
git push origin feat/기능명
```

그다음 GitHub에서 `dev` 대상 Pull Request를 생성합니다. 다른 팀원이 변경 범위와 실행 여부를 간단히 확인한 뒤 병합합니다.

여러 기능이 `dev`에 합쳐져 시연 가능한 상태가 되면 다음을 확인합니다.

- Frontend가 정상 실행되고 주요 화면이 동작하는지
- Backend가 정상 실행되고 `/health`, `/docs` 및 추가된 API가 동작하는지
- Frontend와 Backend 연동에 문제가 없는지
- 실제 `.env`나 비밀 값이 커밋되지 않았는지

확인이 끝나면 GitHub에서 `dev`에서 `main`으로 Pull Request를 생성합니다. 긴급 수정도 가능한 한 `fix/* → dev → main` 순서를 따릅니다.

## Frontend / Backend 협업 방식

Frontend와 Backend는 가능한 한 독립적으로 개발합니다. API가 필요한 기능은 구현 전에 URL, HTTP 메서드, 요청 값, 정상 응답, 오류 응답을 먼저 합의합니다.

예상 API:

```text
GET  /api/schedules/today
POST /api/schedules
GET  /api/shelters/nearby
POST /api/cooling-spots
POST /api/routes/safe
```

실제 API가 준비되지 않았다면 Frontend는 합의된 응답 형태의 mock 데이터로 화면 개발을 먼저 진행합니다. Backend API의 현재 사용 방법과 스키마는 서버 실행 후 FastAPI Swagger UI(`/docs`)에서 확인합니다.

## 환경변수 규칙

- API Key, 비밀번호, Secret 값은 코드에 직접 작성하지 않습니다.
- `.env`, `.env.local` 등 실제 환경변수 파일은 Git에 올리지 않습니다.
- 새로운 환경변수를 추가하면 관련 `.env.example`에도 변수 이름과 안전한 예시를 추가합니다.
- `NEXT_PUBLIC_` 접두사가 있는 값은 브라우저에 공개되므로 비밀 값을 넣지 않습니다.

## 코드 충돌 방지

팀원의 작업 영역을 가능한 한 분리합니다. Frontend 작업은 `frontend/`, Backend 작업은 `backend/` 내부에서 진행합니다.

다음 공통 파일을 수정할 때는 작업 전이나 PR 생성 시 팀원에게 공유합니다.

- `README.md`
- `.gitignore`
- `.env.example`
- `docs/` 내부 공통 문서

큰 기능을 한 브랜치에서 오래 개발하지 않고 화면, API 또는 수정 사항 단위로 작게 나눕니다. 같은 파일을 동시에 바꿔야 한다면 담당 범위와 병합 순서를 먼저 정합니다.
