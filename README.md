# 폭염 이동 안전 지원 서비스

폭염 상황에서 생활지원사의 안전한 이동을 돕는 해커톤 프로젝트입니다. 생활지원사는 방문 일정을 등록하고 현재 위치와 목적지를 기준으로 주변 무더위쉼터 및 기업 쿨링스팟을 확인하며, 폭염 위험을 고려한 안전 경로를 추천받을 수 있습니다. 기업은 자신의 공간을 쿨링스팟으로 등록할 수 있습니다.

## 프로젝트 구조

```text
rest/
├── frontend/             # Next.js 웹 애플리케이션
├── backend/              # FastAPI 서버
├── docs/                 # 개발 및 구조 문서
├── .env.example          # 공통 외부 API 환경변수 예시
├── .gitignore
└── README.md
```

상세한 폴더 역할은 [프로젝트 구조 문서](docs/PROJECT_STRUCTURE.md)를 참고하세요. 현재 구현 상태와 다음 작업은 [작업 현황 문서](docs/WORK_STATUS.md), API 형식은 [API 명세](docs/API.md)와 [A/B 분석 인터페이스](docs/AB_INTERFACE.md)에 정리되어 있습니다.

## 기술 스택

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- Backend: FastAPI, Python, Uvicorn, SQLAlchemy, Alembic
- Database: MySQL 8.x
- API 문서: FastAPI Swagger UI

## Frontend 실행 방법

Node.js 20 이상과 npm이 필요합니다.

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

브라우저에서 <http://localhost:3000>을 엽니다. 프로덕션 빌드는 `npm run build`, 빌드 결과 실행은 `npm run start`를 사용합니다.

## Backend 실행 방법

Docker Desktop과 Python 3.11 이상을 권장합니다. 프로젝트 루트에서 환경변수를 준비하고 MySQL을 먼저 실행합니다.

```bash
cp backend/.env.example backend/.env
docker compose up -d mysql
```

`backend/.env`의 MySQL 비밀번호와 `DATABASE_URL`을 로컬 환경에 맞게 변경한 뒤 Backend를 준비합니다.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

서버는 <http://localhost:8000>에서 실행됩니다.

- 상태 확인: <http://localhost:8000/health>
- DB 연결 확인: <http://localhost:8000/health/db>
- 방문대상자 목록: <http://localhost:8000/visit-targets>
- 오늘 일정: <http://localhost:8000/schedules/today>
- 다음 일정: <http://localhost:8000/schedules/next>
- 현재 업무 상태: <http://localhost:8000/work-sessions/current>
- Swagger API 문서: <http://localhost:8000/docs>

Docker MySQL은 로컬 `127.0.0.1:3307`에서 실행됩니다. `python -m scripts.seed`는 방문대상자 8명, 쿨링스팟 5곳, 오늘 업무 세션 1개와 방문 일정 4개를 추가하며, 다시 실행해도 중복으로 생성하지 않습니다.

Windows PowerShell에서는 가상환경 활성화 명령으로 `.venv\Scripts\Activate.ps1`을 사용합니다.

## 환경변수 설정

예시 파일을 복사한 뒤 로컬 환경에 맞게 값을 채웁니다.

- 루트 `.env.example`: 기상청, 지도/경로, 공공 무더위쉼터 API 키 목록
- `frontend/.env.example`: 브라우저에서 사용하는 백엔드 API 주소
- `backend/.env.example`: 서버 설정과 외부 API 키

실제 `.env`, `.env.local` 등의 파일은 Git에서 제외됩니다. 비밀 값은 코드나 커밋에 직접 넣지 마세요. 새 변수를 만들면 해당 프로젝트의 `.env.example`에도 변수 이름을 추가합니다.

## 기본 협업 방식

2인 해커톤 팀에 맞춰 `dev`에서 통합 테스트를 거치는 단순한 브랜치 흐름을 사용합니다.

1. 최신 `dev`에서 `feat/...` 또는 `fix/...` 브랜치를 만듭니다.
2. Frontend와 Backend 작업 영역을 가능한 한 분리합니다.
3. 기능 단위로 짧게 커밋하고 원격 브랜치에 push합니다.
4. `dev` 대상 Pull Request를 만들고 서로 확인한 뒤 병합합니다.
5. `dev`에서 연동과 핵심 기능을 테스트한 뒤 `dev`에서 `main`으로 Pull Request를 만듭니다.
6. API 기능은 요청/응답 형식을 먼저 합의하고, API 준비 전에는 Frontend에서 mock 데이터를 사용합니다.

브랜치 및 커밋 규칙의 전체 내용은 [개발 방식 문서](docs/DEVELOPMENT.md)를 참고하세요.
