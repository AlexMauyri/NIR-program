import os
from dataclasses import dataclass

@dataclass(frozen=True)
class MinioConfig:
    endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    secret_key: str = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    bucket: str = os.getenv("MINIO_BUCKET", "ml-features")
    use_ssl: bool = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

    @property
    def endpoint_url(self) -> str:
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.endpoint}"
