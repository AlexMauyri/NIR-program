import mlflow
from mlflow.tracking import MlflowClient
import boto3
from botocore.client import Config
from config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


class MLFlowConnectionError(Exception):
    pass

def get_mlflow_client() -> MlflowClient:
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        return MlflowClient()
    except Exception as e:
        raise MLFlowConnectionError(f"MLFlow unavailable: {e}")


def _get_minio_endpoint_url() -> str:
    endpoint = settings.minio_endpoint
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    scheme = "https" if settings.minio_use_ssl else "http"
    return f"{scheme}://{endpoint}"


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=_get_minio_endpoint_url(),
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
    )

engine = create_async_engine(
    settings.postgres_url,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
