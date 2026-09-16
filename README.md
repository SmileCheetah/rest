<img width="239" height="544" alt="스크린샷 2026-09-16 오후 8 56 58" src="https://github.com/user-attachments/assets/2bff649d-3fda-478e-8560-a1c3530f81b9" /># 쉼표

## 폭염 이동 안전 지원 서비스

> 폭염 속 생활지원사의 방문 일정과 이동 경로를 분석해
> 필요한 휴식과 안전한 이동 경로를 안내하는 AI 기반 서비스입니다.

[![GitHub]([https://img.shields.io/badge/GitHub-Repository-181717?logo=github)](https://github.com/SmileCheetah/rest](https://github.com/SmileCheetah/rest))
[![Demo]([https://img.shields.io/badge/Demo-Live%20Service-00C853)](https://rest-brown-iota.vercel.app](https://rest-brown-iota.vercel.app/))

---

## 프로젝트 소개

폭염이 심해질수록 생활지원사는 취약계층을 돌보기 위해
야외 이동을 반복하지만, 방문 일정과 폭염 위험을 함께 고려해
언제 쉬고 어디로 이동해야 하는지 판단하기는 어렵습니다.

REST는 다음 데이터를 결합해 생활지원사의 안전한 이동을 지원합니다.

- 방문 일정과 방문 대상자 정보
- 기온·습도·체감온도·폭염 위험 정보
- 현재 위치와 다음 방문지
- 연속·누적 야외 노출시간
- 공공 무더위쉼터와 기업 쿨링스팟
- TMAP 보행자 경로 정보

이를 바탕으로 휴식 필요도를 판단하고,
필요한 경우 쿨링스팟을 경유하는 안전 경로를 추천합니다.

---

## 해커톤 진행 과정

### 온라인 해커톤

폭염 속 돌봄노동자의 안전 공백을 문제로 정의하고,
기상 데이터·이동 데이터·쉼터 데이터를 활용한
AI 기반 안전 동행 서비스 아이디어를 기획했습니다.

- 생활지원사의 폭염 노출 문제 정의
- 방문 일정과 이동 경로를 고려한 휴식 예측 방향 설계
- 공공 무더위쉼터와 기업 쿨링스팟 연계
- AI가 이동구간별 휴식 필요도와 적정 휴식 횟수를 판단하는 구조 기획

### 오프라인 해커톤

온라인에서 정의한 아이디어를 실제 동작하는 MVP로 구현했습니다.

- 서울 종로구 창신동 일대 시나리오 구성
- 생활지원사 방문 일정 mock 데이터 구성
- 기상청 및 TMAP API 연동
- 이동구간별 폭염 위험과 야외 노출시간 계산
- 휴식 필요도에 따른 쿨링스팟 추천
- 일반 경로와 안전 경로 비교
- 방문·휴식 활동 기록 및 업무 결과 집계

---

## 주요 기능

### 1. 방문 일정 관리

- 방문 대상자 조회
- 오늘 방문 일정 확인
- 방문 일정 추가·수정·삭제
- 다음 방문지 조회
- 방문 완료 처리

### 2. 폭염 위험 확인

- 현재 기온·습도·체감온도 조회
- 시간대별 기상 예보 조회
- 폭염 영향예보 및 생활기상지수 확인
- 이동구간별 폭염 위험 판단

### 3. 야외 노출시간 계산

- 연속 야외 이동시간 계산
- 하루 누적 이동시간 계산
- 최근 휴식시간 반영
- 방문과 이동 일정에 따른 예상 노출시간 계산

### 4. 휴식 필요도 판단

- 기상 상태, 이동시간, 활동량, 최근 휴식시간을 종합
- 휴식 필요도 점수 산출
- `LOW`, `MEDIUM`, `HIGH` 단계로 분류
- 위험 요인과 판단 근거 제공

### 5. 쿨링스팟 추천

- 공공 무더위쉼터와 기업 쿨링스팟 통합
- 운영시간과 방문 예정시간 비교
- 경로 이탈거리와 추가 이동시간 고려
- 이용 가능한 후보 중 최적의 쿨링스팟 추천

### 6. 안전 경로 안내

- TMAP 기반 일반 보행 경로 생성
- 추천 쿨링스팟을 경유하는 안전 경로 생성
- 일반 경로와 안전 경로의 거리·시간 비교
- 사용자의 휴식 선택 및 이동 결과 기록

---

## 서비스 화면

### 오늘 일정과 폭염 상태

생활지원사가 오늘 방문할 대상자와
현재 폭염 상태를 한 화면에서 확인할 수 있습니다.

<img width="258" height="570" alt="스크린샷 2026-09-16 오후 8 57 12" src="https://github.com/user-attachments/assets/399377e7-64a3-432a-9cc1-43239e6448f0" />

### 일반 경로와 안전 경로 비교

폭염 위험도와 휴식 필요도를 반영해
쿨링스팟을 경유하는 안전 경로를 제안합니다.

<img width="239" height="544" alt="스크린샷 2026-09-16 오후 8 56 58" src="https://github.com/user-attachments/assets/074a36bb-0a90-4f77-a90e-e24b33ad6e96" />

### 쿨링스팟 추천

현재 이동 경로에서 이용 가능한 쉼터와
예상 추가 이동시간을 확인할 수 있습니다.

<img width="227" height="204" alt="스크린샷 2026-09-16 오후 8 59 05" src="https://github.com/user-attachments/assets/472ebfb7-97f8-429d-870e-6b9dc9a31f63" />

### 업무 완료 결과

방문·휴식·이동 기록을 바탕으로
하루 업무 결과와 노출시간을 요약합니다.

<img width="250" height="540" alt="스크린샷 2026-09-16 오후 9 01 14" src="https://github.com/user-attachments/assets/f14fe3f8-03e8-4e6c-94c0-f6476053fbd9" />

---

## 담당 역할

김상호

- Next.js 기반 일정·지도·이동 안내 화면 구현
- FastAPI 기반 일정·업무 세션·기상·경로 API 구현
- SQLAlchemy·MySQL 기반 데이터 모델 및 DB 설계
- Alembic 기반 데이터베이스 migration 구성
- 기상청·TMAP·공공 쉼터 데이터 연동
- 연속·누적 야외 노출시간 계산 로직 구현
- 휴식 필요도 판단 로직 구현
- 운영시간·거리·경로 이탈시간을 고려한 쿨링스팟 추천
- 방문·휴식·이동 활동 기록 및 업무 결과 집계
- 팀원이 구현한 AI 모델 API와 전체 서비스 흐름 통합

김윤진

- AI 모델 API 요청·응답 구조 구현
- 폭염 위험 및 휴식 필요도 예측 모델 구현
- 학습 데이터와 모델 결과 개선
- AI 판단 결과를 서비스에서 활용할 수 있도록 연동

---

## 서비스 흐름

```text
오늘 방문 일정 확인
        ↓
업무 시작 및 다음 방문지 조회
        ↓
현재 위치와 다음 방문지 기반 일반 경로 생성
        ↓
기상 정보와 이동 정보를 결합
        ↓
야외 노출시간 및 폭염 위험 분석
        ↓
휴식 필요도 판단
        ↓
쿨링스팟 후보 필터링 및 추천
        ↓
일반 경로와 안전 경로 비교
        ↓
방문·휴식 결과 기록
        ↓
하루 업무 결과 집계
시스템 구조
Frontend
Next.js · React · TypeScript
        │
        │ REST API
        ▼
Backend
FastAPI
 ├── Router       HTTP 요청 처리
 ├── Schema       요청·응답 검증
 ├── Service      도메인 및 계산 로직
 ├── Model        SQLAlchemy 데이터 모델
 └── ML           위험·휴식 필요도 분석
        │
        ▼
MySQL
방문자 · 일정 · 이동구간 · 경로 · 위험판단
쿨링스팟 · 활동로그 · 업무 세션
기술적 구현
계층형 Backend 구조
Frontend 요청을 Router, Schema, Service, Model 계층으로 분리했습니다.
Frontend 요청
→ Router
→ Schema 검증
→ Service 로직
→ SQLAlchemy Model
→ MySQL
→ JSON 응답
기능별 책임을 분리해 일정·기상·경로·휴식·쿨링스팟 기능을
독립적으로 관리하고 통합할 수 있도록 구성했습니다.
외부 API 오류 처리
기상청과 TMAP API 호출 과정에서 발생할 수 있는
인증 오류, 요청 제한, 네트워크 오류, 응답 형식 오류를 구분했습니다.
- API 키 누락: 503 Service Unavailable
- 외부 API 오류: 502 Bad Gateway
- 존재하지 않는 데이터: 404 Not Found
- 잘못된 상태 전환: 409 Conflict
데이터베이스 설계
다음 데이터를 별도의 테이블로 관리했습니다.
- visit_targets: 방문 대상자
- work_sessions: 하루 업무 세션
- schedules: 방문 일정
- cooling_spots: 공공·기업 쿨링스팟
- route_segments: 이동구간
- route_options: 일반·안전 경로
- risk_assessments: 위험 판단 결과
- activity_logs: 방문·이동·휴식 활동 기록
시간과 상태 관리
- 데이터베이스에는 UTC 기준으로 저장
- 사용자 응답은 Asia/Seoul 기준으로 변환
- 업무 상태를 READY → IN_PROGRESS → COMPLETED로 관리
- 완료된 방문과 업무는 중복 처리되지 않도록 검증
API
주요 API는 다음과 같습니다.
Method	Endpoint	설명
GET	/health	서버 상태 확인
GET	/health/db	데이터베이스 연결 확인
GET	/visit-targets	방문 대상자 목록 조회
GET	/schedules/today	오늘 방문 일정 조회
POST	/schedules	방문 일정 생성
PATCH	/schedules/{id}/complete	방문 완료 처리
POST	/work-sessions/start	업무 시작
GET	/weather/current	현재 기상 정보 조회
GET	/heatwave/current	폭염 영향예보 조회
POST	/routes/normal	일반 보행 경로 생성
POST	/routes/safe	쿨링스팟 경유 안전 경로 생성
POST	/routes/recommendation	위험 판단 기반 경로 추천
POST	/route-segments	이동구간 생성
GET	/work-sessions/current	현재 업무 상태 조회


상세한 API 형식은 [API 명세](docs/API.md)에서 확인할 수 있습니다.
기술 스택
Frontend
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
Backend
- FastAPI
- Python
- Uvicorn
- SQLAlchemy Async
- Alembic
Database
- MySQL 8.x
- Docker
- InnoDB
- utf8mb4
External API
- 기상청 API
- TMAP 보행자 경로 API
- 공공 무더위쉼터 데이터
프로젝트 구조
rest/
├── frontend/
│   ├── src/app/              # Next.js 화면
│   ├── src/components/       # UI 컴포넌트
│   ├── src/lib/              # API 요청 함수
│   └── src/types/            # TypeScript 타입
├── backend/
│   ├── app/
│   │   ├── models/           # SQLAlchemy 모델
│   │   ├── routers/          # API 라우터
│   │   ├── schemas/          # 요청·응답 스키마
│   │   ├── services/         # 도메인 로직
│   │   └── ml/               # AI·분석 로직
│   ├── migrations/           # Alembic migration
│   ├── scripts/              # seed 및 학습 스크립트
│   └── tests/                # Backend 테스트
├── ai-test/                  # AI 모델 실험 코드
├── docs/                     # 프로젝트 문서
├── docker-compose.yml
└── README.md
실행 방법
사전 요구사항
- Node.js 20 이상
- Python 3.11 이상
- Docker Desktop
- MySQL 8.x
Frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev
브라우저에서 http://localhost:3000을 엽니다.
Backend
cp backend/.env.example backend/.env
docker compose up -d mysql

cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
Backend는 http://localhost:8000에서 실행됩니다.
Swagger API 문서는
http://localhost:8000/docs에서 확인할 수 있습니다.
Seed 데이터
Seed 실행 시 다음 mock 데이터가 생성됩니다.
- 방문 대상자 8명
- 공공 쿨링스팟 2곳
- 기업 쿨링스팟 3곳
- 업무 세션 1개
- 방문 일정 4개
같은 날짜에 다시 실행해도 중복으로 생성되지 않습니다.
협업 방식
해커톤 팀에 맞춰 dev 브랜치를 중심으로 협업했습니다.
1. dev에서 기능별 브랜치 생성
2. Frontend와 Backend 작업 영역 분리
3. 기능 단위 커밋 및 원격 브랜치 push
4. Pull Request를 통한 코드 확인
5. dev에서 통합 테스트
6. 최종 기능 확인 후 main 반영
API 요청·응답 형식을 먼저 합의한 뒤
각 담당 기능을 독립적으로 개발하고 최종적으로 통합했습니다.
회고
REST를 구현하며 단순히 AI 모델의 예측 결과를 제공하는 것만으로는
사용자에게 실제 가치가 전달되지 않는다는 점을 배웠습니다.
기상 정보와 AI 판단 결과를 방문 일정, 이동 경로,
휴식 장소 추천과 연결해야 사용자가 실제 행동으로 이어갈 수 있었습니다.
또한 외부 API를 연동할 때는 정상 응답뿐 아니라
인증 실패, 네트워크 오류, 응답 지연과 같은 예외 상황까지
고려해야 안정적인 서비스 흐름을 만들 수 있다는 점을 경험했습니다.
문서
- [프로젝트 구조](docs/PROJECT_STRUCTURE.md)
- [작업 현황](docs/WORK_STATUS.md)
- [API 명세](docs/API.md)
- [A/B 분석 인터페이스](docs/AB_INTERFACE.md)
- [데이터베이스 ERD](docs/database-erd.md)
- [개발 방식](docs/DEVELOPMENT.md)
- [위험 모델 실험 기록](docs/risk-model-experiment.md)
