import os
from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass(frozen=True)
class DBConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT_INNER", "5432"))
    user: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    database: str = os.getenv("POSTGRES_DB", "stocks")

    @property
    def connection_string(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
