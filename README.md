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

상세한 폴더 역할은 [프로젝트 구조 문서](docs/PROJECT_STRUCTURE.md)를 참고하세요.

## 기술 스택

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- Backend: FastAPI, Python, Uvicorn
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

Python 3.11 이상을 권장합니다.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

서버는 <http://localhost:8000>에서 실행됩니다.

- 상태 확인: <http://localhost:8000/health>
- Swagger API 문서: <http://localhost:8000/docs>

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
