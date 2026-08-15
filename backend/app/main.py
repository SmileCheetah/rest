from fastapi import FastAPI

app = FastAPI(
    title="폭염 이동 안전 지원 API",
    description="생활지원사의 안전한 이동을 지원하는 서비스의 백엔드 API",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """서버의 실행 상태를 확인합니다."""
    return {"status": "ok"}

