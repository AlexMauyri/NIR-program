from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_url: str = "postgresql+asyncpg://admin:admin@localhost:5433/stocks"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ml-features"
    minio_use_ssl: bool = False

    mlflow_tracking_uri: str = "http://localhost:5000"
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
