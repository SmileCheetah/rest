# 프로젝트 구조

해커톤에서 빠르게 기능을 만들 수 있도록 Frontend와 Backend를 분리하되, 초기에는 계층을 최소화합니다. 실제 기능이 생길 때 필요한 폴더만 추가합니다.

```text
rest/
├── frontend/
│   ├── public/           # 이미지, 아이콘 등 정적 파일
│   ├── src/app/          # Next.js 페이지, 레이아웃, 전역 스타일
│   ├── .env.example      # 공개 가능한 Frontend 환경변수 예시
│   └── package.json      # 스크립트 및 JavaScript 의존성
├── backend/
│   ├── app/
│   │   ├── models/       # SQLAlchemy 테이블 모델
│   │   ├── routers/      # 기능별 FastAPI 엔드포인트
│   │   ├── schemas/      # API 요청 및 응답 모델
│   │   ├── services/     # 조회 및 업무 로직
│   │   ├── config.py     # 환경변수 설정
│   │   ├── database.py   # DB 엔진과 요청 단위 세션
│   │   └── main.py       # FastAPI 앱 생성 및 라우터 등록
│   ├── migrations/       # Alembic DB migration
│   ├── scripts/          # 로컬 mock 데이터 seed
│   ├── .env.example      # Backend 환경변수 예시
│   ├── alembic.ini       # Alembic 설정
│   └── requirements.txt  # Python 의존성
├── docs/
│   ├── DEVELOPMENT.md    # Git 및 팀 협업 규칙
│   ├── PROJECT_STRUCTURE.md
│   ├── WORK_STATUS.md     # 현재 구현 상태와 다음 작업
│   ├── database-erd.md   # MySQL ERD와 테이블 정의
│   └── role-responsibilities.md
├── docker-compose.yml    # 로컬 MySQL 8.x 실행 환경
├── .env.example          # 저장소 공통 외부 API 변수 목록
├── .gitignore
└── README.md
```

## 기능이 늘어날 때

### Frontend

- 새 화면: `frontend/src/app/<경로>/page.tsx`
- 여러 화면에서 쓰는 UI: `frontend/src/components/`
- API 호출 함수: `frontend/src/lib/api/`
- 공유 TypeScript 타입: `frontend/src/types/`
- 이미지와 아이콘: `frontend/public/`

폴더는 첫 파일이 필요해질 때 만듭니다. 한 화면에서만 쓰는 작은 컴포넌트는 해당 화면 가까이에 두어도 됩니다.

### Backend

- 기능별 API 라우터: `backend/app/routers/` (예: `schedules.py`, `routes.py`)
- 외부 API 연동 및 업무 로직: `backend/app/services/`
- 요청/응답 Pydantic 모델: `backend/app/schemas/`
- DB 테이블 모델: `backend/app/models/`
- DB 구조 변경: 모델 수정 후 `backend/migrations/`에 Alembic migration 추가
- 로컬 mock 데이터: `backend/scripts/seed.py`
- 공통 설정: `backend/app/config.py`

라우터가 생기면 `backend/app/main.py`에서 등록합니다. 초기에는 데이터 접근 계층이나 복잡한 의존성 주입 구조를 미리 만들지 않고, 코드가 반복되거나 저장소가 실제로 필요해질 때 분리합니다.

### 문서

API 요청/응답에 대한 팀 합의가 길어지면 `docs/API.md`를 추가합니다. 기본 API 스키마와 테스트 기능은 FastAPI `/docs`를 우선 사용합니다.
