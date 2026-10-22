# backend/app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Groq
    GROQ_API_KEY: str = ""

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # Redis
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    # BallDontLie
    BALLDONTLIE_API_KEY: str = ""

    # ML
    MODEL_PATH: str = "app/ml/artifacts/courtiq_model.pkl"
    MODEL_SCALER_PATH: str = "app/ml/artifacts/scaler.pkl"
    MODEL_FEATURES_PATH: str = "app/ml/artifacts/feature_names.json"
    MIN_GAMES_FOR_PREDICTION: int = 5
    USE_ML_MODEL: bool = True

    # Scheduling
    ENABLE_SCHEDULER: bool = True
    INGEST_HOUR_UTC: int = 8
    RETRAIN_DAY: str = "monday"

    # NBA API
    NBA_API_DELAY: float = 0.7

    # Admin routes (ingest/retrain/bootstrap) require this token in the X-Admin-Token header.
    # Leave empty to disable admin routes entirely.
    ADMIN_TOKEN: str = ""

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
