from prefect import task
from datetime import date
from configs import MinioConfig
from clients import MinioClient

from utils import _get_logger

@task(name="upload_to_minio")
def upload_to_minio(
    local_path: str,
    object_name: str,
    minio_config: MinioConfig,
) -> None:
    logger = _get_logger()

    logger.info(">>> UPLOAD to MinIO: %s", local_path)
    minio_client = MinioClient(minio_config)

    minio_client.upload(local_path, object_name)
    
    logger.info("Uploaded: s3://%s/%s", minio_config.bucket, object_name)
    logger.info("<<< UPLOAD to MinIO: done")
