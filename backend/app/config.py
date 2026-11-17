from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "civicweave"
    
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    default_city: str = "Sample City"

    semantic_weight: float = 0.45
    spatial_weight: float = 0.35
    temporal_weight: float = 0.20
    default_spatial_radius_meters: float = 300.0
    default_temporal_window_days: int = 7
    semantic_similarity_threshold: float = 0.5
    combined_score_threshold: float = 0.6

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def cloudinary_configured(self) -> bool:
        return bool(self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
