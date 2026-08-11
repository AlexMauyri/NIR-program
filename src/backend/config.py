from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_url: str = "postgresql+asyncpg://admin:admin@localhost:5433/stocks"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
