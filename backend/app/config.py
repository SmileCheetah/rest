from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """환경변수에서 애플리케이션 설정을 불러옵니다."""

    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"
    kma_api_key: str | None = None
    kma_asos_api_key: str | None = None
    kma_impact_api_key: str | None = None
    kma_living_index_api_key: str | None = None
    kma_api_base_url: str = (
        "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
    )
    kma_asos_api_base_url: str = (
        "https://apis.data.go.kr/1360000/AsosHourlyInfoService"
    )
    kma_impact_api_base_url: str = (
        "https://apis.data.go.kr/1360000/ImpactInfoServiceV2"
    )
    kma_living_index_api_base_url: str = (
        "https://apis.data.go.kr/1360000/LivingWthrIdxServiceV5"
    )
    map_api_key: str | None = None
    tmap_api_base_url: str = "https://apis.openapi.sk.com/tmap"
    public_shelter_api_key: str | None = None
    public_shelter_api_url: str = "https://www.safetydata.go.kr/V2/api/DSSP-IF-10942"
    risk_model_path: Path | None = BACKEND_DIR / "artifacts/risk-model/risk_classifier.joblib"
    work_limit_model_path: Path | None = (
        BACKEND_DIR / "artifacts/risk-model-asos/work_limit_classifier.joblib"
    )
    database_url: str

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
